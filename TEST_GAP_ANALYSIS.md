# JARVIS 2.0 — TEST GAP ANALYSIS & TEST MATRIX

**Audit Date:** November 24, 2026
**Auditor:** Principal QA & Security Engineer

---

## 1. Test Execution Audit Summary

- **Total Backend Tests Collected**: 167
- **Total Backend Tests Passed**: 167 (100%)
- **Total Backend Tests Failed**: 0
- **Total Frontend Tests**: 0 (No runner installed)

---

## 2. False-Green Analysis & The `JARVIS_ENV=test` Mask

A passing test suite does **not** prove system functionality in production. This audit identified a critical **false-green condition**:

```text
[Pytest Conftest: backend/tests/conftest.py]
os.environ["JARVIS_ENV"] = "test"  ----->  [backend/app/settings.py]
                                           auth_enabled = False (when ENV == "test")
                                                  │
                                                  ▼
                                       require_auth bypasses check!
                                       All 167 tests run unauthenticated!
```

### Consequences:
1. `test_chat.py`, `test_e2e_smoke.py`, and `test_e2e_workflows.py` pass without providing credentials because authentication is globally disabled in test mode.
2. The security suite (`test_security_hardening.py`) verifies that `require_auth` blocks unauthenticated calls **only** when explicitly monkeypatched with `settings.auth_enabled = True`.
3. Because the frontend never sends authentication credentials, **the entire system passes tests while being completely non-functional for real users**.

---

## 3. High-Priority Test Gaps

### GAP-01: End-to-End Authenticated Workflow Test in Development Mode
- **Current State**: Zero tests run `client.post("/api/chat")` under `JARVIS_ENV=development` with simulated frontend token exchange.
- **Risk**: Frontend auth breakages remain completely invisible to pytest.
- **Required Test**: A test fixture simulating browser boot:
  1. Boot backend with `settings.auth_enabled = True`.
  2. Exchange API key for session token at `POST /api/auth/token`.
  3. Send `POST /api/chat` with `Authorization: Bearer <session_token>`.
  4. Assert 200 OK.

### GAP-02: Action Confirmation End-to-End Serialization Test
- **Current State**: Current tests mock `execute_confirmed_action` or test unit logic, but failed to assert serialization of the full `ChatResponse` returned to the client.
- **Risk**: Pydantic alias errors (e.g. `tool_name` vs `toolName`) crash FastAPI at runtime with 500 errors.
- **Required Test**: Execute an end-to-end confirmation lifecycle where `confirmedActionId` is submitted and the HTTP response body is fully validated against `ChatResponse`.

### GAP-03: `ModelRouter` Live Chat Integration Test
- **Current State**: `ModelRouter` is only tested in `test_agent_orchestration.py` via direct method invocation (`router.route()`).
- **Risk**: Orchestrator never invokes router; router bugs do not impact chat tests, and chat tests do not verify routing.
- **Required Test**: Send coding, math, and research prompts to `/api/chat` and assert that `ModelRouter` was called and selected the appropriate provider/model tier.

### GAP-04: `TaskGraph` Live Orchestration Test
- **Current State**: `TaskGraph` is only tested with synthetic lambdas in `test_agent_orchestration.py`.
- **Risk**: DAG engine is completely disconnected from real user chat turns.
- **Required Test**: Trigger a multi-step user goal (e.g. "Search weather and system stats") and verify the orchestrator creates and executes a `TaskGraph` with concurrent execution.

### GAP-05: Complete Frontend Client & Component Test Suite
- **Current State**: 0 frontend unit or component tests exist in `jarvis-frontend`.
- **Risk**: UI crashes, state corruption in `speechManager.ts`, unhandled modal triggers, and API error regressions go undetected.
- **Required Test**: Install `vitest` + `@testing-library/react` and implement:
  - `client.test.ts`: Error handling, header injection, token rotation.
  - `ActionConfirmationModal.test.tsx`: Render target parameters, confirm/cancel callbacks.
  - `speechManager.test.ts`: VAD state transitions and barge-in handling.
