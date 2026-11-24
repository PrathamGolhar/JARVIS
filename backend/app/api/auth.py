from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.services.auth import (
    create_session_token,
    get_configured_api_key,
    owner_id_for_credential,
    require_auth,
    revoke_session_token,
    verify_credential,
)
from app.services.permissions import reset_emergency_stop, trigger_emergency_stop
from app.settings import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthTokenRequest(BaseModel):
    api_key: str


class AuthTokenResponse(BaseModel):
    ok: bool
    session_token: str
    token_type: str = "Bearer"


class AuthStatusResponse(BaseModel):
    auth_enabled: bool
    permission_mode: str
    emergency_stop_active: bool


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status() -> AuthStatusResponse:
    """Public status endpoint to check if authentication is active and inspect system posture."""
    return AuthStatusResponse(
        auth_enabled=getattr(settings, "auth_enabled", True),
        permission_mode=getattr(settings, "permission_mode", "assisted"),
        emergency_stop_active=getattr(settings, "emergency_stop_active", False),
    )


@router.post("/token", response_model=AuthTokenResponse)
async def obtain_session_token(payload: AuthTokenRequest) -> AuthTokenResponse:
    """Exchange the Master API Key for a high-entropy session token."""
    if not payload.api_key or not verify_credential(payload.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Master API Key.",
        )
    token = create_session_token(
        label="user_session",
        owner_id=owner_id_for_credential(payload.api_key),
    )
    return AuthTokenResponse(ok=True, session_token=token)


@router.post("/revoke")
async def revoke_token(request: Request, token: str = Depends(require_auth)) -> dict[str, Any]:
    """Revoke the current session token."""
    revoked = revoke_session_token(token)
    return {"ok": True, "revoked": revoked}


@router.post("/emergency-stop")
async def activate_emergency_stop(token: str = Depends(require_auth)) -> dict[str, Any]:
    """Immediately halt all autonomous actions, code execution, and tool activities."""
    trigger_emergency_stop()
    return {"ok": True, "emergency_stop_active": True, "message": "Emergency stop successfully activated."}


@router.post("/emergency-reset")
async def deactivate_emergency_stop(token: str = Depends(require_auth)) -> dict[str, Any]:
    """Reset emergency stop and restore standard permission mode."""
    reset_emergency_stop()
    return {"ok": True, "emergency_stop_active": False, "message": "Emergency stop reset."}
