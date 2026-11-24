"""
Authoritative SQLite Storage Engine for JARVIS Memory and Conversation History.

Enterprise Reliability Controls:
1. Write-Ahead Logging (WAL): PRAGMA journal_mode=WAL eliminates reader/writer lock contention.
2. Synchronous Normal: PRAGMA synchronous=NORMAL ensures optimal throughput without durability loss in WAL mode.
3. Busy Timeout: PRAGMA busy_timeout=5000 retries automatically for 5 seconds under concurrent write contention.
4. Composite Indexing: idx_messages_session_id on (session_id, id DESC) optimizes history lookups without table scans.
5. Atomic Transactions: Managed via 'with conn:' context managers ensuring automatic commit or rollback.
6. Online Zero-Downtime Backup: Supports live database backups using SQLite's native backup API.
7. Schema Migration Tracking: Formalized migration ledger with idempotency guards.
"""

from contextlib import contextmanager
from dataclasses import dataclass
import datetime
import logging
from pathlib import Path
import platform
import sqlite3
import threading
from typing import Any, Generator, Optional
from uuid import UUID

from app.schemas import MemoryItem
from app.settings import settings

logger = logging.getLogger("jarvis.database")

SCHEMA_VERSION = 2


@dataclass(frozen=True)
class StoredMessage:
    role: str
    content: str
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None


class PersistentMemoryStore:
    """
    Thread-safe, WAL-enabled SQLite persistence store for conversations,
    semantic memory, and preference settings.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = str(db_path or (settings.data_dir / "jarvis_memory.db"))
        self._lock = threading.RLock()
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        """Apply performance, concurrency, and durability pragmas to connection."""
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA cache_size = -64000;")  # 64MB memory cache

    def _get_connection(self) -> sqlite3.Connection:
        """Create and configure a new SQLite connection."""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=10.0,
        )
        self._configure_connection(conn)
        return conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Thread-safe context manager providing an active SQLite connection with automatic
        commit on clean exit and automatic rollback on unhandled exceptions.
        """
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    yield conn
            finally:
                conn.close()

    def _init_db(self) -> None:
        """Initialize tables, indexes, and execute schema migrations."""
        with self.transaction() as conn:
            # 1. Migration tracking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Conversation messages table
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
            # Optimal composite index: seeks directly by session_id and orders by id DESC
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id, id DESC)")

            # 3. Preferences and long-term memory table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")

            # 4. Check and apply migrations idempotently
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

            # Record schema version
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (?, ?)",
                (SCHEMA_VERSION, "v2_wal_and_composite_indexes"),
            )

        logger.info("Database initialized successfully at: %s (WAL mode enabled)", self.db_path)

    def get_history(self, session_id: str | UUID, limit: int = 14) -> list[dict[str, str]]:
        """Retrieve recent conversation history in standard message format using composite index."""
        sid = str(session_id)
        with self.transaction() as conn:
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
        tool_name: Optional[str] = None,
        tool_call_id: Optional[str] = None,
    ) -> None:
        """Atomically append a message to the persistent conversation database."""
        sid = str(session_id)
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, tool_name, tool_call_id) VALUES (?, ?, ?, ?, ?)",
                (sid, role, content, tool_name, tool_call_id),
            )

    def clear_session(self, session_id: str | UUID) -> int:
        """Clear history for a specific session. Returns number of messages deleted."""
        sid = str(session_id)
        with self.transaction() as conn:
            cur = conn.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
            return cur.rowcount

    def set_memory(
        self,
        key: str,
        value: str,
        category: str = "general",
        provenance: str = "user_preference",
    ) -> tuple[MemoryItem, bool]:
        """
        Save or update a persistent fact or preference atomically.
        Detects conflicts when a preexisting key has a different value, recording the change in audit log.
        Returns (MemoryItem, is_conflict).
        """
        clean_key = key.strip().lower()
        now = datetime.datetime.now().isoformat()
        is_conflict = False

        with self.transaction() as conn:
            cursor = conn.execute("SELECT value FROM memories WHERE key = ?", (clean_key,))
            existing = cursor.fetchone()
            if existing and existing["value"].strip() != value.strip():
                is_conflict = True
                logger.info(
                    "Memory conflict detected for key '%s': overwriting '%s' with '%s' (provenance: %s)",
                    clean_key,
                    existing["value"],
                    value.strip(),
                    provenance,
                )

            conn.execute(
                "INSERT OR REPLACE INTO memories (key, value, category, updated_at) VALUES (?, ?, ?, ?)",
                (clean_key, value.strip(), category.strip(), now),
            )
            item = MemoryItem(key=clean_key, value=value.strip(), category=category, updatedAt=now)
            return item, is_conflict

    def delete_memory(self, key: str) -> bool:
        """Delete a persistent memory entry."""
        with self.transaction() as conn:
            cur = conn.execute("DELETE FROM memories WHERE key = ?", (key.strip().lower(),))
            return cur.rowcount > 0

    def get_memory(self, key: str) -> Optional[str]:
        """Retrieve a stored preference."""
        with self.transaction() as conn:
            cursor = conn.execute("SELECT value FROM memories WHERE key = ?", (key.strip().lower(),))
            row = cursor.fetchone()
            return row["value"] if row else None

    def list_memories(self) -> list[MemoryItem]:
        """Return all stored memories as typed MemoryItems."""
        with self.transaction() as conn:
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

    def backup_database(self, destination_path: Optional[str] = None) -> str:
        """
        Perform an online, live, zero-downtime backup of the active SQLite database
        using the native sqlite3.backup API.
        """
        if not destination_path:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Path(self.db_path).parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            dest_file = backup_dir / f"jarvis_backup_{timestamp}.db"
        else:
            dest_file = Path(destination_path)
            dest_file.parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            src_conn = sqlite3.connect(self.db_path)
            dest_conn = sqlite3.connect(str(dest_file))
            try:
                src_conn.backup(dest_conn, pages=100)
                logger.info("Live database backup created successfully at: %s", dest_file)
            finally:
                dest_conn.close()
                src_conn.close()

        return str(dest_file)

    def vacuum_database(self) -> None:
        """Reclaim unused disk space and optimize database file."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("VACUUM;")
                logger.info("Database VACUUM completed successfully.")
            finally:
                conn.close()

    def get_storage_stats(self) -> dict[str, Any]:
        """Retrieve operational telemetry and storage metrics for database health diagnostics."""
        with self.transaction() as conn:
            page_count = conn.execute("PRAGMA page_count;").fetchone()[0]
            page_size = conn.execute("PRAGMA page_size;").fetchone()[0]
            journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            msg_count = conn.execute("SELECT COUNT(*) FROM messages;").fetchone()[0]
            mem_count = conn.execute("SELECT COUNT(*) FROM memories;").fetchone()[0]

            return {
                "db_path": self.db_path,
                "journal_mode": journal_mode.upper(),
                "file_size_bytes": page_count * page_size,
                "messages_count": msg_count,
                "memories_count": mem_count,
                "wal_enabled": journal_mode.lower() == "wal",
            }

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
