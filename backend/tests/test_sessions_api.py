from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.memory import memory_store
from app.services.orchestrator import OrchestratorResponse


def test_session_registration_history_reset_and_deletion(monkeypatch):
    client = TestClient(app)
    session_id = str(uuid4())

    async def fake_orchestrate(**kwargs):
        memory_store.append_message(
            kwargs["session_id"],
            "user",
            kwargs["user_text"],
            owner_id=kwargs["owner_id"],
        )
        memory_store.append_message(
            kwargs["session_id"],
            "assistant",
            "Persisted reply",
            owner_id=kwargs["owner_id"],
        )
        return OrchestratorResponse(
            reply="Persisted reply",
            session_id=str(kwargs["session_id"]),
            execution_status="success",
        )

    monkeypatch.setattr("app.api.chat.run_orchestration_async", fake_orchestrate)

    registered = client.post("/api/sessions", json={"sessionId": session_id})
    assert registered.status_code == 200
    response = client.post(
        "/api/chat",
        json={"sessionId": session_id, "text": "Remember this conversation"},
    )
    assert response.status_code == 200

    history = client.get(f"/api/sessions/{session_id}/history")
    assert history.status_code == 200
    assert [message["role"] for message in history.json()] == ["user", "assistant"]

    reset = client.post(f"/api/sessions/{session_id}/reset")
    assert reset.status_code == 200
    assert client.get(f"/api/sessions/{session_id}/history").json() == []

    deleted = client.delete(f"/api/sessions/{session_id}")
    assert deleted.status_code == 200
    assert client.get(f"/api/sessions/{session_id}/history").status_code == 404
