# JARVIS — Architecture Gap Analysis

> **Historical snapshot:** This analysis records findings from its stated audit date. It is not a current implementation specification; verify claims against source and the canonical documentation.

**Audit Date:** 2026-11-23  
**Reference:** `ARCHITECTURE.md`, `AGENTS.md`, `TOOLS.md`

---

## 1. Documented vs. Actual Pipeline

The documentation claims:

```
LISTEN → UNDERSTAND → PLAN → EXECUTE → VERIFY → RESPOND
```

### Actual runtime trace for `/api/chat` POST:

```
1. LISTEN        ✅  Chat API receives text in ChatRequest
2. UNDERSTAND    ⚠️  PlanningEngine.detect_intent_and_plan() — keyword matching only, not AI-driven
3. PLAN          ⚠️  Returns static plan steps (pre-marked as completed before execution)
4. EXECUTE       ✅  execute_with_failover() → AI provider → tool calls → execute_tool_call()
5. VERIFY        ⚠️  output_verifier.verify_generated_file() only called for file generation
6. RESPOND       ✅  OrchestratorResponse assembled and returned
```

**Assessment:** The pipeline exists as a concept and partially as code, but stages 2, 3, and 5 are significantly under-implemented.

---

## 2. Component Implementation Status

| Component (Documented) | File | Status | Notes |
|---|---|---|---|
| **Orchestrator** | `services/orchestrator.py` | ✅ Implemented | Core loop functional |
| **ModelRouter** | `services/ai/router.py` | ❌ Disconnected | Never called in hot path |
| **TaskClassifier** | `services/ai/router.py` | ❌ Disconnected | Part of ModelRouter |
| **PlanningEngine** | `services/agents/planner.py` | ⚠️ Stub | Keyword-only, static steps |
| **TaskGraph** | `services/agents/task_graph.py` | ❌ Orphaned | No production caller |
| **ToolRegistry** | `services/tools/registry.py` | ✅ Implemented | Full dispatch table |
| **OutputVerifier** | `services/agents/verifier.py` | ⚠️ Partial | File-only verification |
| **EventBus** | `services/events/bus.py` | ❌ Orphaned | No subscribers |
| **Study Agent** | `services/agents/study_agent.py` | ✅ Implemented | Used by /api/study |
| **Document Agent** | `services/agents/document_agent.py` | ✅ Implemented | Used for PPTX |
| **Research Agent** | `services/research/researcher.py` | ✅ Implemented | Functional |
| **Coding Agent** | `services/coding/assistant.py` | ✅ Implemented | Used by /api/coding |
| **Verifier Agent** | `services/agents/verifier.py` | ⚠️ Minimal | Only checks file existence |
| **Math Agent** | (none) | ❌ Missing | Docs say exists; it doesn't |
| **Multi-Doc Agent** | (none) | ❌ Missing | Docs say exists; it doesn't |
| **Computer Agent** | (none) | ❌ Missing | Local actions serve this partially |
| **Memory Store** | `services/memory/persistent_memory.py` | ✅ Implemented | SQLite backed |
| **RAG Store** | `services/memory/vector_store.py` | ⚠️ Partial | In-memory only, BM25 |
| **EventBus** | `services/events/bus.py` | ❌ Orphaned | Infrastructure exists, unused |

---

## 3. ModelRouter Gap — Detailed

**What is documented:** An intelligent router that classifies tasks into categories (VISION, CODING, DEEP_REASONING, etc.) and selects the optimal provider per task type.

**What actually happens:**
```python
# orchestrator.py line 182
ai_res, active_provider = execute_with_failover(
    messages=messages,
    tools=TOOLS_SCHEMA,
    temperature=0.3,
    max_tokens=800,
)
```
`execute_with_failover()` in `factory.py` uses a simple cascade: Gemini → Groq → OpenAI → Anthropic → Local. The `ModelRouter.route()` and `TaskClassifier.classify()` methods in `router.py` are never called.

**Impact:** Vision tasks are not preferentially routed to Gemini. Simple conversations do not get Groq's low-latency advantage. All requests use the same `max_tokens=800` regardless of complexity.

**Correction path:**
```python
# In orchestrator.py, replace execute_with_failover() with:
from app.services.ai.router import ModelRouter
ai_res = ModelRouter.execute(
    messages=messages,
    tools=TOOLS_SCHEMA,
    has_images=has_uploaded_image,
)
```

---

## 4. TaskGraph Gap — Detailed

**What is documented:** A DAG that runs independent branches in parallel (e.g., research + PDF extraction + math in parallel).

**What actually exists:** A well-implemented `TaskGraph` class with `execute_all()`, `add_node()`, parallel execution via `asyncio.gather()`. The class works correctly in isolation.

**What is missing:** No code in the orchestrator, any agent, or any API route ever creates a `TaskGraph` or populates it with nodes. All tasks execute sequentially.

**Correction path:** For multi-step compound requests (research + generate doc), `run_orchestration()` should construct a `TaskGraph` and `await task_graph.execute_all()`.

---

## 5. PlanningEngine Gap — Detailed

**What is documented:** "Autonomous planning engine that classifies user intent, constructs discrete execution steps, and coordinates specialized sub-agents."

**What actually exists:**
- Pure keyword string matching (`if any(w in low for w in [...])`)
- Pre-built static step lists with **fixed statuses** (step 1 always "completed")
- No actual dependency on the AI provider
- Steps marked complete before anything runs

**What it should do:** Use the AI provider to decompose the user request into verifiable subtasks, then track their actual completion status.

---

## 6. EventBus Gap — Detailed

**What is documented:** "Decoupled publish/subscribe event messaging across agents, tools, speech, file monitors, and UI notifications."

**What actually exists:** A correct implementation with `publish()`, `subscribe()`, `unsubscribe()`, and event history. However:
- No code subscribes any handler in production
- `event_bus.publish()` is never called in `orchestrator.py`, `tools/registry.py`, or any API handler
- The bus exists but emits nothing and no one listens

**Correction path:** Add `await event_bus.publish(EventType.TASK_STARTED, {...})` in orchestrator; subscribe UI push notifications.

---

## 7. Permissions System Gap

**What is documented:** "Authoritative Capability, Permission, and Approved Action Registry" with `validate_tool_approval()`.

**What actually happens:**
```python
# registry.py execute_tool_call() — never calls permissions.py
def execute_tool_call(tool_name: str, raw_arguments: str | dict) -> dict:
    # Direct dispatch, no capability check
    if tool_name == "web_search":
        return live_web_search(...)
```

**Gap:** `permissions.py` is a complete, correct registry but is a dead code module from the execution path's perspective. Only the `/api/capabilities` route uses it for informational display.

---

## 8. Verification Gap

**What is documented:** "Every agent execution is governed by the verification loop... Verification Check → Self-Correction."

**What actually exists:**
```python
# Only called for generated files:
verified = output_verifier.verify_generated_file(settings.generated_dir / finfo.get("filename", ""))
if verified.get("verified"):
    generated_files.append(finfo)
```

`verify_tool_result()` exists but is never called. Web search results, code execution results, and AI responses have no verification step. There is no self-correction loop.

---

## 9. Architecture Recommendation

The architectural intent is excellent. The implementation gap is not due to poor design — it is due to the system being at an early phase where the infrastructure components (TaskGraph, EventBus, ModelRouter) exist but have not yet been wired into the main orchestration path.

**Priority wiring order:**
1. **ModelRouter** into orchestrator (immediate value: better routing, correct max_tokens)
2. **Sandbox isolation** (security critical)
3. **EventBus** into tool execution (enables real-time progress)
4. **TaskGraph** for compound requests (enables true parallelism)
5. **Capability Registry** enforcement at tool dispatch
6. **PlanningEngine** AI-driven upgrade (replace keyword matching)
