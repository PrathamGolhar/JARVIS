# JARVIS — Test Coverage Analysis

> **Historical snapshot:** File counts and coverage claims below describe an earlier test suite and have not been revalidated. See [TESTING.md](TESTING.md) for current validation commands.

**Audit Date:** 2026-11-23  
**Test Files Found:** 20 test files in `backend/tests/`  
**Test Runner:** pytest + pytest-asyncio  
**CI Coverage:** GitHub Actions `ci.yml` runs `python -m pytest -v --tb=short`

---

## 1. Test Files Inventory

| Test File | Subsystem Covered | Quality | Notes |
|---|---|---|---|
| `test_health.py` | Health endpoints | Good | Basic smoke tests |
| `test_chat.py` | Chat API + orchestration | Adequate | Uses mocked orchestrator |
| `test_tools.py` | Tool registry + calculator | Good | Covers safe tools |
| `test_code_sandbox.py` | Code execution | Partial | No escape tests |
| `test_agents_and_planner.py` | PlanningEngine | Adequate | Keyword detection |
| `test_ai_provider_config.py` | Provider configuration | Good | Local provider only |
| `test_capabilities.py` | Capability registry | Good | Approval status checks |
| `test_diagnostics.py` | Diagnostics API | Good | Metric response shapes |
| `test_document_generation.py` | PDF/DOCX/PPTX/XLSX | Good | File creation + size |
| `test_e2e_smoke.py` | End-to-end pipeline | Partial | Local provider only |
| `test_files.py` | File upload/download | Adequate | Extension + size limits |
| `test_jarvis2_core.py` | Core architecture | Adequate | Imports + settings |
| `test_local_actions.py` | Desktop app launcher | Good | Allowlist enforcement |
| `test_mission_regressions.py` | Regression scenarios | Adequate | Key user flows |
| `test_permission_mode.py` | Permission enforcement | Adequate | read_only mode |
| `test_projects_and_memory.py` | Projects + memory | Good | CRUD operations |
| `test_runtime_repairs.py` | Runtime resilience | Adequate | Error handling |
| `test_speech.py` | TTS/STT endpoints | Partial | Groq not tested |
| `test_study_mode.py` | Study notes generation | Good | Mock AI response |
| `test_web_actions.py` | Web action planning | Good | URL generation |

---

## 2. Coverage Gaps — Critical Missing Tests

### 2.1 Security Tests (ALL MISSING)

| Missing Test | Risk | Description |
|---|---|---|
| Sandbox escape via `import subprocess` | P0 | Confirm blocked or confirm vulnerability |
| Sandbox escape via `import os` | P0 | File access outside temp dir |
| Sandbox escape via `import socket` | P0 | Network access from sandbox |
| `permission_mode` injection | P0 | Set `"hacker"` mode via settings API |
| Unauthenticated settings update | P0 | No auth required |
| Path traversal via `read_file` with `../../../../etc/passwd` | P1 | Confirm blocked |
| SSRF in `web_reader.py` with private-IP domain | P1 | DNS rebinding bypass |
| Cross-session memory read | P2 | Use session_id of another session |
| Confirmation token replay after TTL | P1 | Execute old token |
| Generated file access from different session | P2 | Download other session's files |

### 2.2 Reliability Tests (MISSING)

| Missing Test | Risk | Description |
|---|---|---|
| Concurrent chat requests | P1 | Blocking I/O impact on throughput |
| Rate limit enforcement | P1 | >10 req/min behavior |
| AI provider failover sequence | P2 | Gemini fails → Groq succeeds |
| Tool iteration limit (max_tool_iterations=8) | P2 | Fallback when iterations exceeded |
| RAG persistence across restart | P2 | Chunks lost after restart |
| Confirmation token TTL expiry | P1 | Token rejected after 60s |

### 2.3 Functional Tests (PARTIAL)

| Missing Test | Description |
|---|---|
| `ModelRouter` task classification | TaskCategory assignment for each input type |
| `TaskGraph` DAG execution order | Dependency resolution correctness |
| `EventBus` publish/subscribe | Listener invocation |
| BM25 search accuracy | RAG search returns most relevant chunk |
| Groq primary vs fallback model selection | 429 triggers fallback |
| Document generation with Unicode content | Non-ASCII in PDF/DOCX |
| File upload followed by RAG search | End-to-end RAG pipeline |

---

## 3. Code Sandbox Test Gap — Detail

`test_code_sandbox.py` exists but covers only the happy path:
```python
def test_execute_valid_python():
    result = execute_sandboxed_code("print('hello')")
    assert result.ok
    assert "hello" in result.stdout
```

**Missing:**
```python
def test_sandbox_blocks_subprocess():
    result = execute_sandboxed_code("import subprocess; subprocess.run(['whoami'])")
    assert not result.ok   # CURRENTLY FAILS — subprocess is NOT blocked

def test_sandbox_blocks_os():
    result = execute_sandboxed_code("import os; os.listdir('/')")
    assert not result.ok   # CURRENTLY FAILS — os is NOT blocked

def test_sandbox_blocks_network():
    result = execute_sandboxed_code("import socket; socket.create_connection(('google.com', 80))")
    assert not result.ok   # CURRENTLY FAILS — network is NOT blocked
```

---

## 4. Test Infrastructure Assessment

| Aspect | Status | Notes |
|---|---|---|
| `conftest.py` | ✅ Present | FastAPI TestClient, temp DB fixture |
| Mocking strategy | ⚠️ Partial | AI providers mocked via monkeypatch |
| Async tests | ✅ Supported | pytest-asyncio configured |
| Test isolation | ✅ Present | Each test gets its own temp DB |
| Environment isolation | ✅ CI sets `JARVIS_AI_PROVIDER=local` | Prevents live API calls in CI |
| Test output size | ✅ Healthy | Tests run without hanging |
| Coverage measurement | ❌ Missing | No `pytest-cov` configured |

---

## 5. Recommended Additional Test Files

```
backend/tests/
├── test_security_sandbox.py          # Sandbox escape attempts
├── test_security_path_traversal.py   # File access outside workspace
├── test_security_ssrf.py             # SSRF bypass attempts
├── test_security_permission_mode.py  # Permission bypass
├── test_security_auth.py             # Unauthenticated endpoint access
├── test_concurrency.py               # Concurrent requests + blocking I/O
├── test_model_router.py              # TaskClassifier + RouteDecision
├── test_task_graph.py                # DAG execution + parallelism
├── test_event_bus.py                 # Publish/subscribe
├── test_rag_pipeline.py              # Upload → index → search
└── test_provider_failover.py         # Failover sequence simulation
```

---

## 6. CI Pipeline Assessment

| Step | Status | Notes |
|---|---|---|
| Python 3.11 setup | ✅ | Correct version |
| pip caching | ✅ | Using requirements.txt hash |
| Test run | ✅ | `python -m pytest -v --tb=short` |
| Coverage report | ❌ Missing | No `--cov` flag |
| Node 20 setup | ✅ | Correct version |
| `npm ci` (frozen lockfile) | ✅ | Reproducible install |
| TypeScript type check + build | ✅ | `npm run build` |
| Artifact integrity check | ✅ | `test -f dist/index.html` |
| E2E browser tests | ❌ Missing | No Playwright/Cypress |
| Security scan (Bandit/Semgrep) | ❌ Missing | No SAST tool |
| Dependency vulnerability scan | ❌ Missing | No `pip-audit` or `npm audit` |

---

## 7. Priority Test Implementation Order

1. **P0:** `test_security_sandbox.py` — establish whether escape is possible
2. **P0:** `test_security_auth.py` — establish authentication gap
3. **P0:** `test_security_permission_mode.py` — permission bypass
4. **P1:** `test_security_ssrf.py` — SSRF validation
5. **P1:** `test_provider_failover.py` — failover correctness
6. **P2:** `test_model_router.py` — routing classification
7. **P2:** `test_rag_pipeline.py` — upload to search
8. **P3:** Add `--cov` to CI for coverage reporting
