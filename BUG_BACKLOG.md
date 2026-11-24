# JARVIS — Bug Backlog

> **Historical snapshot:** This backlog records findings from its stated audit date. Items have not been revalidated against the current workspace.

**Audit Date:** 2026-11-23  
**Status:** All bugs confirmed by code inspection. Items marked [UNVERIFIED] require runtime testing to confirm.

---

## Priority Legend
- 🔴 P0 — Blocks security or causes data loss
- 🟠 P1 — Breaks important functionality
- 🟡 P2 — Degrades experience or quality
- 🟢 P3 — Cosmetic, minor, or cleanup

---

## 🔴 P0 — Critical

### BUG-001 · Sandbox Escape via `subprocess`/`os` Import

**File:** `backend/app/services/coding/sandbox.py`  
**Function:** `execute_sandboxed_code()`  
**Status:** Confirmed  

Python's `-I` flag only blocks site-packages. `import subprocess`, `import os`, `import socket` all work and give full system access.

**Fix:** Add AST pre-scan to reject blocked modules before execution.

```python
BLOCKED_MODULES = {'os', 'subprocess', 'socket', 'shutil', 'ctypes', 
                   'sys', 'pathlib', 'importlib', 'tempfile'}
tree = ast.parse(code)
for node in ast.walk(tree):
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        mod = (node.module or '').split('.')[0]
        for alias in node.names:
            root = alias.name.split('.')[0]
            if root in BLOCKED_MODULES or mod in BLOCKED_MODULES:
                raise ValueError(f"Module '{root or mod}' is not permitted in sandbox.")
```

---

### BUG-002 · `permission_mode` Input Not Validated Before Persisting

**File:** `backend/app/api/settings_api.py`  
**Function:** `update_settings()`  
**Status:** Confirmed  

Any string is accepted. Only `"read_only"` triggers protection. Setting `"full_control"` or any unknown string bypasses all safety checks.

**Fix:**
```python
VALID_MODES = {"read_only", "assisted", "full_control"}
if request.permission_mode not in VALID_MODES:
    raise HTTPException(422, f"permissionMode must be one of {VALID_MODES}")
```

---

## 🟠 P1 — High Priority

### BUG-003 · Groq Primary/Fallback Model IDs Are Inverted in settings.py Code Defaults

**File:** `backend/app/settings.py` lines 56–61  
**Status:** Confirmed  

`settings.py` defaults: `groq_chat_model="openai/gpt-oss-20b"` (small), `groq_fallback_model="openai/gpt-oss-120b"` (large).  
`.env.example` says primary=120b, fallback=20b.  

When no env vars are set (clean install), the smaller model is used as primary, the larger as fallback — the opposite of the stated intent.

Additionally, the model IDs `openai/gpt-oss-20b` and `openai/gpt-oss-120b` may not be valid Groq model identifiers, potentially causing 404 errors on first request.

**Fix:** Verify actual Groq model IDs. Align defaults in `settings.py` with `.env.example`.

---

### BUG-004 · Synchronous `requests` Calls Block Async Event Loop

**Files:** `services/orchestrator.py`, `services/tools/web_search.py`, `services/research/researcher.py`, `services/ai/groq_provider.py`, `services/ai/gemini_provider.py`  
**Status:** Confirmed  

All AI provider calls and web search use `requests.post()` / `requests.get()` synchronously from within async FastAPI route handlers. This blocks uvicorn's event loop for 1–10+ seconds per request, serializing all concurrent connections.

**Fix:**
```python
# Replace requests with httpx in providers
import httpx
async with httpx.AsyncClient() as client:
    resp = await client.post(url, json=payload, timeout=30)
```
Or use `loop.run_in_executor(None, ...)` as an interim fix.

---

### BUG-005 · Confirmation Tokens Have No TTL — Unbounded Memory and Stale Execution

**File:** `backend/app/services/orchestrator.py`  
**Status:** Confirmed  

`_PENDING_CONFIRMATIONS` dict never purges old entries. A token for `write_file` from a previous session can be re-confirmed at any future time.

**Fix:** Add timestamp to `PendingConfirmation`, reject tokens older than 60 seconds, add periodic cleanup.

---

### BUG-006 · `inspect.signature` Hack in Chat API

**File:** `backend/app/api/chat.py` lines 25–37  
**Status:** Confirmed  

```python
sig = inspect.signature(run_orchestration)
param_count = len(sig.parameters)
if param_count <= 3:
    res = run_orchestration(request.session_id, request.text, request.confirmed_action_id)
```

Runtime introspection to handle test mocks. Will silently misbehave if the signature changes (adds a parameter), passing arguments in wrong positions.

**Fix:** Remove introspection. Update test fixtures to match the actual function signature.

---

### BUG-007 · `max_tokens=800` Causes Truncated AI Responses on Complex Tasks

**File:** `backend/app/services/orchestrator.py` line 187  
**Status:** Confirmed  

800 tokens (~600 words) is insufficient for:
- Document synthesis (needs 2000+)
- Code generation (needs 1500+)
- Research summarization (needs 2000+, researcher.py uses 3500)

The LLM frequently terminates mid-sentence.

**Fix:** Increase to `max_tokens=2000` as default; add per-mode overrides based on `plan.mode`.

---

### BUG-008 · No Rate Limiting — Cost Amplification and Resource Exhaustion

**File:** `backend/app/main.py`  
**Status:** Confirmed  

Unlimited requests per second to `/api/chat`, `/api/research`, `/api/coding/execute`. A loop or browser tab runaway can exhaust provider quotas within minutes.

**Fix:** Add `slowapi`:
```python
from slowapi import Limiter
limiter = Limiter(key_func=lambda req: req.headers.get("X-Session-Id", req.client.host))
@app.post("/api/chat")
@limiter.limit("10/minute")
async def chat(...): ...
```

---

## 🟡 P2 — Medium Priority

### BUG-009 · PlanningEngine Step 1 Always Pre-Marked "completed"

**File:** `backend/app/services/agents/planner.py`  
**Status:** Confirmed  

```python
PlanStep(stepNumber=1, title="...", status="completed"),  # pre-completed!
PlanStep(stepNumber=2, title="...", status="in_progress"),
```

Steps are static and don't reflect actual execution. The UI shows step 1 as done when the request hasn't started processing.

**Fix:** Initialize all steps with `status="pending"`. Update statuses via orchestrator callbacks or EventBus events.

---

### BUG-010 · RAG Vector Store Lost on Process Restart

**File:** `backend/app/services/memory/vector_store.py`  
**Status:** Confirmed  

All indexed document chunks are in `self._chunks: dict` in-process memory only. After restart, uploaded documents must be re-uploaded to be searchable.

**Fix:** Persist chunk index to SQLite (add a `chunks` table to `jarvis_memory.db`) or use a file-backed JSON index.

---

### BUG-011 · `BM25` Search in RAG Store Is O(N×M) Per Query

**File:** `backend/app/services/memory/vector_store.py`  
**Status:** Confirmed (theoretical, [UNVERIFIED at scale])  

The search iterates every token in every chunk and calls `list.count()` (O(N)) for each query token:
```python
count = chunk_tokens.count(q)   # O(chunk_len) per query term
```
For 100 large documents with 800-word chunks, each query could examine millions of token comparisons.

**Fix:** Precompute `Counter()` per chunk at index time, store in `DocumentChunk.token_counts`.

---

### BUG-012 · `permissions.py` Capability Registry Never Called by Tool Execution

**File:** `backend/app/services/tools/registry.py`  
**Status:** Confirmed  

`execute_tool_call()` dispatches directly by tool name. `validate_tool_approval()` exists but is never called, so the documented capability registry is bypassed entirely.

**Fix:** Add at the top of `execute_tool_call()`:
```python
approved, needs_confirm, msg = validate_tool_approval(tool_name)
if not approved:
    return {"ok": False, "error": msg}
```

---

### BUG-013 · Generated Files Directory Grows Without Bound

**File:** `backend/data/generated/` (175+ files observed)  
**Status:** Confirmed  

No cleanup policy. Each test run and each document generation request creates permanent files. No max age, no max count.

**Fix:** Add cleanup task on startup: delete files older than 7 days. Or add a housekeeping endpoint.

---

### BUG-014 · Session ID Not Validated Against Caller Identity

**File:** `backend/app/services/memory/persistent_memory.py`  
**Status:** Confirmed  

Client-supplied `session_id` UUID used directly as database key. Any session can read any other session's history by supplying a known UUID.

**Fix:** Requires authentication (BUG auth prerequisite) to bind sessions to users.

---

### BUG-015 · `wakeWordEnabled` Always Returns `True`

**File:** `backend/app/api/settings_api.py` line 47  
**Status:** Confirmed  

```python
wakeWordEnabled=True,  # hardcoded, no actual setting
```

Misleads the UI into showing wake word as always enabled when it may not be functional.

**Fix:** Add `JARVIS_WAKE_WORD_ENABLED` env var and wire to settings + response.

---

### BUG-016 · Dockerfile `generated_files` vs `generated` Mismatch

**File:** `Dockerfile` line 34  
**Status:** Confirmed  

```dockerfile
RUN mkdir -p /app/data/workspace /app/data/generated_files /app/data/uploads
```
But `settings.py` uses `data_dir / "generated"`. On container first run the app creates `generated/` itself via `self.generated_dir.mkdir(parents=True, exist_ok=True)`, but the Dockerfile `mkdir` creates a useless `generated_files/` directory.

**Fix:** Change Dockerfile to `mkdir -p /app/data/generated /app/data/uploads /app/data/projects`.

---

## 🟢 P3 — Low Priority / Cleanup

### BUG-017 · `AGENTS.md` Describes Agents That Don't Exist

**File:** `AGENTS.md`  
**Status:** Confirmed  

Math Agent, Multi-Doc Agent, Computer Agent are documented in the architecture matrix but have no corresponding Python files.

**Fix:** Update `AGENTS.md` to reflect actual implemented agents only. Remove phantom entries.

---

### BUG-018 · `requirements.txt` Lacks Patch Version Pinning

**File:** `backend/requirements.txt`  
**Status:** Confirmed  

```
fastapi>=0.115,<1
ddgs>=9.16.0        # no upper bound!
```

**Fix:** Generate `requirements.lock.txt` via `pip-compile requirements.txt`. Use lockfile in CI and Docker.

---

### BUG-019 · `ModelRouter` Allocates New Provider Instances on Every `route()` Call

**File:** `backend/app/services/ai/router.py` lines 116–177  
**Status:** Confirmed  

```python
gemini = GeminiProvider()      # allocates
if gemini.is_available(): ...
groq = GroqProvider()          # allocates again even if gemini was used
if groq.is_available(): ...
```

Multiple provider instances created on every routing decision (called per request).

**Fix:** Cache provider availability results for 30 seconds or use the existing `provider_health_registry`.

---

### BUG-020 · `test_artifact.txt` Committed to Repository Root

**File:** `test_artifact.txt` (repo root)  
**Status:** Confirmed  

A test artifact file left in the repository root. Should be in `.gitignore` and removed.

**Fix:** `git rm test_artifact.txt` and add `*.txt` exceptions or specific ignore rule.
