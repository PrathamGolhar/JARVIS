# JARVIS 2.0 — PRIORITIZED ACTIONABLE BACKLOG

**Audit Date:** November 24, 2026
**Auditor:** Principal Software Architect & Release Engineer

---

## Priority Scale & Criteria
- 🔴 **P0 (Critical / Blocker)**: Complete denial of service for end users, security bypass, or runtime crash.
- 🟠 **P1 (High Priority)**: Core architectural disconnect, dead code in runtime path, or missing major documented capability.
- 🟡 **P2 (Medium Priority)**: Subsystem isolation gap, missing auth on secondary routes, or documentation divergence.
- 🟢 **P3 (Low Priority / Polish)**: Performance optimization, cosmetic improvements, or optional extensions.

---

## 1. 🔴 P0 — Critical Action Items

### P0-01: Implement Frontend Authentication Handshake & Token Injection
- **Issue**: Backend requires API key/bearer token in dev/prod (`auth_enabled=True`), but frontend sends zero auth headers. 100% of frontend requests fail with 401.
- **Action**:
  1. Add a centralized `apiClient` fetch wrapper in `jarvis-frontend/src/api/client.ts`.
  2. Implement session negotiation on app mount: exchange configured API key or local token via `POST /api/auth/token`.
  3. Store session token in memory / `sessionStorage` and inject `Authorization: Bearer <token>` on all outbound requests.
  4. Provide a Settings UI input to allow entering or updating the Master API key.

### P0-02: Fix `ToolEvent` Schema Field Alias Mismatch Crashing Confirmed Actions
- **Issue**: `orchestrator.py` produces `{"tool_name": "confirmed_action", ...}`, while `schemas.py` defines `ToolEvent.tool_name` with `alias="toolName"` and lacks `populate_by_name=True`. Causes HTTP 500 on all confirmed action completions.
- **Action**:
  1. Add `model_config = ConfigDict(populate_by_name=True)` to `ToolEvent`, `PendingAction`, `PlanStep`, and `ChatResponse` in `backend/app/schemas.py`.
  2. Change dictionary key to `"toolName"` in `backend/app/services/orchestrator.py` (lines 117 & 296).

---

## 2. 🟠 P1 — High Priority Action Items

### P1-01: Wire `ModelRouter` into Live Chat Orchestration Path
- **Issue**: `ModelRouter` and `TaskClassifier` are implemented in `router.py`, but never invoked in `run_orchestration()`.
- **Action**:
  1. Import `model_router` in `backend/app/services/orchestrator.py`.
  2. Classify task category and call `model_router.route(user_text, active_mode=mode)`.
  3. Pass the resolved provider and model tier into `execute_with_failover()`.

### P1-02: Connect Multi-Step Execution Plans to `TaskGraph` DAG Engine
- **Issue**: `TaskGraph` exists with cycle detection and semaphore concurrency, but orchestrator uses a sequential while-loop.
- **Action**:
  1. For multi-step plans (`plan.requires_tools`), construct a `TaskGraph` instance from plan steps or parallel LLM tool calls.
  2. Execute independent tools concurrently via `task_graph.execute()`.
  3. Map DAG execution results into `ChatResponse.toolEvents` and `ChatResponse.planSteps`.

### P1-03: Implement Genuine Multimodal & Vision Understanding
- **Issue**: Zero image handling exists in backend schemas, AI provider adapters, or frontend UI.
- **Action**:
  1. Add optional `images: list[str] = Field(default_factory=list)` (base64 data URIs) to `ChatRequest` in `schemas.py`.
  2. Update `GeminiProvider.chat()` and `OpenAIProvider.chat()` to format inline image data blocks.
  3. Add an image upload button and preview thumbnail in `jarvis-frontend/src/App.tsx`.

### P1-04: Install & Configure Frontend Test Infrastructure
- **Issue**: 0 automated tests exist for the React frontend application.
- **Action**:
  1. Install `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, and `jsdom` in `jarvis-frontend`.
  2. Add `npm test` script to `package.json`.
  3. Implement automated test suites for API client error handling, auth injection, and confirmation modal rendering.

---

## 3. 🟡 P2 — Medium Priority Action Items

### P2-01: Attach Authentication Dependency to Speech API Router
- **Issue**: `/api/tts` and `/api/transcribe` in `backend/app/api/speech.py` lack `require_auth`, allowing unauthenticated quota draining.
- **Action**: Add `dependencies=[Depends(require_auth)]` to `backend/app/api/speech.py`.

### P2-02: Scope Global User Preferences by Session/User
- **Issue**: `memory_store.build_system_context()` injects all preferences into all sessions globally.
- **Action**: Update `build_system_context(session_id=None)` and SQLite queries in `persistent_memory.py` to filter preferences by session or user.

### P2-03: Reconcile Documented `EventBus` and Specialized Agent Classes
- **Issue**: `EventBus` is documented but non-existent. Agents (`study_agent`, `document_agent`) are bypassed by the orchestrator.
- **Action**:
  1. Implement lightweight pub/sub `EventBus` in `services/events/bus.py` or update documentation to remove misleading references.
  2. Route study and document chat intents directly to `study_agent` and `document_agent`.

### P2-04: Add Authenticated End-to-End Test in CI Test Suite
- **Issue**: Conftest disables auth globally, masking frontend/backend integration issues.
- **Action**: Add a dedicated integration test suite running with `settings.auth_enabled = True` verifying the complete login, token exchange, and chat flow.

---

## 4. 🟢 P3 — Low Priority / Polish

### P3-01: Optional ONNX Local Embeddings for Hybrid RAG
- **Issue**: FTS5 and Okapi BM25 provide strong keyword search; dense vector embeddings would enable semantic synonym matching for environments with GPUs.
- **Action**: Add an opt-in ONNX runtime plugin in `services/memory/embeddings.py`.

### P3-02: Desktop & Web Push Notifications for Scheduled Reminders
- **Issue**: Reminders log to SQLite and server console, but lack OS desktop toasts.
- **Action**: Implement Windows toast notifications via `plyer` or Web Notifications API in the frontend.
