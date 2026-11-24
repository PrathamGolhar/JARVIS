import asyncio
import io
from pathlib import Path
import time
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.ai.base import AIChatResponse
from app.services.ai.factory import execute_with_failover
from app.services.ai.health import CircuitBreaker, CircuitState, ErrorCategory, provider_health_registry
from app.services.memory import memory_store
from app.services.memory.vector_store import rag_store
from app.services.permissions import validate_tool_approval
from app.services.tools.registry import execute_tool_call


client = TestClient(app)


# -------------------------------------------------------------------------
# Workflow 1 & 2: Normal Conversation & Direct Intent
# -------------------------------------------------------------------------
def test_workflow_normal_conversation_and_direct_intent():
    sid = str(uuid4())
    resp = client.post("/api/chat", json={"text": "Hello JARVIS, good morning!", "sessionId": sid})
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert data["mode"] == "general"
    assert len(data.get("toolEvents", [])) == 0  # No tool calls needed for simple greeting


# -------------------------------------------------------------------------
# Workflow 3: Web Research with Citations
# -------------------------------------------------------------------------
def test_workflow_web_research_tool_execution():
    with patch("app.services.tools.registry.live_web_search") as mock_search:
        mock_search.return_value = {
            "ok": True,
            "query": "artificial intelligence",
            "results": [
                {"title": "AI Overview", "url": "https://example.com/ai", "domain": "example.com", "snippet": "Overview"},
            ],
        }
        res = execute_tool_call("web_search", {"query": "artificial intelligence"})
        assert res["ok"] is True
        assert len(res["results"]) == 1
        assert res["results"][0]["url"] == "https://example.com/ai"


# -------------------------------------------------------------------------
# Workflow 4 & 5: Document Upload, Indexing, and RAG Retrieval
# -------------------------------------------------------------------------
def test_workflow_document_upload_and_rag(tmp_path: Path):
    session_id = str(uuid4())
    registered = client.post("/api/sessions", json={"sessionId": session_id})
    assert registered.status_code == 200
    file_content = b"Technical Whitepaper: System architecture uses SQLite WAL mode for fast concurrency."
    response = client.post(
        f"/api/files/upload?session_id={session_id}",
        files={"file": ("whitepaper.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert response.status_code == 200
    upload_data = response.json()
    assert upload_data["ok"] is True
    file_id = upload_data["fileId"]

    # Query RAG store scoped to the session
    matches = rag_store.search("concurrency WAL mode", session_id=session_id)
    assert len(matches) > 0
    assert "whitepaper.txt" in matches[0]["filename"]
    stored_name = f"{file_id}_whitepaper.txt"
    deleted = client.delete(f"/api/files/{stored_name}")
    assert deleted.status_code == 200
    assert rag_store.search("concurrency WAL mode", session_id=session_id) == []
    assert client.delete(f"/api/sessions/{session_id}").status_code == 200


# -------------------------------------------------------------------------
# Workflow 7 & 8: PDF & PowerPoint Document Generation
# -------------------------------------------------------------------------
def test_workflow_document_generation_pdf():
    res = execute_tool_call(
        "generate_pdf_report",
        {"title": "Q3 Performance", "content_markdown": "# Results\nSubstantive metrics exceeded targets."},
    )
    assert res["ok"] is True
    assert "file" in res
    assert res["file"]["filename"].endswith(".pdf")


# -------------------------------------------------------------------------
# Workflow 9: Coding and Sandbox Execution
# -------------------------------------------------------------------------
def test_workflow_coding_sandbox_safe_and_unsafe():
    # Safe computation
    safe_res = execute_tool_call("execute_python_code", {"code": "x = [i**2 for i in range(5)]\nprint(x)"})
    assert safe_res["ok"] is True
    assert "[0, 1, 4, 9, 16]" in safe_res["stdout"]

    # Blocked unsafe call (OS traversal)
    unsafe_res = execute_tool_call("execute_python_code", {"code": "import os\nos.listdir('.')"})
    assert unsafe_res["ok"] is False
    error_msg = unsafe_res.get("error") or unsafe_res.get("stderr") or ""
    assert "prohibited" in error_msg.lower() or "violation" in error_msg.lower()


# -------------------------------------------------------------------------
# Workflow 10: Memory Creation & Retrieval
# -------------------------------------------------------------------------
def test_workflow_memory_set_and_get():
    item_res = memory_store.set_memory("preferred_code_language", "Python")
    item = item_res[0] if isinstance(item_res, tuple) else item_res
    assert item.key == "preferred_code_language"
    assert memory_store.get_memory("preferred_code_language") == "Python"


# -------------------------------------------------------------------------
# Workflow 12: Reminder Creation
# -------------------------------------------------------------------------
def test_workflow_create_reminder():
    res = execute_tool_call("create_reminder", {"title": "Deploy v2.0", "scheduled_time": "Tomorrow at 9 AM"})
    assert res["ok"] is True
    assert "reminder" in res
    assert res["reminder"]["title"] == "Deploy v2.0"


# -------------------------------------------------------------------------
# Workflow 14: Provider Failure, Circuit Breaker, and Fallback
# -------------------------------------------------------------------------
def test_workflow_provider_failure_and_fallback():
    # Simulate Gemini 503 outage
    with patch("app.services.ai.gemini_provider.GeminiProvider.is_available", return_value=True), \
         patch("app.services.ai.gemini_provider.GeminiProvider.chat", side_effect=RuntimeError("503 Backend Overload")), \
         patch("app.services.ai.groq_provider.GroqProvider.is_available", return_value=True), \
         patch("app.services.ai.groq_provider.GroqProvider.chat", return_value=AIChatResponse(content="Fallback response", tool_calls=[])):

        res, prov = execute_with_failover(messages=[{"role": "user", "content": "hi"}], user_override="auto")
        assert prov == "groq"
        assert res.content == "Fallback response"


# -------------------------------------------------------------------------
# Workflow 15: Permission Denied Actions & Confirmation Flow
# -------------------------------------------------------------------------
def test_workflow_permission_denied_in_readonly_mode(monkeypatch):
    monkeypatch.setattr("app.settings.settings.permission_mode", "read_only")
    is_app, req_conf, msg = validate_tool_approval("write_file", {"file_path": "test.txt", "content": "data"})
    assert is_app is False
    assert "read_only" in msg.lower()


# -------------------------------------------------------------------------
# Failure Testing: Missing Key, Invalid Token, Malformed Arguments
# -------------------------------------------------------------------------
def test_failure_invalid_confirmation_token():
    sid = str(uuid4())
    resp = client.post("/api/chat", json={"text": "proceed", "sessionId": sid, "confirmedActionId": "act_nonexistent_999"})
    assert resp.status_code in (404, 400)


def test_failure_malformed_tool_arguments():
    res = execute_tool_call("calculator", "{not valid json")
    assert res["ok"] is False
    assert "invalid json" in res["error"].lower()
