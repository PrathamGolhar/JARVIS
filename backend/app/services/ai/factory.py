import logging
import time
from typing import Any
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.base import AIProvider, AIChatResponse
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.groq_provider import GroqProvider
from app.services.ai.health import (
    ErrorCategory,
    ProviderStatus,
    classify_http_error,
    provider_health_registry,
)
from app.services.ai.local_provider import LocalProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.settings import settings

logger = logging.getLogger("jarvis.ai_factory")

# Ordered provider cascade: best to last resort
_PROVIDER_CASCADE = ["gemini", "groq", "openai", "anthropic"]
_PROVIDER_CLASSES: dict[str, type[AIProvider]] = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def get_ai_provider(preferred: str | None = None, fallback_on_unconfigured: bool = False) -> AIProvider:
    """
    Resolve the active AI provider.

    In auto mode, select the best configured provider:
    Gemini → Groq → OpenAI → Anthropic → Local fallback.

    For an explicitly requested provider, fail loudly if it is not configured
    (unless fallback_on_unconfigured=True) so callers can surface the real
    problem instead of silently falling back to another provider.
    """
    pref = (preferred or settings.ai_provider or "auto").lower()

    if pref == "local":
        rec = provider_health_registry.get("local")
        rec.configured = True
        rec.status = ProviderStatus.HEALTHY
        return LocalProvider()

    provider_map = _PROVIDER_CLASSES

    if pref in provider_map:
        provider = provider_map[pref]()
        rec = provider_health_registry.get(pref)
        rec.configured = provider.is_available()
        if provider.is_available():
            if rec.status == ProviderStatus.UNKNOWN:
                rec.status = ProviderStatus.HEALTHY
            return provider
        rec.status = ProviderStatus.UNAVAILABLE
        if not fallback_on_unconfigured and (preferred is not None or settings.ai_provider.lower() == pref):
            raise RuntimeError(f"Selected AI provider '{pref}' is not configured.")

    if pref not in {"auto", "", *provider_map.keys()}:
        logger.warning("Unknown AI provider requested: %s. Falling back to auto selection.", pref)

    # Auto fallback order: Gemini → Groq → OpenAI → Anthropic → Local
    for provider_name in _PROVIDER_CASCADE:
        provider = provider_map[provider_name]()
        rec = provider_health_registry.get(provider_name)
        rec.configured = provider.is_available()
        if provider.is_available():
            # Skip providers that are known-failed due to auth or quota (non-retryable)
            if rec.error_category in (ErrorCategory.AUTHENTICATION, ErrorCategory.QUOTA_EXHAUSTED):
                logger.info(
                    "Skipping provider '%s' (non-retryable error: %s)",
                    provider_name, rec.error_category.value,
                )
                continue
            if rec.status == ProviderStatus.UNKNOWN:
                rec.status = ProviderStatus.HEALTHY
            return provider
        rec.status = ProviderStatus.UNAVAILABLE

    # All cloud providers unavailable — activate local
    logger.warning("All cloud AI providers unavailable. Activating local offline engine.")
    rec = provider_health_registry.get("local")
    rec.configured = True
    rec.status = ProviderStatus.HEALTHY
    return LocalProvider()


def get_active_provider_safe() -> AIProvider:
    """Get active provider with guaranteed safe fallback to LocalProvider if unconfigured."""
    return get_ai_provider(fallback_on_unconfigured=True)


def list_configured_providers() -> list[str]:
    providers = []
    if GeminiProvider().is_available():
        providers.append("gemini")
    if GroqProvider().is_available():
        providers.append("groq")
    if OpenAIProvider().is_available():
        providers.append("openai")
    if AnthropicProvider().is_available():
        providers.append("anthropic")
    providers.append("local")
    return providers


def execute_with_failover(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    temperature: float = 0.3,
    max_tokens: int = 800,
    user_override: str | None = None,
) -> tuple[AIChatResponse, str]:
    """
    Execute a chat request with automatic provider failover.

    Returns (response, provider_name_used).

    Failover order: preferred → cascade → local.
    Authentication errors and quota exhaustion are not retried.
    """
    pref = (user_override or settings.ai_provider or "auto").lower()

    # Build ordered list of providers to try
    if pref in _PROVIDER_CLASSES:
        providers_to_try = [pref] + [p for p in _PROVIDER_CASCADE if p != pref]
    else:
        providers_to_try = list(_PROVIDER_CASCADE)

    failures: list[str] = []

    for provider_name in providers_to_try:
        cls = _PROVIDER_CLASSES.get(provider_name)
        if not cls:
            continue
        provider = cls()
        rec = provider_health_registry.get(provider_name)
        rec.configured = provider.is_available()

        if not provider.is_available():
            rec.status = ProviderStatus.UNAVAILABLE
            failures.append(f"{provider_name.upper()}: not configured")
            continue

        # Skip known non-retryable failures
        if rec.error_category in (ErrorCategory.AUTHENTICATION, ErrorCategory.QUOTA_EXHAUSTED):
            failures.append(f"{provider_name.upper()}: skipped ({rec.error_category.value})")
            continue

        t0 = time.perf_counter()
        try:
            response = provider.chat(messages=messages, tools=tools, temperature=temperature, max_tokens=max_tokens)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            rec.record_success(latency_ms)
            logger.info("Provider '%s' responded in %.0fms", provider_name, latency_ms)
            return response, provider_name
        except RuntimeError as exc:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            exc_str = str(exc)
            # Try to classify from HTTP error info embedded in RuntimeError message
            cat = _classify_runtime_error(exc_str)
            rec.record_failure(cat, exc_str[:200])
            failures.append(f"{provider_name.upper()}: {cat.value} — {exc_str[:80]}")
            logger.warning("Provider '%s' failed (%s): %s", provider_name, cat.value, exc_str[:120])
            # Non-retryable: don't try remaining providers for auth issues specific to this provider
            # but still try the next provider (they have different keys)
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            rec.record_failure(ErrorCategory.UNKNOWN, str(exc)[:200])
            failures.append(f"{provider_name.upper()}: {type(exc).__name__} — {str(exc)[:80]}")
            logger.warning("Provider '%s' unexpected error: %s", provider_name, exc)

    # All cloud providers failed — use local offline engine and surface failure clearly
    logger.error("All AI providers exhausted. Failures:\n%s", "\n".join(failures))
    failure_summary = "\n".join(f"  • {f}" for f in failures)
    local = LocalProvider()
    rec = provider_health_registry.get("local")
    rec.configured = True
    rec.status = ProviderStatus.HEALTHY

    offline_response = local.chat(messages=messages, tools=tools, temperature=temperature, max_tokens=max_tokens)
    return offline_response, "local"


def _classify_runtime_error(exc_str: str) -> ErrorCategory:
    """Extract error category from a RuntimeError message string."""
    low = exc_str.lower()
    if "401" in exc_str or "403" in exc_str or "authentication" in low or "invalid api key" in low or "unauthorized" in low:
        return ErrorCategory.AUTHENTICATION
    if "quota" in low or "tokens per day" in low or "tpd" in low or "daily" in low:
        return ErrorCategory.QUOTA_EXHAUSTED
    if "429" in exc_str or "rate limit" in low:
        return ErrorCategory.RATE_LIMIT
    if "timeout" in low or "timed out" in low:
        return ErrorCategory.TIMEOUT
    if "404" in exc_str or "model" in low and "not found" in low:
        return ErrorCategory.MODEL_UNAVAILABLE
    if "400" in exc_str or "invalid request" in low:
        return ErrorCategory.INVALID_REQUEST
    if any(f"{c}" in exc_str for c in [500, 502, 503]):
        return ErrorCategory.SERVER_ERROR
    if "network" in low or "connection" in low or "unreachable" in low:
        return ErrorCategory.NETWORK
    return ErrorCategory.UNKNOWN
