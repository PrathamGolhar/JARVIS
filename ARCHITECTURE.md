# JARVIS Architecture & Technical Blueprint

This document details the system design, agent orchestration, data flow pipelines, and security boundaries of the JARVIS personal AI assistant.

---

## 1. High-Level Architecture Diagram

```text
                                  +---------------------------------------+
                                  |         JARVIS HUD FRONTEND           |
                                  |    (React 19 + TypeScript + Vite)     |
                                  +---------------------------------------+
                                           |                     |
                                    REST / JSON            Audio Streaming (Edge-TTS)
                                           |                     |
                                           v                     v
+-----------------------------------------------------------------------------------------------------+
|                                          FASTAPI BACKEND CORE                                       |
|                                                                                                     |
|  +-----------------------+     +------------------------+     +----------------------------------+  |
|  |     INTENT PLANNER    | --> |    ORCHESTRATOR & AGENTS| --> |      VERIFICATION SYSTEM         |  |
|  | (Detect & Multi-Step) |     |  (Study, Research, Code)|     | (Integrity, Output Validation)   |  |
|  +-----------------------+     +------------------------+     +----------------------------------+  |
|              |                              |                                   |                   |
|              v                              v                                   v                   |
|  +-----------------------+     +------------------------+     +----------------------------------+  |
|  |  MULTI-PROVIDER AI    |     |      TOOL REGISTRY     |     |       DOCUMENT GENERATORS        |  |
|  | Gemini / Groq / OpenAI|     | Web, Calc, Sandbox, DB |     |   PDF / PPTX / DOCX / XLSX       |  |
|  +-----------------------+     +------------------------+     +----------------------------------+  |
|              |                              |                                   |                   |
|              v                              v                                   v                   |
|  +-----------------------+     +------------------------+     +----------------------------------+  |
|  |   2-LEVEL MEMORY      |     |  LOCAL SANDBOX ENGINE  |     |      UNIVERSAL EXTRACTOR         |  |
|  | SQLite Sessions & RAG |     | Isolated Python Runtime|     | PDF, OCR, Office, Code, Vision   |  |
|  +-----------------------+     +------------------------+     +----------------------------------+  |
+-----------------------------------------------------------------------------------------------------+
```

---

## 2. Operational Pipeline

Every command processed by JARVIS follows the strict 6-stage lifecycle:

```text
[ LISTEN ]     Capture speech via Web Speech API or microphone audio upload.
    │
    ▼
[ UNDERSTAND ] Extract textual intent, user preferences, temporal context, and active project state.
    │
    ▼
[ PLAN ]       Construct a discrete step-by-step ExecutionPlan with required sub-agents & tools.
    │
    ▼
[ EXECUTE ]    Invoke model and execute registered tools (web search, math, file analysis, sandbox).
    │
    ▼
[ VERIFY ]     Validate file existence, non-zero byte size, syntax accuracy, and calculation correctness.
    │
    ▼
[ RESPOND ]    Stream neural voice response and deliver interactive widgets & downloadable artifacts.
```

---

## 3. Subsystem Breakdown

### 3.1 AI Provider Abstraction (`app/services/ai/`)
- Unified interface `AIProvider` with methods `chat()` and `is_available()`.
- Implementations for **Google Gemini (`GeminiProvider`)**, **Groq (`GroqProvider`)**, **OpenAI (`OpenAIProvider`)**, and **Offline Local (`LocalProvider`)**.
- Provider factory with automatic fallback resolution.

### 3.2 Document Generation Engine (`app/services/document_generation/`)
- **PDF**: Built with `reportlab` featuring cover pages, headers, footers, code blocks, and tables.
- **PowerPoint**: Built with `python-pptx` supporting 16:9 widescreen slides, custom color themes (`cyan`, `gold`, `emerald`, `crimson`, `purple`), bullet cards, and speaker notes.
- **Word**: Built with `python-docx` supporting formatted headings, metadata headers, and XML code shading.
- **Excel**: Built with `openpyxl` supporting styled fills, header grids, auto-column sizing, and dynamic `SUM` formulas.

### 3.3 Study & Academic Engine (`app/services/study_mode/`)
- In-depth structured notes generator with definitions, mathematical laws, formulas, and derivations.
- Interactive MCQ exam generator with 4 difficulty tiers (`Easy`, `Medium`, `Hard`, `Exam Level`), hints, solutions, and step-by-step rationale.
- Interactive flashcards.

### 3.4 Deep Research Engine (`app/services/research/`)
- Multi-query search via DuckDuckGo.
- Top webpage extraction with `BeautifulSoup`.
- Grounded intelligence synthesis with full domain citations.

### 3.5 Code Sandbox (`app/services/coding/`)
- Isolated subprocess execution with strict timeouts (`JARVIS_SANDBOX_TIMEOUT`).
- Output buffering and memory safety checks.
- Code explanation, debugging, and automated unit test generation.

### 3.6 Memory & Semantic Search (`app/services/memory/`)
- **Short-Term Memory**: Conversation session turns stored in SQLite `messages`.
- **Long-Term Memory**: Categorized user preferences and facts stored in SQLite `memories`.
- **Local RAG Vector Store**: Document chunking (sliding window with overlap) and BM25 term matching.
