# JARVIS 2.0 — Advanced Autonomous Personal AI Operating Assistant

An elite, production-grade, multi-model AI personal operating assistant inspired by the capabilities and futuristic interface of JARVIS.

Designed for natural voice and multimodal interaction, intelligent model routing, DAG task graph dependency execution, publication document synthesis, deep web research with authentic citations, safe code sandboxing, symbolic calculus/mathematics evaluation, multi-document comparative reasoning, extensible plugins, academic study mode with interactive quizzes, and contextual project management.

---

## 🌟 Core Capabilities & Systems

- **6-Stage Operational Pipeline**: `LISTEN → UNDERSTAND → PLAN → EXECUTE → VERIFY → RESPOND`.
- **Intelligent Model Router (`ModelRouter`)**: Dynamically routes requests across **Google Gemini (multimodal & vision)**, **Groq (ultra-low latency)**, **OpenAI (GPT reasoning)**, **Anthropic**, and an offline **Local Rule Engine** with automatic fallback and user manual override.
- **Task Graph (DAG) Dependency Engine (`TaskGraph`)**: Decomposes complex instructions into directed dependency graphs, executing parallel subtasks concurrently with automatic failure recovery.
- **Asynchronous Event Bus (`EventBus`)**: Decoupled pub/sub event framework across agents, tools, speech, file monitors, and UI notifications.
- **Multimodal Document & Image Analysis**: Universal parsing for `PDF`, `DOCX`, `PPTX`, `XLSX`, `CSV`, `JSON`, code files, and image/circuit diagram OCR.
- **Multi-Document Reasoning Agent**: Comparative cross-file synthesis detecting commonalities, divergence, and generating grounded comparison matrices across multiple documents.
- **Symbolic Mathematics & Computation Engine (`MathEngine`)**: Step-by-step calculus (derivatives, integrals), linear algebra (matrix determinants, inverse), descriptive statistics (mean, median, variance, standard deviation), and physical formulas.
- **Extensible Plugin SDK (`JARVISPlugin`)**: Standardized plugin interface with explicit permission scopes (`READ`, `WRITE`, `DELETE`, `EXTERNAL_NETWORK`, `SYSTEM_COMMAND`, `FINANCIAL`) and tool registration.
- **Publication Document Generation Engine**:
  - **PDF Reports**: Styled headers, tables, code formatting, and page numbers via ReportLab.
  - **PowerPoint Presentations**: Modern widescreen 16:9 decks with speaker notes via python-pptx.
  - **Word Documents**: Formatted `.docx` files with headers, footers, and code shading.
  - **Excel Spreadsheets**: Formatted `.xlsx` workbooks with formula sums and auto-width columns.
- **Dedicated Academic Study Mode**:
  - Structured detailed notes (definitions, laws, formulas with derivations, examples).
  - Interactive exam preparation quiz (Easy, Medium, Hard, Exam Level) with hints, solutions, and explanations.
  - Interactive flashcards.
- **Deep Web Research**: Multi-source DuckDuckGo live search, webpage scraping, and grounded reports with authentic citations.
- **Coding Assistant & Sandbox**: Code debugging, refactoring, test suite generation, and isolated Python sandbox execution with CPU/memory limits.
- **Contextual Project Management**: Track tasks, milestones, linked documents, and project-specific memory.
- **Two-Level Memory & RAG**: Short-term session memory + SQLite persistent key/value facts + local BM25/vector chunk retrieval.
- **Voice System**: Web Speech STT + Edge-TTS neural speech streaming with instant Barge-In support and optional wake word (`"JARVIS"`).
- **HUD Command Palette (`Ctrl+K`)**: Rapid keyboard-driven search and execution across all JARVIS tools, models, and document generators.
- **Safety Tiers**: `READ ONLY`, `ASSISTED` (with interactive action confirmation modals), and `FULL CONTROL`.

---

## 🚀 Quick Start

### Prerequisites
- **Python**: 3.11+
- **Node.js**: 18+ and npm

### 1. Launch with One Click (Windows PowerShell)
```powershell
.\start-dev.ps1
```

### 2. Launch with One Click (Linux / macOS)
```bash
chmod +x ./start-dev.sh
./start-dev.sh
```

### 3. Launch via Docker Compose
```bash
docker compose up --build
```

Access the JARVIS HUD interface at **`http://localhost:5173`** and the API at **`http://127.0.0.1:8765`**.

---

## 🧪 Testing & Verification

Run the full backend test suite (56 tests across 15 modules):
```bash
cd AI/Backend/DR-doom-Day-2-Backend
python -m pytest -v
```

Run frontend build validation:
```bash
cd jarvis-frontend
npm run build
```

---

## 📜 Documentation Suite

- [Architecture Blueprint (ARCHITECTURE.md)](ARCHITECTURE.md)
- [REST API Reference (API.md)](API.md)
- [Database Schema & Models (DATABASE.md)](DATABASE.md)
- [Multi-Agent System & DAG Orchestration (AGENTS.md)](AGENTS.md)
- [Tool Registry & Risk Tiers (TOOLS.md)](TOOLS.md)
- [Setup & Installation Guide (SETUP.md)](SETUP.md)
- [Production Deployment & Docker (DEPLOYMENT.md)](DEPLOYMENT.md)
- [Developer & Plugin SDK Guide (DEVELOPMENT.md)](DEVELOPMENT.md)
- [Testing & Benchmark Methodology (TESTING.md)](TESTING.md)
- [Security & Threat Model (SECURITY.md)](SECURITY.md)
- [Troubleshooting & Diagnostics (TROUBLESHOOTING.md)](TROUBLESHOOTING.md)
- [Contributing Guidelines (CONTRIBUTING.md)](CONTRIBUTING.md)
