# JARVIS 2.0 Database Architecture & Data Models

JARVIS 2.0 utilizes a resilient relational database model (SQLite for development / embedded deployments, with full migration capability to PostgreSQL in enterprise production environments).

---

## 1. Entity-Relationship Overview

```text
+----------------+          +-------------------+          +-------------------+
|      User      | 1 ---- * |   Conversation    | 1 ---- * |      Message      |
+----------------+          +-------------------+          +-------------------+
        |                             |
        | 1                           | 1
        |                             |
        v *                           v *
+----------------+          +-------------------+          +-------------------+
|    Project     | 1 ---- * |       Task        | 1 ---- * |     TaskStep      |
+----------------+          +-------------------+          +-------------------+
        |
        | 1
        v *
+----------------+          +-------------------+          +-------------------+
|  ProjectFile   |          |      Memory       |          |   GeneratedFile   |
+----------------+          +-------------------+          +-------------------+
```

---

## 2. Core Tables & Schemas

### 2.1 `messages` (Short-Term Conversational Memory)
Stores granular interaction history per session.
```sql
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    tool_name TEXT,
    tool_call_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
```

### 2.2 `memories` (Long-Term Semantic & Key/Value Knowledge)
Retains user preferences, project context, and user-approved facts across sessions.
```sql
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('preference', 'fact', 'workflow', 'project', 'instruction')),
    value TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
```

### 2.3 `projects` & `project_tasks`
Provides dedicated workspace state, tracking milestones, linked artifacts, and task lists.
```sql
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('todo', 'in_progress', 'completed', 'cancelled')),
    due_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_project_tasks_pid ON project_tasks(project_id);
```

### 2.4 `reminders` (Scheduled Workflows & Automation)
Stores time-based alarms, cron automation schedules, and recurrent tasks.
```sql
CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    trigger_at DATETIME NOT NULL,
    is_recurring BOOLEAN DEFAULT 0,
    cron_expression TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'fired', 'cancelled')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. Data Migration & Persistence
- Default Local Path: `./data/jarvis.db`
- Backup Command: `sqlite3 ./data/jarvis.db ".backup './data/jarvis_backup.db'"`
- Encryption at Rest: Supported via SQLCipher or Volume-level encryption (LUKS / BitLocker).
