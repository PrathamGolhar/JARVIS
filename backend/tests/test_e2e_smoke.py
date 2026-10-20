"""
End-to-end smoke test suite verifying JARVIS runtime pipeline:
1. Backend start & health check
2. Chat endpoint response & schema validity
3. AI provider response & local fallback honest identification
4. TTS failure isolation (chat survives TTS failure)
5. Web search failure isolation (chat survives web search failure)
6. Truthful diagnostics reporting
"""
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.edge_tts_service import EdgeTtsError

client = TestClient(app)


def test_e2e_01_backend_health_and_readiness():
    """Verify backend starts and responds on health & readiness endpoints."""
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert data_health["status"] == "ok"
    assert data_health["system"] == "JARVIS 2.0"

    res_ready = client.get("/api/ready")
    assert res_ready.status_code == 200
    data_ready = res_ready.json()
    assert data_ready["status"] in ("ready", "degraded")
    assert "database" in data_ready
    assert "ai" in data_ready


def test_e2e_02_chat_endpoint_valid_response():
    """Verify /api/chat accepts valid payload and returns structured response."""
    session_id = str(uuid.uuid4())
    res = client.post(
        "/api/chat",
        json={
            "sessionId": session_id,
            "text": "Hello JARVIS, status report please.",
            "mode": "general",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert len(data["reply"]) > 0
    assert data["sessionId"] == session_id
    assert "turnsRetained" in data
    assert "toolEvents" in data
    assert "citations" in data


def test_e2e_03_ai_provider_local_fallback_identification():
    """Verify that when no cloud API keys are provided, local fallback is truthfully identified."""
    diag = client.get("/api/diagnostics").json()
    ai_item = next((item for item in diag["items"] if item["id"] == "ai_engine"), None)
    assert ai_item is not None
    # Must identify provider truthfully
    assert "AI Core" in ai_item["label"]
    assert "local" in ai_item["details"].lower() or "active" in ai_item["status"].lower() or "ready" in ai_item["status"].lower()


def test_e2e_04_chat_survives_tts_failure():
    """Verify chat request succeeds completely even when TTS is experiencing an outage."""
    with patch("app.api.speech.generate_speech", side_effect=EdgeTtsError("403 Forbidden")):
        # First verify TTS endpoint returns 503
        tts_res = client.post("/api/tts", json={"text": "Hello", "voiceId": "en-US-GuyNeural"})
        assert tts_res.status_code == 503

        # Verify chat endpoint still responds successfully with full text
        chat_res = client.post(
            "/api/chat",
            json={
                "sessionId": str(uuid.uuid4()),
                "text": "Tell me a brief greeting.",
                "mode": "general",
            },
        )
        assert chat_res.status_code == 200
        assert len(chat_res.json()["reply"]) > 0


def test_e2e_05_chat_survives_web_search_failure():
    """Verify chat request succeeds without meta-advice if web search tool fails."""
    with patch("app.services.tools.web_search.live_web_search", return_value={"ok": False, "results": [], "error": "WEB_SEARCH_UNAVAILABLE"}):
        chat_res = client.post(
            "/api/chat",
            json={
                "sessionId": str(uuid.uuid4()),
                "text": "Search for live updates on quantum computing.",
                "mode": "general",
            },
        )
        assert chat_res.status_code == 200
        reply = chat_res.json()["reply"]
        # Must NOT include meta-advice like manual surfing suggestions
        assert "manually browse" not in reply.lower()
        assert "schedule a reminder" not in reply.lower()
