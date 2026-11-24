# JARVIS — Remediation Roadmap

> **Historical planning snapshot:** Recommendations and status below have not been reconciled with the current workspace. Use current source and canonical documentation for implementation decisions.

**Audit commit:** `6b00368`  
**Generated:** 2026-11-23  
**Cross-references:** `AUDIT_REPORT.md`, `SECURITY_FINDINGS.md`, `BUG_BACKLOG.md`

---

## Reading this document

| Column | Meaning |
|--------|---------|
| **Ref** | Finding ID from AUDIT_REPORT (F-xxx), SECURITY_FINDINGS (SEC-xxx), or BUG_BACKLOG (BUG-xxx) |
| **Priority** | P0 = stop-the-line / P1 = this sprint / P2 = next sprint / P3 = backlog |
| **Effort** | XS < 1 h · S < 4 h · M < 1 d · L < 3 d · XL ≥ 3 d |
| **Risk** | Regression risk of the fix itself |
| **Blocker** | Must be done before this item (dependency) |

A finding blocked by an unresolved prerequisite **must not** be shipped first; doing so will give a false sense of security.

---

## Dependency graph

```
SEC-001 (no-auth)
  └─► SEC-003 (settings injection)   must follow auth
  └─► F-018 (session isolation)      must follow auth

SEC-002 (sandbox isolation)
  └─► (independent — do first)

SEC-005 (web_reader SSRF)
  └─► (independent — 3-line fix)

SEC-004 (token TTL)
  └─► (independent)

F-006  (permission_mode bypass)
  └─► (independent, but SEC-001 raises impact)

F-007  (wire ModelRouter)
  └─► F-008 (wire EventBus) can follow independently
  └─► F-015 (enforce permissions.py) depends on orchestrator refactor

F-009  (blocking I/O)
  └─► No hard dependency, but should precede rate-limiting (F-010)
      to avoid masking real throughput

BUG-002 (Groq model inversion)
  └─► (independent, single-line)

F-016  (RAG persistence)
  └─► Requires SQLite schema migration; do after auth so schema is stable
```

---

## Phase 0 — Security Critical (This Week)

> Stop all deployments or external sharing until Phase 0 is complete.

### 0-A · Add authentication to every API endpoint
| Field | Value |
|-------|-------|
| **Refs** | SEC-001, F-001 |
| **Priority** | P0 |
| **Effort** | L |
| **Risk** | Medium — existing integrations without tokens will break; must version-bump API or document migration |
| **Blocker** | None |

**What to do:**

1. Add a `SECRET_KEY` to `.env` and `settings.py`.
2. Create `backend/app/api/auth.py` with an OAuth2 Password Bearer flow using `python-jose` + `passlib`.
3. Register a `POST /api/auth/token` endpoint (outside the auth guard).
4. Add `Depends(get_current_user)` to **every** existing router: `/api/chat`, `/api/settings`, `/api/files/*`, `/api/projects/*`, `/api/memory/*`, `/api/research`.
5. For single-user local deployments, support a simple static API-key header as an alternative (`X-JARVIS-Key`).
6. Update `docker-compose.yml` to inject `SECRET_KEY` via environment.
7. Update README "Getting Started" section.

**Test to establish resolution:**
```python
# tests/test_auth.py
def test_chat_requires_auth(client):
    r = client.post("/api/chat", json={...})
    assert r.status_code == 401

def test_valid_token_allows_chat(client, auth_token):
    r = client.post("/api/chat", json={...}, headers={"Authorization": f"Bearer {auth_token}"})
    assert r.status_code != 401
```

---

### 0-B · Sandbox OS isolation
| Field | Value |
|-------|-------|
| **Refs** | SEC-002, F-002, BUG-001 |
| **Priority** | P0 |
| **Effort** | M |
| **Risk** | Low — sandbox is currently useless for security; any restriction is improvement |
| **Blocker** | None |

**What to do (two layers, both required):**

**Layer 1 — AST deny-list in `sandbox.py`:**
```python
BLOCKED_MODULES = {
    "os", "sys", "subprocess", "socket", "shutil", "importlib",
    "builtins", "ctypes", "multiprocessing", "threading",
    "pathlib", "glob", "tempfile", "io",
}

class _ImportBlocker(ast.NodeVisitor):
    def visit_Import(self, node):
        for alias in node.names:
            root = alias.name.split(".")[0]
            if root in BLOCKED_MODULES:
                raise SecurityError(f"Import of '{alias.name}' is not permitted.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module and node.module.split(".")[0] in BLOCKED_MODULES:
            raise SecurityError(f"Import from '{node.module}' is not permitted.")
        self.generic_visit(node)
```

Add this visitor pass **before** `exec()` is called.

**Layer 2 — Process-level isolation (Docker deployments):**
Add a `sandbox` service in `docker-compose.yml` using `gVisor` (runsc) or `nsjail`. Route all `execute_code` tool calls to this service over a local socket. Document as optional for local runs, required for multi-user deployments.

**Test to establish resolution:**
```python
def test_sandbox_blocks_os_import(client):
    r = client.post("/api/sandbox/execute", json={"code": "import os; os.listdir('/')"})
    assert r.json()["success"] is False
    assert "not permitted" in r.json()["error"]

def test_sandbox_blocks_subprocess(client):
    r = client.post("/api/sandbox/execute", json={"code": "import subprocess; subprocess.run(['id'])"})
    assert r.json()["success"] is False
```

---

### 0-C · Settings endpoint injection protection
| Field | Value |
|-------|-------|
| **Refs** | SEC-003, F-003 |
| **Priority** | P0 |
| **Effort** | S |
| **Risk** | Low |
| **Blocker** | 0-A (auth) — must be authenticated before this is fully safe |

**What to do:**

1. Apply auth guard (0-A) to `POST /api/settings` immediately.
2. Add an allowlist of writable keys in `settings_api.py`:
   ```python
   WRITABLE_SETTINGS = {
       "GROQ_MODEL_FAST", "GROQ_MODEL_SMART", "GEMINI_MODEL",
       "VOICE_ENABLED", "WAKE_WORD_ENABLED", "TTS_VOICE",
       "PERMISSION_MODE",
   }
   NEVER_LOG_KEYS = {"GROQ_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY"}

   for key in payload:
       if key not in WRITABLE_SETTINGS:
           raise HTTPException(403, f"Key '{key}' is not writable via API")
   ```
3. Confirm API key values are stripped from diagnostic `GET /api/settings` response (already partially done — verify completeness).

**Test:**
```python
def test_settings_rejects_unknown_key(auth_client):
    r = auth_client.post("/api/settings", json={"EVIL_KEY": "value"})
    assert r.status_code == 403

def test_settings_diagnostic_hides_api_keys(auth_client):
    r = auth_client.get("/api/settings")
    body = r.json()
    for key in ("GROQ_API_KEY", "GEMINI_API_KEY"):
        assert key not in body or body.get(key) in ("", "***", None)
```

---

### 0-D · Fix web_reader.py SSRF
| Field | Value |
|-------|-------|
| **Refs** | SEC-005, BUG-012 |
| **Priority** | P0 |
| **Effort** | XS |
| **Risk** | Negligible |
| **Blocker** | None |

**What to do** (3-line fix in `web_reader.py`):
```python
import socket

def _is_private_host(hostname: str) -> bool:
    try:
        ip = socket.gethostbyname(hostname)        # resolve first
    except socket.gaierror:
        return True                                 # treat unresolvable as private
    return ipaddress.ip_address(ip).is_private or \
           ipaddress.ip_address(ip).is_loopback or \
           ipaddress.ip_address(ip).is_link_local
```

This matches the already-correct pattern in `researcher.py`.

**Test:**
```python
def test_web_reader_blocks_internal_via_dns(client):
    # Assumes internal.corp resolves to 10.x.x.x in test env — mock with monkeypatch
    with monkeypatch.setattr("socket.gethostbyname", lambda h: "10.0.0.1"):
        r = client.post("/api/tools/web_read", json={"url": "http://internal.corp/secret"})
        assert r.status_code == 400
```

---

### 0-E · Confirmation token TTL
| Field | Value |
|-------|-------|
| **Refs** | SEC-004, BUG-013 |
| **Priority** | P0 |
| **Effort** | XS |
| **Risk** | Negligible |
| **Blocker** | None |

**What to do** in `orchestrator.py`:
```python
import time
_PENDING_CONFIRMATIONS: dict[str, tuple[dict, float]] = {}   # token → (action, expires_at)
TTL_SECONDS = 300  # 5 minutes

# On store:
_PENDING_CONFIRMATIONS[token] = (action_dict, time.time() + TTL_SECONDS)

# On consume:
entry = _PENDING_CONFIRMATIONS.pop(token, None)
if entry is None:
    raise HTTPException(404, "Token not found")
action_dict, expires_at = entry
if time.time() > expires_at:
    raise HTTPException(410, "Confirmation token expired")
```

**Test:**
```python
def test_expired_confirmation_token_rejected(client, monkeypatch):
    monkeypatch.setattr("time.time", lambda: 999999999)
    r = client.post("/api/confirm", json={"token": "stale-token"})
    assert r.status_code in (404, 410)
```

---

### 0-F · Permission mode bypass hardening
| Field | Value |
|-------|-------|
| **Refs** | F-006, SEC-006 |
| **Priority** | P0 |
| **Effort** | XS |
| **Risk** | Negligible |
| **Blocker** | None |

**What to do** in `permissions.py`:
```python
from enum import Enum

class PermissionMode(str, Enum):
    READ_ONLY = "read_only"
    ASSISTED = "assisted"
    FULL_CONTROL = "full_control"

# In Settings:
permission_mode: PermissionMode = PermissionMode.ASSISTED

# In permissions.py capability checks — replace string comparison with enum:
if self.mode == PermissionMode.READ_ONLY:
    ...
```

Reject any value not in the enum at settings-load time (Pydantic will raise `ValidationError` automatically).

---

## Phase 1 — Reliability (This Sprint, ≤2 weeks)

### 1-A · Replace blocking I/O with async providers
| Field | Value |
|-------|-------|
| **Refs** | F-009, BUG-003 |
| **Priority** | P1 |
| **Effort** | L |
| **Risk** | Medium — rewrites hot path; needs integration test |
| **Blocker** | None (but do before 1-B rate limiting) |

**What to do:**

Option A (preferred) — migrate `groq_provider.py`, `gemini_provider.py`, `local_provider.py` to use `httpx.AsyncClient`:
```python
async def generate(self, messages, model, **kwargs):
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(self.url, headers=self.headers, json=payload)
        resp.raise_for_status()
        return resp.json()
```

Option B (interim) — wrap each sync call site in `orchestrator.py`:
```python
response = await asyncio.get_event_loop().run_in_executor(None, sync_provider.generate, messages)
```

Option A is preferred; Option B is acceptable as an unblocking measure while A is developed.

---

### 1-B · Rate limiting
| Field | Value |
|-------|-------|
| **Refs** | F-010, BUG-004 |
| **Priority** | P1 |
| **Effort** | S |
| **Risk** | Low |
| **Blocker** | 0-A (auth) so limits can be per-user, not just per-IP |

```python
# requirements.txt: slowapi>=0.1.9
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, ...):
    ...
```

---

### 1-C · Fix Groq model ID inversion
| Field | Value |
|-------|-------|
| **Refs** | BUG-002 |
| **Priority** | P1 |
| **Effort** | XS |
| **Risk** | Negligible |
| **Blocker** | None |

In `settings.py`, swap the defaults so that:
- `groq_model_fast` → `"llama-3.1-8b-instant"` (or equivalent lightweight model)
- `groq_model_smart` → `"llama-3.3-70b-versatile"` (or the 120b model if available)

Verify model IDs against `https://console.groq.com/docs/models` before merging.

---

### 1-D · Raise `max_tokens` for orchestrator
| Field | Value |
|-------|-------|
| **Refs** | F-017, BUG-007 |
| **Priority** | P1 |
| **Effort** | XS |
| **Risk** | Low (cost increase) |
| **Blocker** | None |

Change orchestrator default from `800` to `4096` (or make it configurable via `settings.py`). Log a warning when a response is exactly `max_tokens` long (likely truncated).

---

### 1-E · Generated-file cleanup policy
| Field | Value |
|-------|-------|
| **Refs** | F-013, BUG-005 |
| **Priority** | P1 |
| **Effort** | S |
| **Risk** | Low |
| **Blocker** | None |

Implement a retention policy for `backend/data/generated/`:
```python
# On startup and hourly via asyncio.create_task
async def _cleanup_generated(max_age_days=7, max_total_mb=500):
    cutoff = time.time() - max_age_days * 86400
    total = 0
    for f in sorted(Path(GENERATED_DIR).iterdir(), key=lambda p: p.stat().st_mtime):
        stat = f.stat()
        total += stat.st_size
        if stat.st_mtime < cutoff or total > max_total_mb * 1024 * 1024:
            f.unlink()
```

---

### 1-F · Fix dependency versions
| Field | Value |
|-------|-------|
| **Refs** | F-020, BUG-016 |
| **Priority** | P1 |
| **Effort** | S |
| **Risk** | Low — may surface incompatibilities, which is the point |
| **Blocker** | None |

1. Run `pip-compile requirements.in --generate-hashes -o requirements.txt` to pin all transitive deps.
2. Set explicit version floors for the 19 direct deps (e.g. `fastapi>=0.111,<0.112`).
3. Add `pip-audit` to CI (see Phase 4).

---

## Phase 2 — Architecture Wire-Up (Next Sprint, ≤4 weeks)

> These items fix architectural disconnects — components exist but are not wired into the execution path.

### 2-A · Wire ModelRouter/TaskClassifier into orchestrator
| Field | Value |
|-------|-------|
| **Refs** | F-007, BUG-008 |
| **Priority** | P1 |
| **Effort** | M |
| **Risk** | Medium — changes orchestrator core path |
| **Blocker** | 1-A (async providers) should be done first |

**What to do** in `orchestrator.py → process_message()`:
```python
from app.services.ai.router import ModelRouter

router = ModelRouter(settings)

async def process_message(message, context, settings):
    task_type = router.classify_task(message)          # currently unused
    model_config = router.get_model_for_task(task_type)
    provider = factory.get_provider(model_config.provider)
    response = await provider.generate(messages, model_config.model)
    ...
```

Add a regression test that sends a "write code" message and asserts the coding-tier model was selected.

---

### 2-B · Wire EventBus subscribers
| Field | Value |
|-------|-------|
| **Refs** | F-008, BUG-009 |
| **Priority** | P2 |
| **Effort** | M |
| **Risk** | Low — additive |
| **Blocker** | 2-A (orchestrator refactor makes subscription points clearer) |

**What to do:**

1. Register subscribers in `main.py` lifespan:
   ```python
   event_bus.subscribe("tool_executed", log_tool_event)
   event_bus.subscribe("ai_response", update_conversation_memory)
   event_bus.subscribe("error", send_error_to_frontend_ws)
   ```
2. Publish from orchestrator at key transitions:
   ```python
   await event_bus.publish("tool_executed", {"tool": name, "result": result})
   await event_bus.publish("ai_response", {"response": text, "task_type": task_type})
   ```
3. Add a WebSocket event stream endpoint (`GET /api/events/stream`) for frontend real-time updates.

---

### 2-C · Enforce permissions.py tool approval
| Field | Value |
|-------|-------|
| **Refs** | F-015, BUG-011 |
| **Priority** | P1 |
| **Effort** | S |
| **Risk** | Low |
| **Blocker** | 0-A (auth), 0-F (permission mode enum) |

In `orchestrator.py → execute_tool_call()` (or equivalent), add:
```python
from app.services.permissions import PermissionRegistry

registry = PermissionRegistry(settings)

async def execute_tool_call(tool_name, args, settings):
    approval = registry.validate_tool_approval(tool_name, args)
    if approval.requires_confirmation:
        return await _request_confirmation(tool_name, args)
    if not approval.allowed:
        return ToolResult(error=f"Tool '{tool_name}' not permitted in current mode")
    return await _run_tool(tool_name, args)
```

---

### 2-D · Fix PlanningEngine step status
| Field | Value |
|-------|-------|
| **Refs** | F-014, BUG-010 |
| **Priority** | P2 |
| **Effort** | XS |
| **Risk** | Negligible |
| **Blocker** | None |

In `planner.py`, change:
```python
# Before (broken):
steps[0]["status"] = "completed"

# After:
steps[0]["status"] = "pending"
```

This prevents the first step from appearing completed before execution begins.

---

### 2-E · Wire TaskGraph into execution
| Field | Value |
|-------|-------|
| **Refs** | F-007 (secondary), BUG-008 |
| **Priority** | P2 |
| **Effort** | L |
| **Risk** | Medium — significant orchestrator change |
| **Blocker** | 2-A, 2-C |

**What to do:**

1. In `orchestrator.py`, after `PlanningEngine.create_plan()`, instantiate `TaskGraph` with the returned steps.
2. Execute tasks in topological order, allowing truly independent tasks to run concurrently via `asyncio.gather()`.
3. Pass task results downstream using `TaskGraph.update_task_status()`.
4. Update `OutputVerifier` to verify each task result, not just file outputs.

---

## Phase 3 — Quality & Persistence (Weeks 5–8)

### 3-A · RAG/vector store persistence
| Field | Value |
|-------|-------|
| **Refs** | F-016, BUG-012 |
| **Priority** | P2 |
| **Effort** | M |
| **Risk** | Low |
| **Blocker** | None (schema stable after Phase 0) |

Replace in-memory BM25 with a persistent SQLite FTS5 store or integrate `chromadb`/`qdrant-client` (already in `requirements.txt`). Persist the index to `backend/data/memory/vector_store.db`.

---

### 3-B · Wire OutputVerifier to tool results
| Field | Value |
|-------|-------|
| **Refs** | F-015 (secondary), BUG-011 |
| **Priority** | P2 |
| **Effort** | S |
| **Risk** | Low |
| **Blocker** | 2-E (TaskGraph) |

Extend `verifier.py` from file-only to generic tool-result verification:
```python
async def verify_tool_result(self, tool_name: str, result: dict) -> VerificationResult:
    if result.get("error"):
        return VerificationResult(passed=False, reason=result["error"])
    if tool_name == "execute_code" and not result.get("output"):
        return VerificationResult(passed=False, reason="Code execution returned no output")
    return VerificationResult(passed=True)
```

---

### 3-C · Remove SSE signature workaround
| Field | Value |
|-------|-------|
| **Refs** | F-012, BUG-006 |
| **Priority** | P3 |
| **Effort** | S |
| **Risk** | Low |
| **Blocker** | None |

Identify and remove the SSE callback signature hack in the streaming path. Use a proper `StreamingResponse` with `asyncio.Queue` instead.

---

### 3-D · Fix `wakeWordEnabled` schema mismatch
| Field | Value |
|-------|-------|
| **Refs** | F-023, BUG-020 |
| **Priority** | P3 |
| **Effort** | XS |
| **Risk** | Negligible |
| **Blocker** | None |

Align the frontend key `wakeWordEnabled` with the backend `WAKE_WORD_ENABLED` setting — either normalise in the settings API or update the frontend to use snake_case consistently.

---

## Phase 4 — Test Coverage (Weeks 7–10)

### 4-A · Security regression tests
| Field | Value |
|-------|-------|
| **Refs** | TEST_COVERAGE_ANALYSIS.md |
| **Priority** | P1 |
| **Effort** | M |
| **Risk** | Negligible |
| **Blocker** | Phase 0 fixes must exist first |

Create `backend/tests/test_security.py` covering:
- Unauthenticated access to every protected endpoint → 401
- Sandbox OS import attempts → blocked
- File path traversal attempts → 400/403
- SSRF via DNS rebinding mock → 400
- Stale confirmation token → 404/410
- Settings write with invalid key → 403

---

### 4-B · Integration test for orchestrator pipeline
| Field | Value |
|-------|-------|
| **Refs** | TEST_COVERAGE_ANALYSIS.md |
| **Priority** | P1 |
| **Effort** | M |
| **Risk** | Negligible |
| **Blocker** | Phase 2 (architecture wired) |

Create `backend/tests/test_orchestrator_integration.py`:
- `test_coding_message_routes_to_coding_model()`
- `test_research_message_uses_deep_research_path()`
- `test_tool_call_respects_read_only_permission_mode()`
- `test_task_graph_executes_independent_steps_concurrently()`
- `test_full_pipeline_listen_understand_plan_execute_verify_respond()`

---

### 4-C · Add Bandit SAST and pip-audit to CI
| Field | Value |
|-------|-------|
| **Refs** | F-020, CI gap |
| **Priority** | P1 |
| **Effort** | S |
| **Risk** | Negligible |
| **Blocker** | None |

Add to `.github/workflows/ci.yml`:
```yaml
- name: Security audit (pip-audit)
  run: pip-audit -r backend/requirements.txt

- name: SAST (bandit)
  run: bandit -r backend/app -ll -x backend/app/tests
```

---

### 4-D · Coverage enforcement
| Field | Value |
|-------|-------|
| **Refs** | TEST_COVERAGE_ANALYSIS.md |
| **Priority** | P2 |
| **Effort** | S |
| **Risk** | Low |
| **Blocker** | 4-A, 4-B |

Add to `ci.yml`:
```yaml
- name: Run tests with coverage
  run: pytest --cov=app --cov-report=xml --cov-fail-under=70
```

Start at 70%; raise to 85% after Phase 2 integration tests land.

---

## Phase 5 — Documentation & Cleanup (Ongoing)

### 5-A · Update AGENTS.md architecture description
| Field | Value |
|-------|-------|
| **Refs** | F-019 |
| **Priority** | P3 |
| **Effort** | S |
| **Risk** | Negligible |
| **Blocker** | Phase 2 (so actual wiring matches what's written) |

Rewrite the AGENTS.md "Agent Ecosystem Matrix" and "Multi-Agent Task Dependency Graph" sections to reflect actual component wiring after Phase 2. Document which architectural components are aspirational vs. implemented.

---

### 5-B · Fix Dockerfile security
| Field | Value |
|-------|-------|
| **Refs** | F-021, BUG-017 |
| **Priority** | P2 |
| **Effort** | XS |
| **Risk** | Negligible |
| **Blocker** | None |

```dockerfile
# Add before final CMD:
RUN addgroup --system jarvis && adduser --system --ingroup jarvis jarvis
USER jarvis
```

Add `HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1`.

---

### 5-C · README accuracy
| Field | Value |
|-------|-------|
| **Refs** | General |
| **Priority** | P3 |
| **Effort** | S |
| **Risk** | Negligible |
| **Blocker** | Phase 0, 1, 2 (so README reflects real state) |

Update:
- Architecture diagram to match actual component wiring.
- "Features" list to remove claims about TaskGraph and EventBus until Phase 2 is complete.
- Add "Security" section documenting the auth flow added in Phase 0.
- Document `PERMISSION_MODE` values and their effects.

---

## Summary table

| Phase | Item | Ref | Priority | Effort | Blocker |
|-------|------|-----|----------|--------|---------|
| 0 | Add authentication | SEC-001/F-001 | P0 | L | — |
| 0 | Sandbox OS isolation | SEC-002/F-002 | P0 | M | — |
| 0 | Settings injection fix | SEC-003/F-003 | P0 | S | 0-A |
| 0 | SSRF fix (web_reader) | SEC-005 | P0 | XS | — |
| 0 | Confirmation token TTL | SEC-004 | P0 | XS | — |
| 0 | Permission mode enum | F-006 | P0 | XS | — |
| 1 | Async I/O providers | F-009 | P1 | L | — |
| 1 | Rate limiting | F-010 | P1 | S | 0-A |
| 1 | Groq model fix | BUG-002 | P1 | XS | — |
| 1 | Raise max_tokens | F-017 | P1 | XS | — |
| 1 | Generated file cleanup | F-013 | P1 | S | — |
| 1 | Pin dependencies | F-020 | P1 | S | — |
| 2 | Wire ModelRouter | F-007 | P1 | M | 1-A |
| 2 | Wire EventBus | F-008 | P2 | M | 2-A |
| 2 | Enforce permissions | F-015 | P1 | S | 0-A, 0-F |
| 2 | Fix planner step status | F-014 | P2 | XS | — |
| 2 | Wire TaskGraph | F-007 | P2 | L | 2-A, 2-C |
| 3 | RAG persistence | F-016 | P2 | M | — |
| 3 | Wire OutputVerifier | F-015 | P2 | S | 2-E |
| 3 | Remove SSE hack | F-012 | P3 | S | — |
| 3 | Fix wakeWordEnabled | F-023 | P3 | XS | — |
| 4 | Security regression tests | — | P1 | M | Phase 0 |
| 4 | Orchestrator integration tests | — | P1 | M | Phase 2 |
| 4 | Bandit + pip-audit in CI | F-020 | P1 | S | — |
| 4 | Coverage enforcement | — | P2 | S | 4-A, 4-B |
| 5 | Update AGENTS.md | F-019 | P3 | S | Phase 2 |
| 5 | Dockerfile non-root user | F-021 | P2 | XS | — |
| 5 | README accuracy | — | P3 | S | Phase 2 |

---

## Features to preserve throughout all phases

> These are confirmed-working and must not be broken by any fix.

| Feature | Location | Why it must be preserved |
|---------|----------|--------------------------|
| Path traversal protection | `file_tools.py → _resolve_safe_path()` | Correctly prevents `../` escapes |
| Calculator AST safety | `calculator.py` | Prevents `eval()` injection |
| SSRF protection in researcher | `researcher.py` | DNS-resolves before IP check |
| Local actions allowlist | `local_actions.py` | Hardcoded app tuple; no injection vector |
| Provider failover cascade | `factory.py` | Graceful degradation across Groq→Gemini→local |
| Edge-TTS voice synthesis | `groq_stt.py` / TTS path | Core UX feature |
| BM25 keyword search | `vector_store.py` | Works correctly as search; persistence is additive |

---

## Risks that cannot yet be verified

1. **Groq model IDs** — `openai/gpt-oss-20b` / `openai/gpt-oss-120b` may not be valid Groq endpoint model names. Verify against live Groq console before Phase 1-C.
2. **Concurrent load behaviour** — Blocking I/O impact under real concurrent requests has not been load-tested; actual degradation may be more or less severe than estimated.
3. **Frontend test coverage** — `frontend/` was not inspected in depth; TypeScript component tests and E2E tests (if any) have not been assessed.
4. **`ddgs` API stability** — DuckDuckGo's unofficial API has broken on major version bumps before. The wide `>=9.16.0` pin is a risk; a future `ddgs` update could silently break web search.
5. **Docker gVisor availability** — Phase 0-B Layer 2 (process sandbox) depends on `gVisor` or `nsjail` being available in the deployment environment; this cannot be verified without a target environment spec.

---

*This roadmap is ordered by risk × dependency. No item in a later phase should be started until all P0 items in Phase 0 are closed. Re-triage after each phase completes.*
