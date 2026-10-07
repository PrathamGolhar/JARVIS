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
    If 'auto' or unspecified, selects the best configured provider:
    Gemini -> Groq -> OpenAI -> Anthropic -> Local Fallback.
    """
    pref = (preferred or settings.ai_provider or "auto").lower()

    if pref == "gemini":
        prov = GeminiProvider()
        if prov.is_available():
            return prov

    if pref == "groq":
        prov = GroqProvider()
        if prov.is_available():
            return prov

    if pref == "openai":
        prov = OpenAIProvider()
        if prov.is_available():
            return prov

    if pref == "anthropic":
        prov = AnthropicProvider()
        if prov.is_available():
            return prov

    if pref == "local":
        return LocalProvider()

    # Auto fallback order: Gemini -> Groq -> OpenAI -> Anthropic -> Local
    gemini = GeminiProvider()
    if gemini.is_available():
        return gemini

    groq = GroqProvider()
    if groq.is_available():
        return groq

    openai = OpenAIProvider()
    if openai.is_available():
        return openai

    anthropic = AnthropicProvider()
    if anthropic.is_available():
        return anthropic

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

