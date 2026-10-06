# JARVIS 2.0 Testing Methodology & Evaluation Benchmarks

This document outlines testing standards, automated test suites, end-to-end evaluation workflows, and verification requirements for JARVIS 2.0.

---

## 1. Test Architecture

JARVIS 2.0 maintains a dual-layer test suite:
1. **Backend Integration & Unit Tests (Pytest)**: Located in `AI/Backend/DR-doom-Day-2-Backend/tests/`
2. **Frontend Type & Build Validation (TypeScript + Vite)**: Located in `jarvis-frontend/`

---

## 2. Backend Test Suites

| Test Module | Coverage Area |
| :--- | :--- |
| `test_jarvis2_core.py` | ModelRouter, TaskClassifier, TaskGraph DAG, EventBus, MathEngine, MultiDoc Reasoner, PluginRegistry, Health Probes |
| `test_agents_and_planner.py` | Multi-step intent planner, sub-agent decomposition, output integrity verifier |
| `test_document_generation.py`| ReportLab PDF creation, python-pptx 16:9 widescreen decks, python-docx reports, openpyxl workbooks |
| `test_code_sandbox.py` | Isolated Python subprocess execution, timeout guards, memory buffer overflow prevention |
| `test_study_mode.py` | Structured study notes synthesis, definitions, mathematical formula derivations, 4-tier MCQs |
| `test_tools.py` | Tool registry, calculator AST evaluations, workspace confinement, SSRF prevention |
| `test_local_actions.py` | Host bridge application allowlists, confirmation security constraints, CORS origin validation |
| `test_speech.py` | Web Speech transcription codecs, Edge-TTS audio stream endpoints, curated neural voice catalog |
| `test_files.py` | Universal file upload, MIME detection, text extraction, empty file validation |
| `test_projects_and_memory.py`| SQLite persistent memory key/value store, project creation, task management |

### Running the Test Suite:
```bash
cd AI/Backend/DR-doom-Day-2-Backend
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
