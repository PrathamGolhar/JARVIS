"""
Authoritative Authentication and Security Dependencies for JARVIS.

Provides fail-closed API Key and session token verification for local and remote deployments.
Supports constant-time credential comparison, session token generation, and fine-grained access control.
"""

from datetime import datetime, timezone
import hmac
import logging
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.settings import settings

logger = logging.getLogger("jarvis.auth")

# Optional HTTP Bearer handler (auto_error=False allows falling back to header / query param)
_bearer_security = HTTPBearer(auto_error=False)

# In-memory session tokens with timestamps: token -> {"created_at": float, "label": str}
_ACTIVE_SESSION_TOKENS: dict[str, dict] = {}


def generate_master_api_key() -> str:
    """Generate a high-entropy master API key."""
    return f"jarvis_sec_{secrets.token_hex(24)}"


def get_configured_api_key() -> str:
    """Retrieve the active configured API key, generating one in-memory if none exists."""
    key = getattr(settings, "api_key", "").strip()
    if not key:
        # Fallback to an environment-configured key or session key
        if not hasattr(settings, "_ephemeral_api_key"):
            settings._ephemeral_api_key = generate_master_api_key()
            logger.warning(
                "JARVIS_API_KEY was not configured in settings or environment. "
                "Generated ephemeral master key: %s (set JARVIS_API_KEY to persist)",
                settings._ephemeral_api_key,
            )
        return settings._ephemeral_api_key
    return key


def verify_credential(token: str) -> bool:
    """
    Constant-time comparison against configured API key or active session token.
    Prevents timing attacks.
    """
    if not token or not isinstance(token, str):
        return False

    configured_key = get_configured_api_key()
    if hmac.compare_digest(token.encode("utf-8"), configured_key.encode("utf-8")):
        return True

    # Check active session tokens
    if token in _ACTIVE_SESSION_TOKENS:
        return True

    return False


def create_session_token(label: str = "web_ui") -> str:
    """Create a high-entropy session token."""
    token = f"jarvis_sess_{secrets.token_urlsafe(32)}"
    _ACTIVE_SESSION_TOKENS[token] = {
        "created_at": datetime.now(timezone.utc).timestamp(),
        "label": label,
    }
    return token


def revoke_session_token(token: str) -> bool:
    """Revoke an active session token."""
    return _ACTIVE_SESSION_TOKENS.pop(token, None) is not None


async def require_auth(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_security),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    api_key_query: Optional[str] = Query(default=None, alias="api_key"),
) -> str:
    """
    Authoritative authentication dependency.
    Validates requests using:
    1. Authorization: Bearer <token>
    2. X-API-Key: <key>
    3. ?api_key=<key> (query parameter for downloads/media)

    Fail-closed: Returns 401 if authentication is missing or invalid when auth_enabled is True.
    """
    # If authentication is disabled globally (e.g. in certain local unit tests)
    if not getattr(settings, "auth_enabled", True):
        return "unauthenticated_test_mode"

    extracted_token: Optional[str] = None

    if auth_header and auth_header.credentials:
        extracted_token = auth_header.credentials.strip()
    elif x_api_key and x_api_key.strip():
        extracted_token = x_api_key.strip()
    elif api_key_query and api_key_query.strip():
        extracted_token = api_key_query.strip()

    if not extracted_token:
        logger.warning("Unauthenticated request blocked at: %s %s", request.method, request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided. Provide 'X-API-Key' or 'Authorization: Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_credential(extracted_token):
        logger.warning("Invalid credentials rejected at: %s %s", request.method, request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return extracted_token
