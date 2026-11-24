# JARVIS 2.0 Testing Methodology & Evaluation Benchmarks

This document outlines testing standards, automated test suites, end-to-end evaluation workflows, and verification requirements for JARVIS 2.0.

---

## 1. Test Architecture

JARVIS 2.0 maintains a dual-layer test suite:
1. **Backend Integration & Unit Tests (Pytest)**: Located in `backend/tests/`
2. **Frontend Type & Build Validation (TypeScript + Vite)**: Located in `jarvis-frontend/`

---

## 2. Backend Test Suites

| Test Module | Coverage Area | Tests |
| :--- | :--- | :---: |
| `test_security_hardening.py` | Constant-time auth, authoritative permissions, confirmation tokens, SSRF, AST sandbox | 34 |
| `test_reliability.py` | Database WAL mode, concurrent threads, live hot backups, Circuit Breaker, tool timeouts | 10 |
| `test_agent_orchestration.py`| DAG cycle detection, failover state preservation, direct-answer path, prompt injection defense | 11 |
| `test_memory_rag.py` | Restart recovery, SQLite persistent RAG, session scoping, memory conflict detection | 5 |
| `test_e2e_workflows.py` | End-to-end workflows: research, uploads, PDF generation, coding sandbox, reminders | 11 |
| `test_jarvis2_core.py` | ModelRouter, TaskClassifier, TaskGraph DAG, EventBus, MathEngine, MultiDoc Reasoner | 7 |
| `test_chat.py` | Conversational orchestrator, tool calls, confirmation actions, fallback logic | 14 |
| `test_tools.py` | Tool registry, calculator AST evaluations, workspace confinement, SSRF prevention | 14 |
| `test_permission_mode.py` | READ ONLY, ASSISTED, and FULL CONTROL enforcement across tool executions | 10 |
| `test_permissions.py` | Capability status and role permission boundary checks | 8 |
| `test_projects.py` | Project workspace manager, task tracking, linked artifacts | 8 |
| `test_files.py` | Universal file upload, MIME detection, text extraction, empty file validation | 7 |
| `test_local_actions.py` | Host bridge application allowlists, confirmation security constraints, CORS origin | 6 |
| `test_settings.py` | Environment variable precedence, API key masking, default settings | 5 |
| Remaining Unit Suites | Code sandbox, document generators, study mode, speech services | 16 |
| **Total Passed Tests** | **Zero failures across all test suites** | **158** |

### Running the Test Suite:
```bash
cd backend
python -m pytest -v
```

---

## 3. Frontend Build Validation

To verify 0 TypeScript type errors and successful production asset bundling:
```bash
cd jarvis-frontend
npm run build
```

---

## 4. Benchmark Workflow Evaluation

Automated tests verify that JARVIS fulfills end-to-end benchmark scenarios:
- **Scenario A**: Upload PDF → Extract Structure → Generate Structured Notes → Output Verified PDF.
- **Scenario B**: Research Topic → Scrape Web Pages → Generate 16:9 Presentation → Output Verified PPTX.
- **Scenario C**: Code Debug Request → Isolate Subprocess Sandbox → Execute Test Suite → Output Verified Patch.
- **Scenario D**: Symbolic Math Query → Parse AST Expression → Compute Derivative / Determinant → Output Step-by-Step Rationale.
