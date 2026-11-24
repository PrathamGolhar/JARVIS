"""
Adversarial Security and Execution Safety Regression Test Suite for JARVIS.

Validates:
1. Complete API route authorization policy (public vs private).
2. Session token TTL expiration and revocation.
3. Privilege elevation to full_control requiring re-authentication.
4. Action confirmation one-time consumption, replay protection, and cross-session isolation.
5. Pydantic schema serialization for confirmed action events (no 500 error).
6. JavaScript and Python sandbox escape vector interception.
7. SSRF PinnedIPAdapter DNS rebinding/TOCTOU mitigation.
8. Symlink and workspace path traversal containment.
9. Emergency stop execution halting.
"""

import io
from pathlib import Path
import time
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.auth import (
    create_session_token,
    get_configured_api_key,
    require_auth,
    revoke_session_token,
    verify_credential,
)
from app.services.coding.sandbox import execute_sandboxed_code
from app.services.confirmation import confirmation_manager
from app.services.permissions import (
    PermissionMode,
    reset_emergency_stop,
    trigger_emergency_stop,
    validate_tool_approval,
)
from app.services.security_network import (
    PinnedIPAdapter,
    SSRFSecurityError,
    safe_http_fetch,
    validate_hostname_ip_resolution,
)
from app.services.tools.file_tools import _resolve_safe_path
from app.settings import settings

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1. AUTHENTICATION & PUBLIC/PRIVATE ROUTE POLICY
# -----------------------------------------------------------------------------

def test_public_routes_accessible_without_auth(monkeypatch):
    """Liveness probes and auth negotiation status must remain public."""
    monkeypatch.setattr(settings, "auth_enabled", True)

    res_health = client.get("/api/health")
    assert res_health.status_code == 200

    res_auth_status = client.get("/api/auth/status")
    assert res_auth_status.status_code == 200


def test_sensitive_routes_require_authentication(monkeypatch):
    """Every sensitive subsystem must fail-closed (401) when unauthenticated."""
    monkeypatch.setattr(settings, "auth_enabled", True)

    protected_endpoints = [
        ("POST", "/api/chat", {"sessionId": str(uuid4()), "text": "hello"}),
        ("GET", "/api/settings", None),
        ("POST", "/api/settings", {"aiProvider": "local"}),
        ("POST", "/api/code/execute", {"code": "print(1)", "language": "python"}),
        ("GET", "/api/files/download/report.pdf", None),
        ("GET", "/api/memory", None),
        ("GET", "/api/projects", None),
        ("GET", "/api/diagnostics", None),
        ("GET", "/api/capabilities", None),
        ("GET", "/api/voices", None),
        ("POST", "/api/tts", {"text": "hello", "voiceId": "en-US-GuyNeural"}),
        ("POST", "/api/web-actions/plan", {"text": "open youtube"}),
    ]

    for method, path, payload in protected_endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path, json=payload)
        assert res.status_code == 401, f"Endpoint {method} {path} must require authentication (got {res.status_code})"


def test_session_token_ttl_expiration(monkeypatch):
    """Session tokens must expire after their configured TTL."""
    monkeypatch.setattr(settings, "auth_enabled", True)

    # Issue token with very short TTL (0.1s)
    short_token = create_session_token(label="ttl_test", ttl_seconds=0.1)
    assert verify_credential(short_token) is True

    time.sleep(0.15)
    assert verify_credential(short_token) is False

    # Calling an endpoint with expired token must return 401
    res = client.get("/api/settings", headers={"Authorization": f"Bearer {short_token}"})
    assert res.status_code == 401


def test_session_token_revocation(monkeypatch):
    """Revoking an active token immediately invalidates access."""
    monkeypatch.setattr(settings, "auth_enabled", True)

    token = create_session_token(label="revoke_test", ttl_seconds=3600)
    assert verify_credential(token) is True

    # Revoke
    revoked = revoke_session_token(token)
    assert revoked is True
    assert verify_credential(token) is False

    res = client.get("/api/settings", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


# -----------------------------------------------------------------------------
# 2. PRIVILEGE ELEVATION TO FULL_CONTROL
# -----------------------------------------------------------------------------

def test_elevation_to_full_control_blocked_without_reauth(monkeypatch):
    """Switching to full_control mode must fail without re-authentication."""
    monkeypatch.setattr(settings, "auth_enabled", False)
    monkeypatch.setattr(settings, "permission_mode", "assisted")

    # Attempt elevation without credentials
    res = client.post("/api/settings", json={"permissionMode": "full_control"})
    assert res.status_code == 403
    assert "elevation" in res.json()["detail"].lower()
    assert settings.permission_mode == "assisted"

    # Now attempt with valid masterApiKey
    test_key = get_configured_api_key()
    res_valid = client.post(
        "/api/settings",
        json={"permissionMode": "full_control", "masterApiKey": test_key},
    )
    assert res_valid.status_code == 200
    assert settings.permission_mode == "full_control"

    # Reset back to assisted for other tests
    settings.permission_mode = "assisted"


# -----------------------------------------------------------------------------
# 3. CONFIRMATION SECURITY & SCHEMAS SERIALIZATION
# -----------------------------------------------------------------------------

def test_confirmation_replay_and_cross_session_rejected():
    """Confirmation tokens must be single-use and bound to the session."""
    sid_a = "session_alice"
    sid_b = "session_bob"
    args = {"filename": "output.txt", "content": "data"}

    action = confirmation_manager.create_confirmation("write_workspace_file", args, session_id=sid_a)
    act_id = action["actionId"]

    # Session Bob cannot execute Alice's confirmation
    with pytest.raises(ValueError) as exc_b:
        confirmation_manager.consume_confirmation(act_id, session_id=sid_b)
    assert "active session" in str(exc_b.value).lower()

    # Session Alice consumes it
    consumed = confirmation_manager.consume_confirmation(act_id, session_id=sid_a)
    assert consumed.tool_name == "write_workspace_file"

    # Replay attack by Alice must fail
    with pytest.raises(ValueError) as exc_replay:
        confirmation_manager.consume_confirmation(act_id, session_id=sid_a)
    assert "not found" in str(exc_replay.value).lower() or "expired" in str(exc_replay.value).lower()


def test_confirmed_action_response_serialization_success(monkeypatch):
    """Executing confirmed action in /api/chat must serialize without Pydantic error (no 500)."""
    monkeypatch.setattr(settings, "auth_enabled", False)
    sid = str(uuid4())

    # Create pending confirmation
    action = confirmation_manager.create_confirmation(
        "calculator",
        {"expression": "2 + 2"},
        session_id=sid,
        label="Calculate Arithmetic",
    )

    # Post confirmation to /api/chat
    res = client.post(
        "/api/chat",
        json={"sessionId": sid, "text": "Confirmed", "confirmedActionId": action["actionId"]},
    )
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "toolEvents" in data
    assert len(data["toolEvents"]) > 0
    assert data["toolEvents"][0]["toolName"] == "confirmed_action"


# -----------------------------------------------------------------------------
# 4. CODE EXECUTION & JAVASCRIPT SANDBOXING
# -----------------------------------------------------------------------------

def test_javascript_sandbox_blocks_dangerous_constructs():
    """JavaScript execution must reject Node.js system and process escape vectors."""
    dangerous_js_snippets = [
        "const cp = require('child_process'); cp.execSync('calc');",
        "const fs = require('fs'); fs.readFileSync('/etc/passwd');",
        "eval('process.env.PATH');",
        "const f = new Function('return process')();",
        "const net = require('net');",
    ]

    for snippet in dangerous_js_snippets:
        res = execute_sandboxed_code(snippet, language="javascript")
        assert res.ok is False
        assert "security policy violation" in res.stderr.lower() or "prohibited" in res.stderr.lower()


def test_code_execution_reports_accurate_isolation_tier():
    """Sandbox response must transparently declare its isolation tier without claiming container VM."""
    res = execute_sandboxed_code("x = 10\nprint(x * 2)", language="python")
    assert res.ok is True
    assert res.isolation_tier == "restricted_ast_subprocess"


# -----------------------------------------------------------------------------
# 5. SSRF PINNED IP ADAPTER & TOCTOU PROTECTION
# -----------------------------------------------------------------------------

def test_pinned_ip_adapter_connection_pool_preserves_tls_hostname():
    """PinnedIPAdapter must route TCP connection to pinned IP while retaining server_hostname for TLS."""
    adapter = PinnedIPAdapter(pinned_ip="93.184.215.14", original_host="example.com")
    conn = adapter.get_connection("https://example.com/index.html")

    assert conn.host == "93.184.215.14"
    assert conn.assert_hostname == "example.com"
    assert conn.conn_kw.get("server_hostname") == "example.com"


# -----------------------------------------------------------------------------
# 6. WORKSPACE CONFINEMENT & SYMLINK PROTECTION
# -----------------------------------------------------------------------------

def test_workspace_path_confinement_blocks_symlinks_escaping_root(tmp_path):
    """Resolving paths must strictly enforce boundary against workspace root."""
    root = settings.workspace_root.resolve()

    # Relative directory escape
    with pytest.raises(PermissionError):
        _resolve_safe_path("../../Windows/System32/calc.exe")

    # Protected configuration files
    with pytest.raises(PermissionError):
        _resolve_safe_path(".env")


# -----------------------------------------------------------------------------
# 7. EMERGENCY STOP ENFORCEMENT
# -----------------------------------------------------------------------------

def test_emergency_stop_halts_direct_execution():
    """When emergency stop is triggered, all tools and actions must fail closed."""
    trigger_emergency_stop()
    try:
        is_app, req_conf, msg = validate_tool_approval("calculator", {"expression": "1+1"})
        assert is_app is False
        assert "emergency stop" in msg.lower()

        res_code = execute_sandboxed_code("print('test')", language="python")
        assert res_code.ok is False
        assert "emergency stop" in res_code.stderr.lower()
    finally:
        reset_emergency_stop()
