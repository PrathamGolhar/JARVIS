import logging
from pathlib import Path
import re
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import SettingsStatusResponse, SettingsUpdateRequest
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.factory import get_ai_provider, list_configured_providers
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.groq_provider import GroqProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.services.auth import require_auth, verify_credential
from app.services.confirmation import confirmation_manager
from app.settings import settings

logger = logging.getLogger("jarvis.api.settings")
router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_auth)])

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

ALLOWED_ENV_KEYS = {
    "JARVIS_AI_PROVIDER",
    "JARVIS_GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "JARVIS_GROQ_API_KEY",
    "GROQ_API_KEY",
    "JARVIS_OPENAI_API_KEY",
    "OPENAI_API_KEY",
    "JARVIS_ANTHROPIC_API_KEY",
    "ANTHROPIC_API_KEY",
    "JARVIS_ELEVENLABS_API_KEY",
    "ELEVENLABS_API_KEY",
    "JARVIS_PERMISSION_MODE",
}


def _persist_env_key(key: str, value: str) -> None:
    """Write or update an allowlisted key in the .env file with validation."""
    if key not in ALLOWED_ENV_KEYS:
        logger.warning("Blocked attempt to persist unapproved key '%s' to .env", key)
        return

    # Sanitize value: no raw newlines
    clean_val = value.replace("\r", "").replace("\n", "").strip()

    if not _ENV_FILE.exists():
        return
    try:
        content = _ENV_FILE.read_text(encoding="utf-8")
        pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
        if pattern.search(content):
            content = pattern.sub(f"{key}={clean_val}", content)
        else:
            content = content.rstrip("\n") + f"\n{key}={clean_val}\n"
        _ENV_FILE.write_text(content, encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not persist setting '%s' to .env: %s", key, exc)


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
    # 1. READ_ONLY Permission Mode Guard
    if getattr(settings, "permission_mode", "assisted") == "read_only":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Modifying administrative settings is disabled in 'read_only' permission mode.",
        )

    # 2. Permission Mode Validation & Elevation Protection
    if request.permission_mode is not None:
        valid_modes = {"read_only", "assisted", "full_control"}
        chosen_mode = request.permission_mode.lower().strip()
        if chosen_mode not in valid_modes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid permission mode '{request.permission_mode}'. Must be one of: {', '.join(sorted(valid_modes))}.",
            )

        current_mode = getattr(settings, "permission_mode", "assisted")
        if chosen_mode == "full_control" and current_mode != "full_control":
            # Explicit re-authentication or confirmation token required for privilege elevation
            elevated = False
            if request.master_api_key and verify_credential(request.master_api_key):
                elevated = True
            elif request.confirmation_token:
                try:
                    confirmation_manager.consume_confirmation(request.confirmation_token, session_id="admin")
                    elevated = True
                except ValueError:
                    elevated = False

            if not elevated:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Privilege elevation to 'full_control' requires explicit re-authentication (provide valid masterApiKey or confirmationToken).",
                )

        settings.permission_mode = chosen_mode
        _persist_env_key("JARVIS_PERMISSION_MODE", chosen_mode)

    if request.ai_provider is not None:
        valid_providers = {"auto", "gemini", "groq", "openai", "anthropic", "local"}
        prov = request.ai_provider.lower().strip()
        if prov not in valid_providers:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid AI provider '{request.ai_provider}'. Must be one of: {', '.join(sorted(valid_providers))}.",
            )
        settings.ai_provider = prov
        _persist_env_key("JARVIS_AI_PROVIDER", prov)

    if request.gemini_api_key is not None and request.gemini_api_key.strip():
        settings.gemini_api_key = request.gemini_api_key.strip()
        _persist_env_key("JARVIS_GEMINI_API_KEY", settings.gemini_api_key)
        _persist_env_key("GOOGLE_API_KEY", settings.gemini_api_key)

    if request.groq_api_key is not None and request.groq_api_key.strip():
        settings.groq_api_key = request.groq_api_key.strip()
        _persist_env_key("JARVIS_GROQ_API_KEY", settings.groq_api_key)
        _persist_env_key("GROQ_API_KEY", settings.groq_api_key)

    if request.openai_api_key is not None and request.openai_api_key.strip():
        settings.openai_api_key = request.openai_api_key.strip()
        _persist_env_key("JARVIS_OPENAI_API_KEY", settings.openai_api_key)
        _persist_env_key("OPENAI_API_KEY", settings.openai_api_key)

    if request.anthropic_api_key is not None and request.anthropic_api_key.strip():
        settings.anthropic_api_key = request.anthropic_api_key.strip()
        _persist_env_key("JARVIS_ANTHROPIC_API_KEY", settings.anthropic_api_key)
        _persist_env_key("ANTHROPIC_API_KEY", settings.anthropic_api_key)

    if request.elevenlabs_api_key is not None and request.elevenlabs_api_key.strip():
        settings.elevenlabs_api_key = request.elevenlabs_api_key.strip()
        _persist_env_key("JARVIS_ELEVENLABS_API_KEY", settings.elevenlabs_api_key)
        _persist_env_key("ELEVENLABS_API_KEY", settings.elevenlabs_api_key)

    return await get_settings()
