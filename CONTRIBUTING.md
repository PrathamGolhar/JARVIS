# Contributing to JARVIS

Thank you for your interest in contributing to JARVIS! This document provides guidelines and workflows for expanding capabilities, adding tools, and submitting pull requests.

---

## 1. Development Setup

### Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/your-repo/JARVIS.git
cd JARVIS

# 1. Backend Setup
cd AI/Backend/DR-doom-Day-2-Backend
python -m venv .venv
# Activate virtual environment
source .venv/bin/activate  # Or on Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Frontend Setup
cd ../../../jarvis-frontend
npm install
```

---

## 2. Coding Standards

- **Python (Backend)**:
  - Format with `black` and `isort`.
  - Enforce type hints on all public functions and service methods.
  - Write test cases in `tests/` for any new tool, agent, or document generator.
- **TypeScript & React (Frontend)**:
  - Clean functional components with React Hooks.
  - Strict type definitions (`interface` / `type`).
  - No `any` types unless strictly necessary for third-party library boundaries.
  - Maintain the sleek, futuristic JARVIS HUD aesthetic.

---

## 3. Adding a New Tool to JARVIS

To register a new capability:
1. Create a module in `app/services/tools/` (e.g., `app/services/tools/my_tool.py`).
2. Register the tool function in `app/services/tools/registry.py` with its JSON schema and execution handler.
3. Categorize its safety risk (`is_high_impact_tool`).
4. Add a unit test in `tests/test_tools.py`.

---

## 4. Running Test Suites

### Backend Tests (pytest)
```bash
cd AI/Backend/DR-doom-Day-2-Backend
python -m pytest -v
```

### Frontend Type-Check & Build
```bash
cd jarvis-frontend
npm run build
```

---

## 5. Pull Request Process

1. Create a descriptive feature branch: `git checkout -b feature/new-document-generator`
2. Commit your changes with clear messages.
3. Ensure all tests pass.
4. Submit a Pull Request detailing the changes, motivation, and verification steps.
