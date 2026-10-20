from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ResearchResponse
from app.services.ai.base import ToolCall
from app.services.ai.local_provider import LocalProvider
from app.services.diagnostics_service import get_deep_diagnostics
from app.services.edge_tts_service import EdgeTtsError
from app.services.tools.web_search import live_web_search

client = TestClient(app)


def test_research_response_properties_prevent_attribute_error():
    """Verify ResearchResponse supports both snake_case and camelCase attributes."""
    resp = ResearchResponse(
        topic="AI Advancements",
        summary="A summary of AI",
        findingsMarkdown="# AI Advancements\n\nContent here.",
        citations=[],
        keyTakeaways=["Key point 1"],
    )
    assert resp.findings_markdown == "# AI Advancements\n\nContent here."
    assert resp.findingsMarkdown == "# AI Advancements\n\nContent here."
    assert resp.key_takeaways == ["Key point 1"]
    assert resp.keyTakeaways == ["Key point 1"]


def test_edge_tts_failure_returns_503_without_crashing_server():
    """Verify that if Edge TTS encounters an upstream error, /api/tts returns 503 with details."""
    with patch("app.api.speech.generate_speech", side_effect=EdgeTtsError("403 Invalid response status")):
        response = client.post("/api/tts", json={"text": "Hello, Master.", "voiceId": "en-US-GuyNeural"})
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert "unavailable" in data["detail"].lower() or "403" in data["detail"]


def test_local_provider_synthesizes_web_search_results():
    """Verify LocalProvider synthesizes web search results without infinite tool loops."""
    provider = LocalProvider()
    messages = [
        {"role": "user", "content": "search for Python programming"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1", "function": {"name": "web_search"}}]},
        {
            "role": "tool",
            "name": "web_search",
            "content": '{"ok": true, "results": [{"title": "Python.org", "url": "https://python.org", "snippet": "Official site"}]}',
        },
    ]
    res = provider.chat(messages=messages)
    assert res.content
    assert "Python.org" in res.content
    assert len(res.tool_calls) == 0


def test_local_provider_handles_web_search_unavailable_gracefully():
    """Verify LocalProvider returns clean fallback message when web search returns 0 results."""
    provider = LocalProvider()
    messages = [
        {"role": "user", "content": "search for current news"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "call_2", "function": {"name": "web_search"}}]},
        {
            "role": "tool",
            "name": "web_search",
            "content": '{"ok": false, "results": [], "error": "WEB_SEARCH_UNAVAILABLE"}',
        },
    ]
    res = provider.chat(messages=messages)
    assert "Web research is temporarily unavailable" in res.content
    assert len(res.tool_calls) == 0


def test_diagnostics_reports_truthful_subsystems():
    """Verify get_deep_diagnostics reports all required subsystems with accurate states."""
    diag = get_deep_diagnostics()
    assert diag.ok is True
    assert len(diag.items) >= 9

    item_ids = {it.id: it for it in diag.items}
    for required_id in ["backend", "database", "ai_engine", "memory", "network", "tts", "stt", "tools", "sandbox"]:
        assert required_id in item_ids, f"Missing required subsystem diagnostic: {required_id}"

    # Verify AI Provider truthfully identifies engine
    ai_item = item_ids["ai_engine"]
    assert "AI Core" in ai_item.label


def test_web_search_returns_structured_fallback_on_empty():
    """Verify live_web_search returns structured error rather than crashing on empty query."""
    res = live_web_search("")
    assert res["ok"] is False
    assert res["error"] == "EMPTY_QUERY"
