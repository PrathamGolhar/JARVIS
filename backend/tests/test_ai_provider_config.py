import pytest

from app.services.ai.factory import get_ai_provider
from app.services.ai.local_provider import LocalProvider
from app.settings import settings


def test_auto_provider_falls_back_to_local_when_all_providers_are_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "auto")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "groq_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "anthropic_api_key", "")

    provider = get_ai_provider()

    assert isinstance(provider, LocalProvider)


def test_explicit_unavailable_provider_raises_a_clear_error(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "ai_provider", "gemini")

    with pytest.raises(RuntimeError, match="Selected AI provider 'gemini' is not configured"):
        get_ai_provider("gemini")
