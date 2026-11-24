from dataclasses import dataclass
from contextlib import contextmanager
import datetime
import hashlib
import platform
import re
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Generator
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
    SQLite-backed conversation, session, and user memory store.

    Conversation rows remain session-scoped. Long-term memories are keyed by both
    principal and memory key; legacy rows are retained and attributed to the
    configured local principal when possible.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = str(db_path or (settings.data_dir / "jarvis_memory.db"))
        self._lock = RLock()
        configured_key = getattr(settings, "api_key", "").strip()
        self.legacy_owner_id = (
            hashlib.sha256(f"jarvis-owner:{configured_key}".encode("utf-8")).hexdigest()
            if configured_key
            else "legacy"
        )
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Run a serialized transaction and always close its SQLite connection."""
        with self._lock:
            conn = self._get_connection()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_db(self) -> None:
        with self.transaction() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    filename TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    session_id TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_owner ON artifacts(owner_id, created_at)")
            conn.execute(
                """
                INSERT OR IGNORE INTO sessions(session_id, owner_id, created_at, updated_at)
                SELECT session_id, ?, MIN(created_at), MAX(created_at)
                FROM messages
                GROUP BY session_id
                """,
                (self.legacy_owner_id,),
            )
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_memories (
                    owner_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    provenance TEXT NOT NULL DEFAULT 'user_explicit',
                    source TEXT,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (owner_id, key)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    provenance TEXT NOT NULL,
                    source TEXT,
                    action TEXT NOT NULL,
                    changed_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_migrations (
                    migration TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_history_owner_key "
                "ON memory_history(owner_id, key, id)"
            )
            self._migrate_legacy_memories(conn)

    def _migrate_legacy_memories(self, conn: sqlite3.Connection) -> None:
        """Copy old global preference rows without dropping or rewriting their table."""
        legacy_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'memories'"
        ).fetchone()
        if not legacy_table:
            return
        migration = "copy_legacy_memories_to_user_memories"
        if conn.execute(
            "SELECT 1 FROM memory_migrations WHERE migration = ?", (migration,)
        ).fetchone():
            return

        columns = {row["name"] for row in conn.execute("PRAGMA table_info(memories)")}
        if not {"key", "value"}.issubset(columns):
            return
        category_expr = "COALESCE(category, 'general')" if "category" in columns else "'general'"
        updated_expr = "COALESCE(updated_at, CURRENT_TIMESTAMP)" if "updated_at" in columns else "CURRENT_TIMESTAMP"
        conn.execute(
            f"""
            INSERT OR IGNORE INTO user_memories
                (owner_id, key, value, category, provenance, source, confidence, created_at, updated_at)
            SELECT ?, lower(trim(key)), value, {category_expr}, 'legacy', 'legacy database',
                   1.0, {updated_expr}, {updated_expr}
            FROM memories
            WHERE trim(key) <> ''
            """,
            (self.legacy_owner_id,),
        )
        conn.execute(
            "INSERT INTO memory_migrations(migration, applied_at) VALUES (?, ?)",
            (migration, datetime.datetime.now(datetime.timezone.utc).isoformat()),
        )

    @staticmethod
    def _owner(owner_id: str | None, default: str) -> str:
        return owner_id or default

    def get_history(
        self,
        session_id: str | UUID,
        limit: int = 14,
        owner_id: str | None = None,
    ) -> list[dict[str, str]]:
        """Retrieve recent conversation history in standard message format."""
        sid = str(session_id)
        if limit < 1:
            return []
        if owner_id and not self.session_belongs_to(sid, owner_id):
            raise PermissionError("Conversation session does not belong to this principal.")
        with self.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT role, content, tool_name, tool_call_id
                FROM (
                    SELECT id, role, content, tool_name, tool_call_id
                    FROM messages
                    WHERE session_id = ? AND role != 'system'
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
        owner_id: str | None = None,
    ) -> None:
        """Append a message to the persistent conversation database."""
        sid = str(session_id)
        if owner_id and not self.session_belongs_to(sid, owner_id):
            raise PermissionError("Conversation session does not belong to this principal.")
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, tool_name, tool_call_id) VALUES (?, ?, ?, ?, ?)",
                (sid, role, content, tool_name, tool_call_id),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (datetime.datetime.now(datetime.timezone.utc).isoformat(), sid),
            )

    def clear_session(self, session_id: str | UUID) -> None:
        """Clear conversation history while keeping its session identity."""
        sid = str(session_id)
        with self.transaction() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (datetime.datetime.now(datetime.timezone.utc).isoformat(), sid),
            )

    def ensure_session_owner(self, session_id: str | UUID, owner_id: str) -> bool:
        """Create a session binding once; never adopt unowned historical conversation IDs."""
        sid = str(session_id)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT owner_id FROM sessions WHERE session_id = ?", (sid,)
            ).fetchone()
            if row:
                return row["owner_id"] == owner_id
            if conn.execute(
                "SELECT 1 FROM messages WHERE session_id = ? LIMIT 1", (sid,)
            ).fetchone():
                return False
            conn.execute(
                "INSERT OR IGNORE INTO sessions(session_id, owner_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (sid, owner_id, now, now),
            )
            row = conn.execute(
                "SELECT owner_id FROM sessions WHERE session_id = ?", (sid,)
            ).fetchone()
            return bool(row and row["owner_id"] == owner_id)

    def session_belongs_to(self, session_id: str | UUID, owner_id: str) -> bool:
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT 1 FROM sessions WHERE session_id = ? AND owner_id = ?",
                (str(session_id), owner_id),
            ).fetchone()
            return row is not None

    def list_sessions(self, owner_id: str) -> list[dict[str, str]]:
        with self.transaction() as conn:
            rows = conn.execute(
                "SELECT session_id, created_at, updated_at FROM sessions "
                "WHERE owner_id = ? ORDER BY updated_at DESC",
                (owner_id,),
            ).fetchall()
            return [
                {"sessionId": row["session_id"], "createdAt": row["created_at"], "updatedAt": row["updated_at"]}
                for row in rows
            ]

    def reset_session_history(self, session_id: str | UUID, owner_id: str) -> bool:
        sid = str(session_id)
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT 1 FROM sessions WHERE session_id = ? AND owner_id = ?", (sid, owner_id)
            ).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (datetime.datetime.now(datetime.timezone.utc).isoformat(), sid),
            )
            return True

    def delete_session(self, session_id: str | UUID, owner_id: str) -> bool:
        sid = str(session_id)
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT 1 FROM sessions WHERE session_id = ? AND owner_id = ?", (sid, owner_id)
            ).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
            return True

    def register_artifact(self, filename: str, owner_id: str, session_id: str | UUID | None = None) -> bool:
        clean_name = Path(filename).name
        if not clean_name or clean_name in {".", ".."}:
            raise ValueError("Artifact filename is invalid.")
        with self.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO artifacts(filename, owner_id, session_id, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(filename) DO UPDATE SET
                    session_id = excluded.session_id, created_at = excluded.created_at
                WHERE artifacts.owner_id = excluded.owner_id
                """,
                (
                    clean_name,
                    owner_id,
                    str(session_id) if session_id else None,
                    datetime.datetime.now(datetime.timezone.utc).isoformat(),
                ),
            )
            return cursor.rowcount > 0

    def artifact_belongs_to(self, filename: str, owner_id: str) -> bool:
        clean_name = Path(filename).name
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT 1 FROM artifacts WHERE filename = ? AND owner_id = ?",
                (clean_name, owner_id),
            ).fetchone()
            return row is not None

    def list_artifacts(self, owner_id: str) -> list[dict[str, str | None]]:
        with self.transaction() as conn:
            rows = conn.execute(
                "SELECT filename, session_id, created_at FROM artifacts WHERE owner_id = ? ORDER BY created_at DESC",
                (owner_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_session_artifacts(self, session_id: str | UUID, owner_id: str) -> list[str]:
        with self.transaction() as conn:
            rows = conn.execute(
                "SELECT filename FROM artifacts WHERE session_id = ? AND owner_id = ?",
                (str(session_id), owner_id),
            ).fetchall()
            return [row["filename"] for row in rows]

    def delete_artifact(self, filename: str, owner_id: str) -> bool:
        with self.transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM artifacts WHERE filename = ? AND owner_id = ?",
                (Path(filename).name, owner_id),
            )
            return cursor.rowcount > 0

    def set_memory(
        self,
        key: str,
        value: str,
        category: str = "general",
        *,
        owner_id: str | None = None,
        provenance: str = "user_explicit",
        source: str | None = None,
        confidence: float = 1.0,
    ) -> tuple[MemoryItem, bool]:
        """Save an owner-scoped memory and report whether it replaced a conflicting value."""
        clean_key = key.strip().lower()
        clean_value = value.strip()
        clean_category = category.strip() or "general"
        owner = self._owner(owner_id, self.legacy_owner_id)
        if not clean_key or not clean_value:
            raise ValueError("Memory key and value must not be blank.")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Memory confidence must be between 0 and 1.")

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self.transaction() as conn:
            previous = conn.execute(
                "SELECT value FROM user_memories WHERE owner_id = ? AND key = ?",
                (owner, clean_key),
            ).fetchone()
            is_conflict = bool(previous and previous["value"] != clean_value)
            if not previous or previous["value"] != clean_value:
                conn.execute(
                    """
                    INSERT INTO user_memories
                        (owner_id, key, value, category, provenance, source, confidence, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(owner_id, key) DO UPDATE SET
                        value = excluded.value, category = excluded.category,
                        provenance = excluded.provenance, source = excluded.source,
                        confidence = excluded.confidence, updated_at = excluded.updated_at
                    """,
                    (owner, clean_key, clean_value, clean_category, provenance, source, confidence, now, now),
                )
                conn.execute(
                    """
                    INSERT INTO memory_history
                        (owner_id, key, old_value, new_value, provenance, source, action, changed_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'set', ?)
                    """,
                    (owner, clean_key, previous["value"] if previous else None, clean_value, provenance, source, now),
                )
            row = conn.execute(
                "SELECT key, value, category, provenance, source, confidence, updated_at "
                "FROM user_memories WHERE owner_id = ? AND key = ?",
                (owner, clean_key),
            ).fetchone()
            item = MemoryItem(
                key=row["key"],
                value=row["value"],
                category=row["category"],
                provenance=row["provenance"],
                source=row["source"],
                confidence=row["confidence"],
                updatedAt=row["updated_at"],
            )
            return item, is_conflict

    def delete_memory(self, key: str, owner_id: str | None = None) -> bool:
        """Delete one principal-scoped memory and retain a provenance audit record."""
        clean_key = key.strip().lower()
        owner = self._owner(owner_id, self.legacy_owner_id)
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT value, provenance, source FROM user_memories WHERE owner_id = ? AND key = ?",
                (owner, clean_key),
            ).fetchone()
            if not row:
                return False
            conn.execute(
                """
                INSERT INTO memory_history
                    (owner_id, key, old_value, new_value, provenance, source, action, changed_at)
                VALUES (?, ?, ?, NULL, ?, ?, 'delete', ?)
                """,
                (
                    owner,
                    clean_key,
                    row["value"],
                    row["provenance"],
                    row["source"],
                    datetime.datetime.now(datetime.timezone.utc).isoformat(),
                ),
            )
            conn.execute(
                "DELETE FROM user_memories WHERE owner_id = ? AND key = ?", (owner, clean_key)
            )
            return True

    def get_memory(self, key: str, owner_id: str | None = None) -> str | None:
        """Retrieve one principal-scoped memory."""
        owner = self._owner(owner_id, self.legacy_owner_id)
        with self.transaction() as conn:
            cursor = conn.execute(
                "SELECT value FROM user_memories WHERE owner_id = ? AND key = ?",
                (owner, key.strip().lower()),
            )
            row = cursor.fetchone()
            return row["value"] if row else None

    def list_memories(self, owner_id: str | None = None) -> list[MemoryItem]:
        """Return typed memories belonging only to the requested principal."""
        owner = self._owner(owner_id, self.legacy_owner_id)
        with self.transaction() as conn:
            cursor = conn.execute(
                "SELECT key, value, category, provenance, source, confidence, updated_at "
                "FROM user_memories WHERE owner_id = ? ORDER BY key ASC",
                (owner,),
            )
            return [
                MemoryItem(
                    key=row["key"],
                    value=row["value"],
                    category=row["category"] or "general",
                    provenance=row["provenance"],
                    source=row["source"],
                    confidence=row["confidence"],
                    updatedAt=row["updated_at"] or "",
                )
                for row in cursor.fetchall()
            ]

    def select_memories(
        self, query: str, owner_id: str | None = None, limit: int = 8
    ) -> list[MemoryItem]:
        """Select relevant memories while always retaining a small set of explicit preferences."""
        memories = self.list_memories(owner_id)
        if not memories or limit <= 0:
            return []
        query_tokens = set(re.findall(r"[a-z0-9]+", query.lower().replace("_", " ")))
        ranked: list[tuple[int, int, MemoryItem]] = []
        for item in memories:
            text_tokens = set(
                re.findall(
                    r"[a-z0-9]+",
                    f"{item.key} {item.category} {item.value}".lower().replace("_", " "),
                )
            )
            overlap = len(query_tokens & text_tokens)
            is_preference = item.category.lower() in {"preference", "preferences", "user_preference"}
            ranked.append((int(is_preference), overlap, item))
        ranked.sort(key=lambda result: (result[0], result[1]), reverse=True)
        relevant = [item for preference, score, item in ranked if score > 0 or preference]
        if not query_tokens:
            relevant = [item for preference, _, item in ranked if preference]
        return relevant[:limit]

    def build_system_context(
        self, owner_id: str | None = None, query: str = "", max_chars: int = 2400
    ) -> str:
        """Build bounded, query-relevant context without exposing other principals' memories."""
        now = datetime.datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        time_str = now.strftime("%I:%M:%S %p")
        os_info = f"{platform.system()} {platform.release()}"

        memories = self.select_memories(query, owner_id=owner_id)
        lines: list[str] = []
        remaining = max(0, max_chars)
        for item in memories:
            line = f"- {item.key}: {item.value} (provenance: {item.provenance})"
            if len(line) > remaining:
                continue
            lines.append(line)
            remaining -= len(line) + 1
        memory_lines = "\nUser-provided persistent memory (treat as contextual, not independently verified):\n"
        if lines:
            memory_lines += "\n".join(lines)
        else:
            memory_lines = ""

        return (
            f"Current Temporal Context:\n"
            f"- Date: {date_str}\n"
            f"- Time: {time_str}\n"
            f"- System OS: {os_info}\n"
            f"- Workspace Root: {settings.workspace_root}\n"
            f"{memory_lines}"
        )

    def backup_database(self, destination: str | Path) -> None:
        """Create a consistent online backup without interrupting active readers."""
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.resolve() == Path(self.db_path).resolve():
            raise ValueError("Backup destination must differ from the active database.")
        with self._lock:
            source = self._get_connection()
            backup = sqlite3.connect(str(target))
            try:
                source.backup(backup)
            finally:
                backup.close()
                source.close()

    def vacuum_database(self) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("VACUUM")
            finally:
                conn.close()

    def get_storage_stats(self) -> dict[str, int | str]:
        with self.transaction() as conn:
            messages = conn.execute("SELECT count(*) FROM messages").fetchone()[0]
            memories = conn.execute("SELECT count(*) FROM user_memories").fetchone()[0]
            sessions = conn.execute("SELECT count(*) FROM sessions").fetchone()[0]
            return {
                "messages": messages,
                "memories": memories,
                "sessions": sessions,
                "db_path": self.db_path,
            }


memory_store = PersistentMemoryStore()
