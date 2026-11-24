"""
Authoritative Authentication and Security Dependencies for JARVIS.

Provides fail-closed API Key and session token verification for local and remote deployments.
Supports constant-time credential comparison, session token generation, and fine-grained access control.
"""

from datetime import datetime, timezone
import hmac
import hashlib
import logging
import secrets
import threading
import time
from typing import Optional

from fastapi import Depends, Header, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.settings import settings

logger = logging.getLogger("jarvis.auth")

# Optional HTTP Bearer handler (auto_error=False allows falling back to header / query param)
_bearer_security = HTTPBearer(auto_error=False)

# Session token lifespan: 24 hours (86,400 seconds)
SESSION_TOKEN_TTL_SECONDS: float = 86400.0

# Thread-safe in-memory session tokens: token -> {"created_at": float, "expires_at": float, "label": str}
_session_lock = threading.Lock()
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


def _purge_expired_tokens_locked() -> None:
    """Remove expired session tokens while holding _session_lock."""
    now = time.time()
    expired = [t for t, meta in _ACTIVE_SESSION_TOKENS.items() if meta.get("expires_at", 0) <= now]
    for t in expired:
        _ACTIVE_SESSION_TOKENS.pop(t, None)


def verify_credential(token: str) -> bool:
    """
    Constant-time comparison against configured API key or active session token.
    Prevents timing attacks. Validates TTL expiration for session tokens.
    """
    if not token or not isinstance(token, str):
        return False

    token_bytes = token.encode("utf-8")

    # 1. Check against Master API Key
    configured_key = get_configured_api_key()
    if hmac.compare_digest(token_bytes, configured_key.encode("utf-8")):
        return True

    # 2. Check against active session tokens with constant-time comparison
    now = time.time()
    with _session_lock:
        _purge_expired_tokens_locked()
        for active_token, meta in list(_ACTIVE_SESSION_TOKENS.items()):
            if hmac.compare_digest(token_bytes, active_token.encode("utf-8")):
                if meta.get("expires_at", float("inf")) > now:
                    return True
                else:
                    _ACTIVE_SESSION_TOKENS.pop(active_token, None)

    return False


def create_session_token(
    label: str = "web_ui",
    ttl_seconds: float = SESSION_TOKEN_TTL_SECONDS,
    owner_id: str | None = None,
) -> str:
    """Create a high-entropy session token with explicit TTL expiration."""
    token = f"jarvis_sess_{secrets.token_urlsafe(32)}"
    now = time.time()
    with _session_lock:
        _purge_expired_tokens_locked()
        _ACTIVE_SESSION_TOKENS[token] = {
            "created_at": now,
            "expires_at": now + ttl_seconds,
            "label": label,
            "owner_id": owner_id or hashlib.sha256(f"jarvis-owner:{token}".encode("utf-8")).hexdigest(),
        }
    return token


def revoke_session_token(token: str) -> bool:
    """Revoke an active session token."""
    with _session_lock:
        return _ACTIVE_SESSION_TOKENS.pop(token, None) is not None


def revoke_all_session_tokens() -> int:
    """Revoke all active session tokens. Returns count of revoked tokens."""
    with _session_lock:
        count = len(_ACTIVE_SESSION_TOKENS)
        _ACTIVE_SESSION_TOKENS.clear()
        return count


def owner_id_for_credential(token: str) -> str:
    """Return a stable, non-secret principal identifier for an authenticated credential."""
    configured_key = get_configured_api_key()
    if hmac.compare_digest(token.encode("utf-8"), configured_key.encode("utf-8")):
        if not getattr(settings, "api_key", "").strip():
            return "legacy"
        return hashlib.sha256(f"jarvis-owner:{configured_key}".encode("utf-8")).hexdigest()

    with _session_lock:
        _purge_expired_tokens_locked()
        metadata = _ACTIVE_SESSION_TOKENS.get(token)
        if metadata:
            return str(metadata["owner_id"])
    if token == "unauthenticated_test_mode":
        return "test_mode"
    raise ValueError("Credential is not an active authenticated principal.")


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
    Never exposes raw tokens in logs or error messages.
    """
    # If authentication is disabled globally (e.g. in test environment)
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


async def require_principal(token: str = Depends(require_auth)) -> str:
    """Dependency returning a stable owner identifier rather than the bearer secret."""
    return owner_id_for_credential(token)
