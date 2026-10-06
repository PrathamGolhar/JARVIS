from dataclasses import dataclass
import datetime
import platform
import sqlite3
from threading import RLock
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
    SQLite-backed persistent conversation history and categorized user preference store.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = str(db_path or (settings.data_dir / "jarvis_memory.db"))
        self._lock = RLock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._get_connection() as conn:
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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Migration check: Ensure category column exists in older SQLite DBs
            cursor = conn.execute("PRAGMA table_info(memories)")
            columns = {row["name"] for row in cursor.fetchall()}
            if "category" not in columns:
                try:
                    conn.execute("ALTER TABLE memories ADD COLUMN category TEXT DEFAULT 'general'")
                except Exception:
                    pass
            if "updated_at" not in columns:
                try:
                    conn.execute("ALTER TABLE memories ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                except Exception:
                    pass
            conn.commit()

    def get_history(self, session_id: str | UUID, limit: int = 14) -> list[dict[str, str]]:
        """Retrieve recent conversation history in standard message format."""
        sid = str(session_id)
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT role, content, tool_name, tool_call_id
                FROM (
                    SELECT id, role, content, tool_name, tool_call_id
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                ORDER BY id ASC
                """,
                (sid, limit),
            )
            rows = cursor.fetchall()
            return [{"role": row["role"], "content": row["content"]} for row in rows]

    def append_message(
        self,
        session_id: str | UUID,
        role: str,
        content: str,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        """Append a message to the persistent conversation database."""
        sid = str(session_id)
        with self._lock, self._get_connection() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, tool_name, tool_call_id) VALUES (?, ?, ?, ?, ?)",
                (sid, role, content, tool_name, tool_call_id),
            )
            conn.commit()

    def clear_session(self, session_id: str | UUID) -> None:
        """Clear history for a specific session."""
        sid = str(session_id)
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
            conn.commit()

    def set_memory(self, key: str, value: str, category: str = "general") -> MemoryItem:
        """Save or update a persistent fact or user preference."""
        clean_key = key.strip().lower()
        now = datetime.datetime.now().isoformat()
        with self._lock, self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO memories (key, value, category, updated_at) VALUES (?, ?, ?, ?)",
                (clean_key, value.strip(), category.strip(), now),
            )
            conn.commit()
            return MemoryItem(key=clean_key, value=value.strip(), category=category, updatedAt=now)

    def delete_memory(self, key: str) -> bool:
        """Delete a persistent memory entry."""
        with self._lock, self._get_connection() as conn:
            cur = conn.execute("DELETE FROM memories WHERE key = ?", (key.strip().lower(),))
            conn.commit()
            return cur.rowcount > 0

    def get_memory(self, key: str) -> str | None:
        """Retrieve a stored preference."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute("SELECT value FROM memories WHERE key = ?", (key.strip().lower(),))
            row = cursor.fetchone()
            return row["value"] if row else None

    def list_memories(self) -> list[MemoryItem]:
        """Return all stored memories as typed MemoryItems."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute("SELECT key, value, category, updated_at FROM memories ORDER BY key ASC")
            return [
                MemoryItem(
                    key=row["key"],
                    value=row["value"],
                    category=row["category"] or "general",
                    updatedAt=row["updated_at"] or "",
                )
                for row in cursor.fetchall()
            ]

    def build_system_context(self) -> str:
        """Build dynamic temporal and environment context to prime the AI assistant."""
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
