from pathlib import Path
import re
from fastapi import APIRouter

from app.schemas import SettingsStatusResponse, SettingsUpdateRequest
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.factory import get_ai_provider, list_configured_providers
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.groq_provider import GroqProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.settings import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


def _persist_env_key(key: str, value: str) -> None:
    """Write or update a single key in the .env file (does not affect unrelated lines)."""
    if not _ENV_FILE.exists():
        return
    try:
        content = _ENV_FILE.read_text(encoding="utf-8")
        pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
        if pattern.search(content):
            content = pattern.sub(f"{key}={value}", content)
        else:
            content = content.rstrip("\n") + f"\n{key}={value}\n"
        _ENV_FILE.write_text(content, encoding="utf-8")
    except OSError:
        pass  # File write errors are non-fatal; settings remain in-memory


@router.get("", response_model=SettingsStatusResponse)
async def get_settings() -> SettingsStatusResponse:
    active_prov = get_ai_provider()
    return SettingsStatusResponse(
        aiProvider=settings.ai_provider,
        availableProviders=list_configured_providers(),
        activeModel=getattr(active_prov, "model", "local-rule-engine"),
        geminiConfigured=GeminiProvider().is_available(),
        groqConfigured=GroqProvider().is_available(),
        openaiConfigured=OpenAIProvider().is_available(),
        anthropicConfigured=AnthropicProvider().is_available(),
        elevenlabsConfigured=bool(settings.elevenlabs_api_key),
        permissionMode=settings.permission_mode,
        wakeWordEnabled=True,
    )


@router.post("", response_model=SettingsStatusResponse)
async def update_settings(request: SettingsUpdateRequest) -> SettingsStatusResponse:
    if request.ai_provider is not None:
        settings.ai_provider = request.ai_provider
        _persist_env_key("JARVIS_AI_PROVIDER", request.ai_provider)
    if request.gemini_api_key is not None and request.gemini_api_key.strip():
        settings.gemini_api_key = request.gemini_api_key
        _persist_env_key("JARVIS_GEMINI_API_KEY", request.gemini_api_key)
        _persist_env_key("GOOGLE_API_KEY", request.gemini_api_key)
    if request.groq_api_key is not None and request.groq_api_key.strip():
        settings.groq_api_key = request.groq_api_key
        _persist_env_key("JARVIS_GROQ_API_KEY", request.groq_api_key)
        _persist_env_key("GROQ_API_KEY", request.groq_api_key)
    if request.openai_api_key is not None and request.openai_api_key.strip():
        settings.openai_api_key = request.openai_api_key
        _persist_env_key("JARVIS_OPENAI_API_KEY", request.openai_api_key)
        _persist_env_key("OPENAI_API_KEY", request.openai_api_key)
    if request.anthropic_api_key is not None and request.anthropic_api_key.strip():
        settings.anthropic_api_key = request.anthropic_api_key
        _persist_env_key("JARVIS_ANTHROPIC_API_KEY", request.anthropic_api_key)
        _persist_env_key("ANTHROPIC_API_KEY", request.anthropic_api_key)
    if request.elevenlabs_api_key is not None and request.elevenlabs_api_key.strip():
        settings.elevenlabs_api_key = request.elevenlabs_api_key
        _persist_env_key("JARVIS_ELEVENLABS_API_KEY", request.elevenlabs_api_key)
        _persist_env_key("ELEVENLABS_API_KEY", request.elevenlabs_api_key)
    if request.permission_mode is not None:
        settings.permission_mode = request.permission_mode
        _persist_env_key("JARVIS_PERMISSION_MODE", request.permission_mode)

    return await get_settings()
