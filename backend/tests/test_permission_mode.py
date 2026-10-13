import pytest

from app.services.coding.sandbox import execute_sandboxed_code
from app.services.local_actions import execute_local_action
from app.services.tools.file_tools import write_workspace_file
from app.settings import Settings, settings


def test_permission_mode_read_only_blocks_sandbox(monkeypatch) -> None:
    monkeypatch.setattr(settings, "permission_mode", "read_only")
    res = execute_sandboxed_code("print('test')", language="python")
    assert res.ok is False
    assert "disabled in 'read_only' permission mode" in res.stderr
    assert res.exit_code == 1


def test_permission_mode_read_only_blocks_file_write(monkeypatch) -> None:
    monkeypatch.setattr(settings, "permission_mode", "read_only")
    res = write_workspace_file("test_write.txt", "sample text")
    assert res.get("ok") is False
    assert "disabled in 'read_only' permission mode" in res.get("error", "")


def test_write_workspace_file_blocks_env_file(monkeypatch) -> None:
    monkeypatch.setattr(settings, "permission_mode", "assisted")
    res_env = write_workspace_file(".env", "EXPOSED_KEY=123")
    assert res_env.get("ok") is False
    assert "prohibited for security" in res_env.get("error", "")

    res_env_local = write_workspace_file(".env.local", "EXPOSED_KEY=123")
    assert res_env_local.get("ok") is False
    assert "prohibited for security" in res_env_local.get("error", "")


def test_permission_mode_read_only_blocks_local_action(monkeypatch) -> None:
    monkeypatch.setattr(settings, "permission_mode", "read_only")
    with pytest.raises(RuntimeError) as exc_info:
        execute_local_action("calculator")
    assert "disabled in 'read_only' permission mode" in str(exc_info.value)


def test_permission_mode_supports_safety_tier_alias(monkeypatch) -> None:
    monkeypatch.delenv("JARVIS_PERMISSION_MODE", raising=False)
    monkeypatch.setenv("JARVIS_SAFETY_TIER", "full_control")
    cfg = Settings()
    assert cfg.permission_mode == "full_control"

    monkeypatch.setenv("JARVIS_PERMISSION_MODE", "read_only")
    monkeypatch.setenv("JARVIS_SAFETY_TIER", "full_control")
    cfg2 = Settings()
    # Canonical JARVIS_PERMISSION_MODE takes precedence over alias
    assert cfg2.permission_mode == "read_only"


def test_validate_configuration_sanitizes_credentials() -> None:
    report = settings.validate_configuration()
    assert "environment" in report
    assert "ai_providers" in report
    assert "speech" in report
    assert "database" in report
    assert "features" in report

    # Ensure sensitive raw keys are not exposed in report
    serialized = str(report)
    assert settings.gemini_api_key not in serialized or not settings.gemini_api_key
    assert settings.groq_api_key not in serialized or not settings.groq_api_key
    assert "password" not in serialized.lower() or "***" in serialized
