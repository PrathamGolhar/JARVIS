from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.memory import memory_store
from app.services.orchestrator import OrchestratorError, OrchestratorResponse

client = TestClient(app)


def test_chat_returns_reply_and_retains_context(monkeypatch) -> None:
    session_id = uuid4()

    def fake_run_orchestration(sid, user_text, confirmed_action_id=None):
        memory_store.append_message(sid, "user", user_text)
        memory_store.append_message(sid, "assistant", f"reply to {user_text}")
        return OrchestratorResponse(
            reply=f"reply to {user_text}",
            session_id=str(sid),
            turns_retained=1,
        )

    monkeypatch.setattr("app.api.chat.run_orchestration", fake_run_orchestration)

    response = client.post("/api/chat", json={"sessionId": str(session_id), "text": "Hello Jarvis"})
    assert response.status_code == 200

    body = response.json()
    assert body["sessionId"] == str(session_id)
    assert body["reply"] == "reply to Hello Jarvis"

    history = memory_store.get_history(session_id)
    assert len(history) >= 2
    assert history[-2]["content"] == "Hello Jarvis"
    memory_store.clear_session(session_id)


def test_chat_rejects_blank_text() -> None:
    response = client.post("/api/chat", json={"sessionId": str(uuid4()), "text": "   "})
    assert response.status_code == 422


def test_chat_returns_safe_provider_error(monkeypatch) -> None:
    def fake_run_orchestration(sid, user_text, confirmed_action_id=None):
        raise OrchestratorError("Groq API key is not configured.", status_code=503)

    monkeypatch.setattr("app.api.chat.run_orchestration", fake_run_orchestration)
    response = client.post("/api/chat", json={"sessionId": str(uuid4()), "text": "Hello"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Groq API key is not configured."
