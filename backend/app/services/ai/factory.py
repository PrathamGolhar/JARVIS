import logging
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.base import AIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.groq_provider import GroqProvider
from app.services.ai.local_provider import LocalProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.settings import settings

logger = logging.getLogger("jarvis.ai_factory")


def get_ai_provider(preferred: str | None = None) -> AIProvider:
    """
    Resolve the active AI provider.

    In auto mode, select the best configured provider:
    Gemini -> Groq -> OpenAI -> Anthropic -> Local fallback.

    For an explicitly requested provider, fail loudly if it is not configured so callers
    can surface the real problem instead of silently falling back to another provider.
    """
    pref = (preferred or settings.ai_provider or "auto").lower()

    if pref == "local":
        return LocalProvider()

    provider_map = {
        "gemini": GeminiProvider,
        "groq": GroqProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }

    if pref in provider_map:
        provider = provider_map[pref]()
        if provider.is_available():
            return provider
        if preferred is not None or settings.ai_provider.lower() == pref:
            raise RuntimeError(f"Selected AI provider '{pref}' is not configured.")

    if pref not in {"auto", "", *provider_map.keys()}:
        logger.warning("Unknown AI provider requested: %s. Falling back to auto selection.", pref)

    # Auto fallback order: Gemini -> Groq -> OpenAI -> Anthropic -> Local
    for provider_name in ("gemini", "groq", "openai", "anthropic"):
        provider = provider_map[provider_name]()
        if provider.is_available():
            return provider

    return LocalProvider()


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

