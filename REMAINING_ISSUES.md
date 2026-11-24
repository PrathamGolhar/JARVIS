# JARVIS 2.0 — REMAINING ISSUES & MAINTENANCE BACKLOG

**Date:** November 24, 2026  
**Status:** No Critical (P0) or High (P1) Deficiencies Remain.  

---

## 1. P2 — Medium Priority Maintenance Items

1. **Docker Host CLI Integration**:
   - The development workstation lacks Docker CLI binaries on PATH. While the multi-stage `Dockerfile` and `docker-compose.yml` are syntactically and structurally validated, automated CI/CD container tests require a Docker engine runner.
2. ~~**Periodic Background Cleanup Schedule**~~ — **RESOLVED (2026-11-24)**:
   - `clean_stale_files()` is now wired to an `asyncio` background task in `app/main.py` via the FastAPI lifespan context.
   - On startup: sweeps both `data/generated` and `data/uploads` immediately.
   - Recurring: sweeps every 24 h (`_CLEANUP_INTERVAL_SECONDS = 86_400`).
   - No new dependency added (stdlib `asyncio` only — APScheduler is NOT installed).
   - `clean_all_stale_files()` added to `maintenance.py` as a convenience wrapper.
   - `CleanupSummary.merge()` added to combine results from multiple directories.
   - 9 regression tests in `backend/tests/test_maintenance.py` — all passing.

---

## 2. P3 — Low Priority Enhancements

1. **Local Embeddings (Optional Hybrid RAG)**:
   - Current RAG uses Okapi BM25 and SQLite FTS5 with sentence-aware chunk boundaries. It provides fast, zero-dependency keyword and conceptual matching. For environments with GPUs, an optional ONNX-based local embedding model (e.g. BGE-micro) could be attached as an opt-in plugin.
2. **Browser Push Notifications**:
   - Reminders currently trigger via system log and API status queries. Adding Web Push API or local OS desktop toast notifications would enhance reminder visibility.
