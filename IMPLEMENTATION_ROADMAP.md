# JARVIS 2.0 — IMPLEMENTATION & REMEDIATION ROADMAP

> **Historical planning snapshot:** This roadmap records recommendations from its stated audit date. The canonical frontend path is now `frontend/`; references to `jarvis-frontend/` and other recommendations are preserved as historical and have not been revalidated.

**Audit Date:** November 24, 2026
**Auditor:** Principal Software Architect & Release Engineer

---

## 1. Guiding Engineering Principles
1. **Security Over Convenience**: Never weaken authentication or sandbox boundaries to fix integration issues.
2. **Reliability Over Feature Count**: Restore end-to-end user operation before building new capabilities.
3. **Evidence Over Assumptions**: Every stage must conclude with executed, passing tests.
4. **Anti-Regression Mandate**: Preserve all 167 passing backend tests and the 0-error TypeScript build.

---

## 2. Phased Implementation Roadmap

### Phase 1: Operational Restitution (P0 Blockers)
*Goal: Restore 100% functional end-to-end chat, settings, and action confirmation from the web UI.*

1. **Step 1.1: Frontend Client Authentication Layer**
   - Create centralized `apiClient` in `jarvis-frontend/src/api/client.ts`.
   - Implement bootstrap session token acquisition (`POST /api/auth/token`).
   - Automatically inject `Authorization: Bearer <token>` into all outbound HTTP requests.
   - Add API key input to Settings modal for explicit key configuration.
2. **Step 1.2: Schema Alias & Serialization Fix**
   - In `backend/app/schemas.py`, add `model_config = ConfigDict(populate_by_name=True)` to `ToolEvent`, `PendingAction`, `PlanStep`, and `ChatResponse`.
   - In `backend/app/services/orchestrator.py`, standardize dictionary keys to `"toolName"`.
   - Verify action confirmation lifecycle completes without 500 error.
3. **Step 1.3: End-to-End Auth Regression Tests**
   - Add automated test verifying that with `auth_enabled=True`, unauthenticated calls fail with 401 and authenticated calls succeed with 200.

---

### Phase 2: AI Intelligence & Orchestration Activation (P1 Disconnects)
*Goal: Turn disconnected components (ModelRouter and TaskGraph) into active runtime systems.*

1. **Step 2.1: ModelRouter Integration**
   - Wire `model_router.route()` into `orchestrator.py::run_orchestration()`.
   - Ensure task classification drives model tier selection while respecting circuit breaker availability.
   - Maintain manual provider/model override capability in Settings.
2. **Step 2.2: TaskGraph DAG Concurrency in Chat Loop**
   - Adapt `run_orchestration()` to construct a `TaskGraph` when multi-step plans require multiple independent tools.
   - Execute independent nodes concurrently with `asyncio.gather` bounded by `Semaphore(4)`.
   - Maintain sequential fallback for dependent tasks.
3. **Step 2.3: Multimodal Vision Implementation**
   - Add optional `images: list[str]` to `ChatRequest` schema.
   - Update `GeminiProvider.chat()` to parse base64 data URIs into Gemini inline data parts.
   - Add image attachment and preview UI to `jarvis-frontend/src/App.tsx`.

---

### Phase 3: Secondary Hardening & Test Modernization (P1 & P2 Gaps)
*Goal: Close test gaps, secure secondary endpoints, and clean architecture.*

1. **Step 3.1: Frontend Test Suite Initialization**
   - Install `vitest`, `@testing-library/react`, and `@testing-library/jest-dom`.
   - Write unit tests for API clients, confirmation dialogs, and speech state machine.
   - Add `npm test` to CI pipeline.
2. **Step 3.2: Secure Speech API Endpoints**
   - Add `dependencies=[Depends(require_auth)]` to `backend/app/api/speech.py`.
   - Update frontend `speech.ts` to pass bearer credentials.
3. **Step 3.3: Scope Memory Preferences**
   - Add `session_id` filter to `memory_store.build_system_context()`.
   - Prevent cross-session preference leakage.
4. **Step 3.4: Reconcile Agent Documentation**
   - Update `AGENTS.md` and `ARCHITECTURE.md` to accurately document the concrete tool modules and dispatch flow.

---

## 3. Milestones & Acceptance Criteria

| Milestone | Deliverables | Verification Metric |
|:---|:---|:---|
| **M1: UI Operability** | Frontend auth token injection, `ToolEvent` alias fix | User can chat, save settings, and confirm actions in UI under `JARVIS_ENV=development` with 0 console errors |
| **M2: Live DAG & Router** | `ModelRouter` and `TaskGraph` active in `orchestrator.py` | Coding prompts route to coding models; parallel tools execute concurrently |
| **M3: Multimodal & Vision** | Image upload in UI + Gemini vision adapter | User can upload screenshot and ask questions about it |
| **M4: Automated QA Shield**| Vitest frontend test suite + Authenticated E2E test | `npm test` and `pytest` both run and pass in CI |
