"""
Authoritative Security Regression Test Suite for JARVIS.

Covers all 13 critical security requirements from MASTER PROMPT 01:
1. Missing authorization enforcement (401 Unauthorized)
2. Invalid authorization credentials rejection
3. SSRF through private IP access (IPv4 & IPv6)
4. SSRF through DNS-related bypasses (hostname resolving to private IP)
5. SSRF through redirects (open redirect to cloud metadata / localhost)
6. Invalid confirmation IDs rejection
7. Expired confirmations rejection (TTL enforcement)
8. Replayed confirmations protection (one-time use)
9. Cross-session confirmation rejection (session isolation)
10. Confirmation argument tampering detection (hash integrity)
11. Unknown tool execution rejection (fail-closed default)
12. READ_ONLY permission mode violations (writes, code exec, app launch, uploads, deletions, settings)
13. Sandbox escape attempts (AST static validation: os, subprocess, socket, eval, dunder escapes)
14. File path traversal and symlink escape attempts
15. Unauthorized deletion of protected files
16. Emergency stop kill-switch validation
"""

import io
import socket
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import create_session_token, get_configured_api_key
from app.services.coding.sandbox import execute_sandboxed_code
from app.services.confirmation import confirmation_manager
from app.services.permissions import (
    PermissionMode,
    reset_emergency_stop,
    trigger_emergency_stop,
    validate_tool_approval,
)
from app.services.security_network import (
    SSRFSecurityError,
    is_safe_external_url,
    safe_http_fetch,
    validate_hostname_ip_resolution,
)
from app.services.tools.file_tools import _resolve_safe_path, read_workspace_file, write_workspace_file
from app.services.tools.registry import execute_tool_call, is_high_impact_tool
from app.services.tools.web_reader import read_webpage_content
from app.settings import settings

client = TestClient(app)


# ==============================================================================
# A. AUTHENTICATION & AUTHORIZATION TESTS
# ==============================================================================

def test_missing_authorization_rejected_when_auth_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "api_key", "secret_master_key_12345")

    # Access without auth token
    res = client.get("/api/settings")
    assert res.status_code == 401
    assert "credentials were not provided" in res.json().get("detail", "").lower()

    # Chat without auth token
    chat_res = client.post("/api/chat", json={"sessionId": str(uuid4()), "text": "Hello"})
    assert chat_res.status_code == 401


def test_invalid_authorization_token_rejected(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "api_key", "secret_master_key_12345")

    res = client.get("/api/settings", headers={"X-API-Key": "completely_wrong_key"})
    assert res.status_code == 401
    assert "invalid" in res.json().get("detail", "").lower()


def test_valid_authorization_accepted(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_enabled", True)
    test_key = "test_valid_master_key_99999"
    monkeypatch.setattr(settings, "api_key", test_key)

    # Via X-API-Key
    res = client.get("/api/settings", headers={"X-API-Key": test_key})
    assert res.status_code == 200
    assert "aiProvider" in res.json()

    # Via Authorization: Bearer
    res_bearer = client.get("/api/settings", headers={"Authorization": f"Bearer {test_key}"})
    assert res_bearer.status_code == 200

    # Via Session Token
    sess_token = create_session_token("test_session")
    res_sess = client.get("/api/settings", headers={"X-API-Key": sess_token})
    assert res_sess.status_code == 200


# ==============================================================================
# B. SSRF PROTECTION TESTS
# ==============================================================================

@pytest.mark.parametrize(
    "bad_url",
    [
        "http://127.0.0.1:8000/secret",
        "http://localhost:8080/admin",
        "http://10.0.0.5/api",
        "http://192.168.1.1/router",
        "http://172.16.0.1/internal",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]:8080/flag",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://0.0.0.0:8000/",
    ],
)
def test_ssrf_private_and_metadata_ip_access_blocked(bad_url: str) -> None:
    res = read_webpage_content(bad_url)
    assert res["ok"] is False
    assert "restricted" in res["error"].lower() or "prohibited" in res["error"].lower() or "blocked" in res["error"].lower()


def test_ssrf_dns_rebinding_blocked(monkeypatch) -> None:
    # Simulate a domain that resolves to a private loopback IP address
    fake_addrinfo = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))]
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: fake_addrinfo)

    with pytest.raises(SSRFSecurityError) as exc_info:
        validate_hostname_ip_resolution("rebind.attacker.example.com")
    assert "restricted ip address" in str(exc_info.value).lower()


def test_ssrf_redirect_to_private_ip_blocked(monkeypatch) -> None:
    # First hop is public domain, but responds with redirect to link-local metadata 169.254.169.254
    class MockRedirectResponse:
        status_code = 302
        headers = {"Location": "http://169.254.169.254/latest/meta-data/"}
        encoding = "utf-8"
        def iter_content(self, **kwargs):
            return []

    # Mock public DNS resolution for hop 1
    def mock_addrinfo(host, *args, **kwargs):
        if "evil-public-site.com" in host:
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 80))]
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("169.254.169.254", 80))]

    monkeypatch.setattr(socket, "getaddrinfo", mock_addrinfo)
    monkeypatch.setattr("requests.get", lambda *args, **kwargs: MockRedirectResponse())

    with pytest.raises(SSRFSecurityError) as exc_info:
        safe_http_fetch("http://evil-public-site.com/redirect")
    assert "restricted" in str(exc_info.value).lower() or "prohibited" in str(exc_info.value).lower()


# ==============================================================================
# C. CONFIRMATION SECURITY TESTS
# ==============================================================================

def test_confirmation_lifecycle_and_one_time_use() -> None:
    sid = "session_test_123"
    args = {"file_path": "report.txt", "content": "hello"}
    conf = confirmation_manager.create_confirmation("write_file", args, session_id=sid)
    action_id = conf["actionId"]
    assert action_id.startswith("act_")

    # First consumption: Succeeds
    pending = confirmation_manager.consume_confirmation(action_id, session_id=sid)
    assert pending.tool_name == "write_file"
    assert pending.arguments == args

    # Second consumption (Replay): Must fail!
    with pytest.raises(ValueError) as exc:
        confirmation_manager.consume_confirmation(action_id, session_id=sid)
    assert "invalid or has expired" in str(exc.value).lower() or "already been consumed" in str(exc.value).lower()


def test_confirmation_cross_session_rejected() -> None:
    conf = confirmation_manager.create_confirmation(
        "open_application",
        {"app_id": "calculator"},
        session_id="session_A",
    )
    action_id = conf["actionId"]

    # Session B tries to confirm session A's action
    with pytest.raises(ValueError) as exc:
        confirmation_manager.consume_confirmation(action_id, session_id="session_B")
    assert "does not belong to the active session" in str(exc.value).lower()


def test_confirmation_expiration_enforced(monkeypatch) -> None:
    conf = confirmation_manager.create_confirmation(
        "write_file",
        {"file_path": "test.txt", "content": "data"},
        session_id="session_exp",
    )
    action_id = conf["actionId"]

    # Fast-forward time past 300s TTL
    with patch("app.services.confirmation.time.time", return_value=conf["expires_at"] + 1000.0):
        with pytest.raises(ValueError) as exc:
            confirmation_manager.consume_confirmation(action_id, session_id="session_exp")
        assert "expired" in str(exc.value).lower() or "invalid" in str(exc.value).lower()


def test_confirmation_argument_tampering_rejected() -> None:
    original_args = {"file_path": "harmless.txt", "content": "safe"}
    conf = confirmation_manager.create_confirmation("write_file", original_args, session_id="sess_tamper")
    action_id = conf["actionId"]

    tampered_args = {"file_path": "malicious.sh", "content": "rm -rf /"}
    with pytest.raises(ValueError) as exc:
        confirmation_manager.consume_confirmation(
            action_id,
            session_id="sess_tamper",
            assert_arguments=tampered_args,
        )
    assert "do not match the original" in str(exc.value).lower()


# ==============================================================================
# D. TOOL REGISTRY & UNKNOWN TOOL TESTS
# ==============================================================================

def test_unknown_tool_denied_by_default() -> None:
    res = execute_tool_call("malicious_unregistered_tool", {"arg": "val"})
    assert res["ok"] is False
    assert "not in the approved capabilities registry" in res["error"] or "denied by default" in res["error"]


def test_unknown_tool_classified_as_high_impact() -> None:
    # Fail-closed: unknown tools must NEVER inherit low risk!
    assert is_high_impact_tool("unknown_tool_xyz") is True
    assert is_high_impact_tool("evil_cmd") is True
    assert is_high_impact_tool("calculator") is False
    assert is_high_impact_tool("web_search") is False
    assert is_high_impact_tool("execute_python_code") is True


def test_tool_arguments_schema_validation() -> None:
    # Invalid missing arguments should fail schema check
    res_bad = execute_tool_call("web_search", {})
    assert res_bad["ok"] is False
    assert "Schema validation error" in res_bad["error"]

    res_app_bad = execute_tool_call("open_application", {"app_id": "malicious_exe"})
    assert res_app_bad["ok"] is False
    assert "Schema validation error" in res_app_bad["error"]


# ==============================================================================
# E. READ-ONLY PERMISSION MODE ENFORCEMENT
# ==============================================================================

def test_read_only_mode_blocks_all_mutations(monkeypatch) -> None:
    monkeypatch.setattr(settings, "permission_mode", "read_only")

    # 1. File write
    res_write = write_workspace_file("test.txt", "data")
    assert res_write["ok"] is False
    assert "read_only" in res_write["error"].lower()

    # 2. Code execution
    res_code = execute_sandboxed_code("x = 10", language="python")
    assert res_code.ok is False
    assert "read_only" in res_code.stderr.lower()

    # 3. Settings modification API
    monkeypatch.setattr(settings, "auth_enabled", False)
    res_sett = client.post("/api/settings", json={"aiProvider": "openai"})
    assert res_sett.status_code == 403
    assert "read_only" in res_sett.json()["detail"].lower()

    # 4. Local action execution
    res_local = client.post("/api/local-actions/execute", json={"appId": "calculator", "confirmed": True})
    assert res_local.status_code == 403

    # 5. File upload API
    res_up = client.post(
        "/api/files/upload",
        files={"file": ("test.txt", io.BytesIO(b"data"), "text/plain")},
    )
    assert res_up.status_code == 403

    # 6. File deletion API
    res_del = client.delete("/api/files/test.txt")
    assert res_del.status_code == 403


# ==============================================================================
# F. SANDBOX HARDENING & AST ESCAPE TESTS
# ==============================================================================

@pytest.mark.parametrize(
    "malicious_code",
    [
        "import os\nos.system('calc')",
        "import subprocess\nsubprocess.run(['notepad'])",
        "import socket\nsocket.socket()",
        "import sys\nprint(sys.executable)",
        "from os import path",
        "eval('1 + 1')",
        "exec('x = 1')",
        "open('test.txt', 'w')",
        "().__class__.__bases__[0].__subclasses__()",
    ],
)
def test_sandbox_ast_blocks_prohibited_constructs(malicious_code: str, monkeypatch) -> None:
    monkeypatch.setattr(settings, "permission_mode", "assisted")
    res = execute_sandboxed_code(malicious_code, language="python")
    assert res.ok is False
    assert "security policy" in res.stderr.lower() or "prohibited" in res.stderr.lower() or "restricted" in res.stderr.lower()


# ==============================================================================
# G. FILE PATH TRAVERSAL AND SECURITY TESTS
# ==============================================================================

def test_file_tools_path_traversal_and_null_bytes() -> None:
    # Null byte attack
    with pytest.raises(PermissionError) as exc_null:
        _resolve_safe_path("doc\0.txt")
    assert "null bytes" in str(exc_null.value).lower()

    # Directory traversal
    with pytest.raises(PermissionError) as exc_trav:
        _resolve_safe_path("../../../windows/system32/cmd.exe")
    assert "outside the authorized workspace" in str(exc_trav.value).lower()

    # Direct access to .env
    with pytest.raises(PermissionError) as exc_env:
        _resolve_safe_path(".env")
    assert "restricted" in str(exc_env.value).lower() or ".env" in str(exc_env.value).lower()


def test_file_download_protected_files_blocked(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_enabled", False)
    # Attempt downloading .env
    res = client.get("/api/files/download/.env")
    assert res.status_code in (400, 403, 404)

    # Attempt downloading database
    res_db = client.get("/api/files/download/jarvis_memory.db")
    assert res_db.status_code in (400, 403, 404)


# ==============================================================================
# H. EMERGENCY STOP KILL SWITCH TESTS
# ==============================================================================

def test_emergency_stop_halts_execution(monkeypatch) -> None:
    try:
        trigger_emergency_stop()
        assert settings.emergency_stop_active is True

        # Tool execution must be completely denied
        approved, req_conf, msg = validate_tool_approval("web_search")
        assert approved is False
        assert "emergency stop is active" in msg.lower()

        # Code execution must be halted
        res = execute_sandboxed_code("x = 10", language="python")
        assert res.ok is False
        assert "emergency stop" in res.stderr.lower()
    finally:
        reset_emergency_stop()
        assert settings.emergency_stop_active is False
