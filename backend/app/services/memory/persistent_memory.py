from contextlib import contextmanager
from dataclasses import dataclass
import datetime
import platform
import sqlite3
from threading import RLock
from typing import Iterator
from uuid import UUID

from app.schemas import MemoryItem
from app.settings import settings


@dataclass(frozen=True)
class StoredMessage:
    role: str
    content: str
    tool_name: str | None = None
    tool_call_id: str | None = None


class PersistentMemoryStore:
    """
    SQLite-backed conversation history and categorized memory store.

    Schema changes are tracked with SQLite's PRAGMA user_version. Migrations
    run transactionally and deliberately fail loudly instead of hiding errors.
    """

    SCHEMA_VERSION = 1
    MEMORY_KEY_MAX_LENGTH = 160
    MEMORY_VALUE_MAX_LENGTH = 10_000
    MEMORY_CATEGORY_MAX_LENGTH = 40

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = str(db_path or (settings.data_dir / "jarvis_memory.db"))
        self._lock = RLock()
        self._init_db()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 10000")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._lock, self._connection() as conn:
            current_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
            if current_version > self.SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database schema version {current_version} is newer than "
                    f"this JARVIS build supports ({self.SCHEMA_VERSION})."
                )

            # Version 1 adopts the existing messages/memories tables. Existing
            # installations are upgraded in place; rows are never dropped.
            if current_version < 1:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        tool_name TEXT,
                        tool_call_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        category TEXT DEFAULT 'general',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                message_columns = {
                    row["name"] for row in conn.execute("PRAGMA table_info(messages)")
                }
                if "tool_name" not in message_columns:
                    conn.execute("ALTER TABLE messages ADD COLUMN tool_name TEXT")
                if "tool_call_id" not in message_columns:
                    conn.execute("ALTER TABLE messages ADD COLUMN tool_call_id TEXT")
                if "created_at" not in message_columns:
                    conn.execute("ALTER TABLE messages ADD COLUMN created_at TEXT")
                    conn.execute(
                        "UPDATE messages SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
                    )

                memory_columns = {
                    row["name"] for row in conn.execute("PRAGMA table_info(memories)")
                }
                if "category" not in memory_columns:
                    conn.execute(
                        "ALTER TABLE memories ADD COLUMN category TEXT NOT NULL DEFAULT 'general'"
                    )
                if "updated_at" not in memory_columns:
                    # SQLite cannot add a non-constant CURRENT_TIMESTAMP default
                    # to a populated table. Add a nullable column, then backfill.
                    conn.execute("ALTER TABLE memories ADD COLUMN updated_at TEXT")
                    conn.execute(
                        "UPDATE memories SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"
                    )

                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)"
                )
                conn.execute("PRAGMA user_version = 1")

    @classmethod
    def _normalize_memory(cls, key: str, value: str, category: str) -> tuple[str, str, str]:
        if not isinstance(key, str) or not isinstance(value, str) or not isinstance(category, str):
            raise ValueError("Memory key, value, and category must be strings.")

        clean_key = key.strip().lower()
        clean_value = value.strip()
        clean_category = category.strip().lower() or "general"

        if not clean_key:
            raise ValueError("Memory key cannot be blank.")
        if len(clean_key) > cls.MEMORY_KEY_MAX_LENGTH:
            raise ValueError(f"Memory key cannot exceed {cls.MEMORY_KEY_MAX_LENGTH} characters.")
        if not clean_value:
            raise ValueError("Memory value cannot be blank.")
        if len(clean_value) > cls.MEMORY_VALUE_MAX_LENGTH:
            raise ValueError(f"Memory value cannot exceed {cls.MEMORY_VALUE_MAX_LENGTH} characters.")
        if len(clean_category) > cls.MEMORY_CATEGORY_MAX_LENGTH:
            raise ValueError(
                f"Memory category cannot exceed {cls.MEMORY_CATEGORY_MAX_LENGTH} characters."
            )
        return clean_key, clean_value, clean_category

    def get_history(self, session_id: str | UUID, limit: int = 14) -> list[dict[str, str]]:
        """Retrieve recent conversation history in chronological order."""
        if limit < 1:
            raise ValueError("History limit must be at least 1.")
        sid = str(session_id)
        with self._lock, self._connection() as conn:
            rows = conn.execute(
                """
                SELECT role, content
                FROM (
                    SELECT id, role, content
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                ORDER BY id ASC
                """,
                (sid, limit),
            ).fetchall()
            return [{"role": row["role"], "content": row["content"]} for row in rows]

    def append_message(
        self,
        session_id: str | UUID,
        role: str,
        content: str,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        """Append a message to persistent conversation history."""
        if not role.strip():
            raise ValueError("Message role cannot be blank.")
        if not isinstance(content, str):
            raise ValueError("Message content must be a string.")
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                INSERT INTO messages (session_id, role, content, tool_name, tool_call_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(session_id), role.strip(), content, tool_name, tool_call_id),
            )

    def clear_session(self, session_id: str | UUID) -> None:
        """Clear history for one session without affecting other sessions."""
        with self._lock, self._connection() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (str(session_id),))

    def set_memory(self, key: str, value: str, category: str = "general") -> MemoryItem:
        """Create or update a memory without deleting/replacing its database row."""
        clean_key, clean_value, clean_category = self._normalize_memory(key, value, category)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._lock, self._connection() as conn:
            conn.execute(
                """
                INSERT INTO memories (key, value, category, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    category = excluded.category,
                    updated_at = excluded.updated_at
                """,
                (clean_key, clean_value, clean_category, now),
            )
        return MemoryItem(
            key=clean_key,
            value=clean_value,
            category=clean_category,
            updatedAt=now,
        )

    def delete_memory(self, key: str) -> bool:
        """Delete one memory entry and report whether it existed."""
        if not isinstance(key, str) or not key.strip():
            return False
        with self._lock, self._connection() as conn:
            cur = conn.execute("DELETE FROM memories WHERE key = ?", (key.strip().lower(),))
            return cur.rowcount > 0

    def get_memory(self, key: str) -> str | None:
        """Retrieve a memory value by its normalized key."""
        if not isinstance(key, str) or not key.strip():
            return None
        with self._lock, self._connection() as conn:
            row = conn.execute(
                "SELECT value FROM memories WHERE key = ?", (key.strip().lower(),)
            ).fetchone()
            return row["value"] if row else None

    def list_memories(self) -> list[MemoryItem]:
        """Return all stored memories as typed MemoryItems."""
        with self._lock, self._connection() as conn:
            rows = conn.execute(
                "SELECT key, value, category, updated_at FROM memories ORDER BY key ASC"
            ).fetchall()
            return [
                MemoryItem(
                    key=row["key"],
                    value=row["value"],
                    category=row["category"] or "general",
                    updatedAt=row["updated_at"] or "",
                )
                for row in rows
            ]

    def build_system_context(self) -> str:
        """Build temporal/environment context and the currently stored memories."""
        now = datetime.datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M:%S %p")
        os_info = f"{platform.system()} {platform.release()}"

        memories = self.list_memories()
        memory_lines = ""
        if memories:
            memory_lines = "\nKnown User Preferences & Facts:\n" + "\n".join(
                f"- {m.key}: {m.value}" for m in memories
            )

        return (
            f"Current Temporal Context:\n"
            f"- Date: {date_str}\n"
            f"- Time: {time_str}\n"
            f"- System OS: {os_info}\n"
            f"- Workspace Root: {settings.workspace_root}\n"
            f"{memory_lines}"
        )


memory_store = PersistentMemoryStore()
