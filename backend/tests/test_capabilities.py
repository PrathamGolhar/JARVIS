from fastapi.testclient import TestClient
from app.main import app
from app.services.permissions import (
    APPROVED_CAPABILITIES,
    get_capability_status,
    is_capability_approved,
    validate_tool_approval,
)

client = TestClient(app)


def test_list_capabilities_endpoint() -> None:
    response = client.get("/api/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(APPROVED_CAPABILITIES)

    cap_names = [c["name"] for c in data]
    assert "voice.microphone.listen" in cap_names
    assert "voice.speech.stream" in cap_names
    assert "voice.speech.interim" in cap_names
    assert "voice.speech.final" in cap_names
    assert "ai.response.generate" in cap_names
    assert "web.search" in cap_names
    assert "files.write" in cap_names
    assert "desktop.open_application" in cap_names
    assert "tts.playback" in cap_names
    assert "visualizer.audio_reactive" in cap_names


def test_check_approved_capability() -> None:
    response = client.post("/api/capabilities/check", json={"capability": "web.search"})
    assert response.status_code == 200
    data = response.json()
    assert data["approved"] is True
    assert data["requiresConfirmation"] is False
    assert data["status"] == "approved"


def test_check_sensitive_capability_requires_confirmation() -> None:
    response = client.post("/api/capabilities/check", json={"capability": "files.write"})
    assert response.status_code == 200
    data = response.json()
    assert data["approved"] is True
    assert data["requiresConfirmation"] is True
    assert data["status"] == "requires_confirmation"


def test_reject_wildcards_and_unauthorized_capabilities() -> None:
    # Wildcards must never be approved
    assert is_capability_approved("*") is False
    assert is_capability_approved("all") is False
    assert is_capability_approved("allowAll") is False
    assert is_capability_approved("admin_everything") is False
    assert is_capability_approved("system_all") is False

    res = client.post("/api/capabilities/check", json={"capability": "*"})
    assert res.status_code == 200
    assert res.json()["approved"] is False
    assert res.json()["status"] == "denied"


def test_tool_capability_validation() -> None:
    # Legitimate tool validation
    is_approved, requires_conf, msg = validate_tool_approval("web_search")
    assert is_approved is True
    assert requires_conf is False
    assert "approved" in msg

    is_approved, requires_conf, msg = validate_tool_approval("write_file")
    assert is_approved is True
    assert requires_conf is True
    assert "requires explicit user confirmation" in msg

    # Fake or unapproved tool validation
    is_approved, requires_conf, msg = validate_tool_approval("execute_arbitrary_code")
    assert is_approved is False
    assert requires_conf is False
    assert "not in the approved capabilities registry" in msg
