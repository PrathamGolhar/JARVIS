"""
Authoritative Confirmation and Two-Phase Action Verification for JARVIS.

Enforces:
1. Cryptographically secure random tokens (secrets.token_urlsafe).
2. Strict session-binding: A confirmation token can only be executed by the session that created it.
3. Strict expiration: 300-second (5-minute) TTL.
4. One-time use / Replay protection: Token is atomically consumed upon execution.
5. Argument integrity: SHA-256 verification ensures arguments cannot be mutated post-confirmation.
6. Thread-safe concurrent storage and automatic cleanup of stale actions.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
import secrets
import threading
import time
from typing import Any, Optional

logger = logging.getLogger("jarvis.confirmation")

CONFIRMATION_TTL_SECONDS = 300  # 5 minutes


def _hash_arguments(arguments: dict[str, Any]) -> str:
    """Generate canonical SHA-256 hash of tool arguments to prevent argument tampering."""
    serialized = json.dumps(arguments, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass
class PendingConfirmation:
    action_id: str
    session_id: str
    tool_name: str
    arguments: dict[str, Any]
    arguments_hash: str
    created_at: float
    expires_at: float
    label: str
    description: str
    consumed: bool = False


class ConfirmationManager:
    """Thread-safe store and validator for high-impact pending actions."""

    def __init__(self, ttl_seconds: int = CONFIRMATION_TTL_SECONDS) -> None:
        self._lock = threading.Lock()
        self._actions: dict[str, PendingConfirmation] = {}
        self.ttl_seconds = ttl_seconds

    def create_confirmation(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        session_id: str,
        label: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create and store a session-bound, expiring pending action."""
        with self._lock:
            self._purge_expired_locked()

            action_id = f"act_{secrets.token_urlsafe(24)}"
            now = time.time()
            expires_at = now + self.ttl_seconds
            arg_hash = _hash_arguments(arguments)

            if not label:
                if tool_name == "open_application":
                    app_id = arguments.get("app_id", "application")
                    label = f"Launch {app_id.replace('_', ' ').title()}"
                    description = f"Launch desktop application: {app_id}"
                elif tool_name == "write_file":
                    target = arguments.get("file_path", "file")
                    label = f"Write {target}"
                    description = f"Create or update workspace file: {target}"
                elif tool_name == "execute_python_code":
                    label = "Execute Python Code"
                    description = "Execute sandboxed Python script in restricted subprocess"
                else:
                    label = f"Execute {tool_name}"
                    description = f"Execute high-impact operation: {tool_name}"

            pending = PendingConfirmation(
                action_id=action_id,
                session_id=str(session_id),
                tool_name=tool_name,
                arguments=arguments,
                arguments_hash=arg_hash,
                created_at=now,
                expires_at=expires_at,
                label=label or f"Execute {tool_name}",
                description=description or f"Confirm execution of {tool_name}",
                consumed=False,
            )
            self._actions[action_id] = pending

            logger.info(
                "Created pending confirmation %s for tool '%s' (session=%s, expires_in=%ds)",
                action_id,
                tool_name,
                session_id,
                self.ttl_seconds,
            )

            return {
                "actionId": action_id,
                "sessionId": str(session_id),
                "toolName": tool_name,
                "arguments": arguments,
                "label": pending.label,
                "description": pending.description,
                "requiresConfirmation": True,
                "expiresAt": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
                "expires_at": expires_at,
            }

    def consume_confirmation(
        self,
        action_id: str,
        session_id: str,
        assert_arguments: Optional[dict[str, Any]] = None,
    ) -> PendingConfirmation:
        """
        Validate and atomically consume a pending confirmation.
        Raises ValueError if invalid, expired, already consumed, or session mismatched.
        """
        with self._lock:
            self._purge_expired_locked()

            pending = self._actions.get(action_id)
            if not pending:
                raise ValueError("Confirmation token is invalid or has expired.")

            if pending.consumed:
                raise ValueError("Confirmation token has already been consumed (replay attempt blocked).")

            now = time.time()
            if now > pending.expires_at:
                self._actions.pop(action_id, None)
                raise ValueError(f"Confirmation token expired {int(now - pending.expires_at)}s ago.")

            # Strict session validation: Cross-session confirmation is blocked
            if str(pending.session_id) != str(session_id):
                logger.warning(
                    "Cross-session confirmation attempt rejected for %s: expected %s, got %s",
                    action_id,
                    pending.session_id,
                    session_id,
                )
                raise ValueError("Confirmation token does not belong to the active session.")

            # Argument tampering validation
            if assert_arguments is not None:
                provided_hash = _hash_arguments(assert_arguments)
                if provided_hash != pending.arguments_hash:
                    logger.warning("Tampered confirmation arguments rejected for %s", action_id)
                    raise ValueError("Action arguments do not match the original confirmation proposal.")

            # Mark consumed and remove atomically
            pending.consumed = True
            self._actions.pop(action_id, None)

            logger.info("Successfully consumed confirmation token %s for '%s'", action_id, pending.tool_name)
            return pending

    def _purge_expired_locked(self) -> int:
        """Internal helper to clean up expired entries."""
        now = time.time()
        expired_keys = [k for k, v in self._actions.items() if now > v.expires_at or v.consumed]
        for k in expired_keys:
            self._actions.pop(k, None)
        return len(expired_keys)

    def count_pending(self) -> int:
        with self._lock:
            self._purge_expired_locked()
            return len(self._actions)


# Global authoritative instance
confirmation_manager = ConfirmationManager()
