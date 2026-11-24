import asyncio
import concurrent.futures
from pathlib import Path
import sqlite3
import time
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import pytest

from app.core.errors import ErrorCode, JARVISError, ResourceNotFoundError
from app.main import app
from app.services.ai.health import (
    CircuitBreaker,
    CircuitState,
    ErrorCategory,
    ProviderHealthRecord,
    ProviderStatus,
    provider_health_registry,
)
from app.services.maintenance import clean_stale_files
from app.services.memory.persistent_memory import PersistentMemoryStore
from app.services.tools.registry import execute_tool_call


# -------------------------------------------------------------------------
# 1. Error Architecture & Middleware Contract Tests
# -------------------------------------------------------------------------
def test_tracing_middleware_adds_headers_and_propagates_request_id():
    client = TestClient(app)
    # Provided request ID
    custom_rid = "req_custom_trace_12345"
    response = client.get("/health", headers={"X-Request-ID": custom_rid})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_rid
    assert "X-Response-Time-Ms" in response.headers
    latency = float(response.headers["X-Response-Time-Ms"])
    assert latency >= 0.0

    # Auto-generated request ID
    resp2 = client.get("/health")
    assert resp2.status_code == 200
    assert resp2.headers.get("X-Request-ID") is not None
    assert resp2.headers.get("X-Request-ID").startswith("req_")


def test_centralized_error_handling_contract():
    client = TestClient(app)
    # Unmatched route triggers Starlette 404 handler
    response = client.get("/api/nonexistent-endpoint-xyz-987")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert data["error"]["statusCode"] == 404
    assert "requestId" in data["error"]


def test_custom_jarvis_error_structure():
    err = ResourceNotFoundError("Document", "doc_123")
    assert err.error_code == ErrorCode.NOT_FOUND
    assert err.status_code == 404
    assert err.details == {"resource_type": "Document", "identifier": "doc_123"}


# -------------------------------------------------------------------------
# 2. Database Concurrency, WAL Mode & Recovery Tests
# -------------------------------------------------------------------------
def test_sqlite_wal_pragmas_and_concurrency(tmp_path: Path):
    db_file = tmp_path / "test_concurrency.db"
    store = PersistentMemoryStore(db_path=str(db_file))

    # Verify PRAGMAs
    with sqlite3.connect(str(db_file)) as conn:
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
        # In SQLite, WAL pragma returns 'wal'
        assert journal_mode.lower() == "wal"
        assert busy_timeout >= 5000

    # Test concurrent writes across threads
    def write_turn(thread_idx: int):
        thread_store = PersistentMemoryStore(db_path=str(db_file))
        for i in range(10):
            thread_store.append_message(f"session_{thread_idx}", "user", f"Message {i} from thread {thread_idx}")
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(write_turn, idx) for idx in range(5)]
        results = [f.result() for f in futures]
    assert all(results)

    # Verify all 50 messages were persisted
    with store.transaction() as conn:
        count = conn.execute("SELECT count(*) FROM messages;").fetchone()[0]
        assert count == 50


def test_sqlite_live_backup_and_recovery(tmp_path: Path):
    db_file = tmp_path / "primary.db"
    backup_file = tmp_path / "backup.db"

    store = PersistentMemoryStore(db_path=str(db_file))
    store.append_message("sess_1", "user", "Hello backup test")
    store.set_memory("pref_tone", "concise")

    # Perform zero-downtime online backup
    store.backup_database(backup_file)
    assert backup_file.exists()
    assert backup_file.stat().st_size > 0

    # Verify backup integrity
    backup_store = PersistentMemoryStore(db_path=str(backup_file))
    hist = backup_store.get_history("sess_1")
    assert len(hist) == 1
    assert hist[0]["content"] == "Hello backup test"
    assert backup_store.get_memory("pref_tone") == "concise"


# -------------------------------------------------------------------------
# 3. Provider Reliability & Circuit Breaker Tests
# -------------------------------------------------------------------------
def test_circuit_breaker_tripping_and_recovery():
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.2)

    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # Record 2 failures: still closed
    cb.record_failure(ErrorCategory.SERVER_ERROR)
    cb.record_failure(ErrorCategory.SERVER_ERROR)
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # Record 3rd failure: trips to OPEN
    cb.record_failure(ErrorCategory.SERVER_ERROR)
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # Wait for cooldown
    time.sleep(0.25)
    # Transitions to HALF_OPEN probe
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Success in HALF_OPEN resets to CLOSED
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True


def test_provider_health_registry_circuit_breaker_integration():
    record = provider_health_registry.get("test_provider_cb")
    record.configured = True
    record.circuit_breaker.failure_threshold = 3

    assert record.can_execute() is True

    record.record_failure(ErrorCategory.SERVER_ERROR, "500 Internal Server Error")
    record.record_failure(ErrorCategory.SERVER_ERROR, "500 Internal Server Error")
    record.record_failure(ErrorCategory.SERVER_ERROR, "500 Internal Server Error")

    assert record.circuit_breaker.state == CircuitState.OPEN
    assert record.can_execute() is False
    assert record.status == ProviderStatus.DEGRADED


# -------------------------------------------------------------------------
# 4. Tool Registry Reliability, Timeouts & Tracing
# -------------------------------------------------------------------------
def test_tool_execution_timeout_protection():
    # Test calculator tool timing out when timeout is artificially low
    with patch("app.services.tools.registry._dispatch_tool") as mock_dispatch:
        def slow_dispatch(*args, **kwargs):
            time.sleep(0.5)
            return {"ok": True, "result": 42}
        mock_dispatch.side_effect = slow_dispatch

        result = execute_tool_call(
            "calculator",
            {"expression": "2+2"},
            timeout_seconds=0.1,
        )
        assert result["ok"] is False
        assert "timed out" in result["error"].lower()
        assert "traceId" in result
        assert "executionTimeMs" in result


def test_tool_execution_schema_tracing_and_result_envelope():
    result = execute_tool_call(
        "calculator",
        {"expression": "100 / 4"},
    )
    assert result["ok"] is True
    assert result["result"] == 25.0
    assert "traceId" in result
    assert result["traceId"].startswith("tool_")
    assert "executionTimeMs" in result
    assert isinstance(result["executionTimeMs"], float)


# -------------------------------------------------------------------------
# 5. Maintenance Disk Hygiene Tests
# -------------------------------------------------------------------------
def test_maintenance_clean_stale_files(tmp_path: Path):
    test_dir = tmp_path / "stale_test"
    test_dir.mkdir()

    fresh_file = test_dir / "fresh.pdf"
    fresh_file.write_text("fresh content")

    stale_file = test_dir / "old.pdf"
    stale_file.write_text("old content")
    # Backdate stale_file mtime to 10 days ago
    old_mtime = time.time() - (10 * 86400)
    import os
    os.utime(str(stale_file), (old_mtime, old_mtime))

    summary = clean_stale_files(target_dir=test_dir, max_age_days=7)
    assert summary.files_removed == 1
    assert summary.bytes_reclaimed > 0
    assert fresh_file.exists()
    assert not stale_file.exists()
