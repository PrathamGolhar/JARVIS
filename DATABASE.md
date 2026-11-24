# JARVIS Persistence and Data Model

This document describes the stores currently used by the application. There is no implemented PostgreSQL migration path or ORM schema.

## Storage locations

`backend/app/settings.py` creates `backend/data/` by default. In the Docker image, the corresponding persistent volume is mounted at `/app/data`.

| Data | Current store | Location |
| --- | --- | --- |
| Conversation turns, session ownership, generated-artifact metadata, user memories, memory history | SQLite | `data/jarvis_memory.db` |
| Uploaded document metadata, extracted chunks, full-text index | SQLite with FTS5 | `data/jarvis_documents.db` |
| Projects and project tasks | JSON files | `data/projects/proj_<id>.json` |
| Reminders | JSON file | `data/reminders.json` |
| Uploaded and generated file bytes | Filesystem | `data/uploads/` and `data/generated/` |

Custom upload and generated-file directories can be set with `JARVIS_UPLOAD_ROOT` and `JARVIS_GENERATED_ROOT`. Projects, reminders, and the two SQLite stores continue to use `settings.data_dir`.

## SQLite tables

`jarvis_memory.db` currently creates:

- `messages`: session-scoped turns, role, content, and optional tool metadata.
- `sessions`: session ID, owner ID, and timestamps.
- `artifacts`: generated-file ownership and session metadata.
- `user_memories`: owner-scoped key/value facts with category, provenance, source, confidence, and timestamps.
- `memory_history`: history of changes to user memories.
- `memory_migrations`: applied memory migration markers.

`jarvis_documents.db` currently creates:

- `documents`: file ID, filename, content hash, chunk/word counts, owner/session/project scope, and timestamp.
- `document_chunks`: extracted text, chunk index, and scope metadata.
- `chunks_fts`: SQLite FTS5 index associated with document chunks.

Retrieval uses SQLite full-text search; there is no vector-embedding database. Image uploads are not OCR'd or indexed by the upload route.

## Configuration and operational limitations

`JARVIS_DATABASE_URL` / `DATABASE_URL` is parsed and reported by settings diagnostics, but the persistence stores construct their paths from `settings.data_dir` and do not use that URL. Do not rely on it to move or migrate data.

Back up the full `backend/data/` directory while the application is stopped or use SQLite's supported backup API for each database. Uploaded/generated files and JSON state are separate from SQLite and must also be retained. No application-level encryption at rest is implemented; protect the data directory using host or volume controls appropriate to the deployment.
