import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.memory.persistent_memory import PersistentMemoryStore


@pytest.fixture
def store(tmp_path):
    return PersistentMemoryStore(str(tmp_path / "test_memory.db"))


def test_memory_store_set_get_list_delete(store):
    saved = store.set_memory("  Test_Pref_Robotics  ", "  Arduino and ROS2 platform  ", "Project")
    assert saved.key == "test_pref_robotics"
    assert saved.value == "Arduino and ROS2 platform"
    assert saved.category == "project"
    assert store.get_memory("TEST_PREF_ROBOTICS") == "Arduino and ROS2 platform"
    assert store.list_memories() == [saved]
    assert store.delete_memory("TEST_PREF_ROBOTICS") is True
    assert store.get_memory("test_pref_robotics") is None
    assert store.delete_memory("missing") is False


def test_memory_upsert_preserves_single_row(store):
    store.set_memory("preferred_editor", "VS Code", "preference")
    updated = store.set_memory("PREFERRED_EDITOR", "Neovim", "workflow")
    assert updated.value == "Neovim"
    assert len(store.list_memories()) == 1
    assert store.get_memory("preferred_editor") == "Neovim"


@pytest.mark.parametrize(
    ("key", "value", "category"),
    [
        (" ", "valid", "general"),
        ("key", "  ", "general"),
        ("key", "value", " " * 41),
        ("k" * 161, "value", "general"),
        ("key", "v" * 10_001, "general"),
    ],
)
def test_memory_validation_rejects_invalid_values(store, key, value, category):
    with pytest.raises(ValueError):
        store.set_memory(key, value, category)


def test_legacy_database_migrates_without_losing_rows(tmp_path):
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE memories (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute(
            "INSERT INTO memories (key, value) VALUES (?, ?)",
            ("favorite_language", "Python"),
        )
        conn.execute(
            "CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, "
            "role TEXT NOT NULL, content TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            ("session-1", "user", "Keep this conversation"),
        )

    migrated = PersistentMemoryStore(str(db_path))
    assert migrated.get_memory("favorite_language") == "Python"
    item = migrated.list_memories()[0]
    assert item.category == "general"
    assert item.updated_at
    assert migrated.get_history("session-1") == [
        {"role": "user", "content": "Keep this conversation"}
    ]

    # Initialization is idempotent and leaves the migrated data available.
    PersistentMemoryStore(str(db_path))
    assert migrated.get_memory("favorite_language") == "Python"


def test_future_schema_version_fails_loudly(tmp_path):
    db_path = tmp_path / "future.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA user_version = 999")
    with pytest.raises(RuntimeError, match="newer than this JARVIS build supports"):
        PersistentMemoryStore(str(db_path))


def test_conversation_history_is_isolated_and_ordered(store):
    store.append_message("session-a", "user", "first")
    store.append_message("session-a", "assistant", "second")
    store.append_message("session-b", "user", "other session")
    assert store.get_history("session-a") == [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "second"},
    ]
    store.clear_session("session-a")
    assert store.get_history("session-a") == []
    assert store.get_history("session-b") == [{"role": "user", "content": "other session"}]


def test_memory_api_crud(monkeypatch, tmp_path):
    from app.api import memory as memory_api

    isolated_store = PersistentMemoryStore(str(tmp_path / "api_memory.db"))
    monkeypatch.setattr(memory_api, "memory_store", isolated_store)
    client = TestClient(app)

    created = client.post(
        "/api/memory",
        json={"key": "  preferred_board  ", "value": "ESP32", "category": "preference"},
    )
    assert created.status_code == 200
    assert created.json()["key"] == "preferred_board"

    fetched = client.get("/api/memory/preferred_board")
    assert fetched.status_code == 200
    assert fetched.json()["value"] == "ESP32"

    invalid = client.post("/api/memory", json={"key": " ", "value": "x"})
    assert invalid.status_code == 422

    deleted = client.delete("/api/memory/preferred_board")
    assert deleted.status_code == 200
    assert client.get("/api/memory/preferred_board").status_code == 404
