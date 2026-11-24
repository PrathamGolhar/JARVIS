# JARVIS

JARVIS is a personal AI assistant with a React/Vite interface and a FastAPI backend. This README describes capabilities verified in the current source; aspirational or disconnected modules are called out explicitly rather than presented as working features.

---

## Current capabilities and boundaries

- **Chat and provider routing:** `ModelRouter` and provider adapters support Gemini, Groq, OpenAI, Anthropic, and a rule-based `LocalProvider` fallback. The local provider is not a general-purpose offline language model.
- **Tools and permissions:** Chat tools are dispatched through one registry and checked against the capability policy. Actions can be denied or require explicit confirmation according to permission mode.
- **Memory and documents:** Session history and user memories use SQLite. Text-extractable uploads are stored and searchable through SQLite FTS5 lexical retrieval; this is not vector search.
- **Research:** Search and page retrieval are available, but citations are links from search results and are not independently verified evidence.
- **Files and generation:** Text document extraction and PDF, PPTX, DOCX, and XLSX generation are available through backend services.
- **Study, projects, reminders, coding, and voice:** These have dedicated API/service implementations. Code execution uses a restricted subprocess, not container isolation. Speech uses browser capture, Groq transcription, and Edge TTS.
- **Interface:** The `frontend/` application includes the holographic Three.js globe, HUD panels, chat, and voice controls.

Not currently integrated into the main chat path: plugin tools, `MultiDocumentReasoner`, `VisionAnalyzer`, `OCRService`, and `MathEngine`. Image IDs are accepted by the backend chat API, but the current frontend upload flow does not send them; image uploads are not OCR'd or indexed. See [ARCHITECTURE.md](ARCHITECTURE.md) for verified integration boundaries.

---

## 🚀 Quick Start

### Prerequisites
- **Python**: 3.11+
- **Node.js**: 20+ and npm

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

With default `docker compose up --build`, open the bundled UI/API at **`http://localhost:8765`**. The optional `docker compose --profile dev up --build` profile runs the Vite UI at **`http://localhost:1420`**; the API remains on port `8765`.

---

## 🧪 Testing & Verification

Run the backend test suite:
```powershell
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -v
```

Run frontend tests, TypeScript validation, and build validation:
```bash
npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```

---

## 📜 Documentation Suite

- [Architecture Blueprint (ARCHITECTURE.md)](ARCHITECTURE.md)
- [REST API Reference (API.md)](API.md)
- [Database Schema & Models (DATABASE.md)](DATABASE.md)
- [Engineering Instructions (AGENTS.md)](AGENTS.md)
- [Chat Tool Inventory & Permissions (TOOLS.md)](TOOLS.md)
- [Setup & Installation Guide (SETUP.md)](SETUP.md)
- [Production Deployment & Docker (DEPLOYMENT.md)](DEPLOYMENT.md)
- [Developer & Plugin SDK Guide (DEVELOPMENT.md)](DEVELOPMENT.md)
- [Testing Commands (TESTING.md)](TESTING.md)
- [Security & Threat Model (SECURITY.md)](SECURITY.md)
- [Troubleshooting & Diagnostics (TROUBLESHOOTING.md)](TROUBLESHOOTING.md)
- [Contributing Guidelines (CONTRIBUTING.md)](CONTRIBUTING.md)

Audit reports, test totals, and roadmaps elsewhere in the repository are historical snapshots, not current-state documentation.
# JARVIS
