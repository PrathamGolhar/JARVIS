# Contributing to JARVIS

Thank you for your interest in contributing to JARVIS! This document provides guidelines and workflows for expanding capabilities, adding tools, and submitting pull requests.

---

## 1. Development Setup

### Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/your-repo/JARVIS.git
cd JARVIS

# 1. Backend Setup
cd backend
python -m venv .venv
# Activate virtual environment
source .venv/bin/activate  # Or on Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

# 2. Frontend Setup
cd ../frontend
npm ci
```

---

## 2. Coding Standards

- **Python (Backend)**:
  - Follow existing formatting and typing patterns.
  - Add focused tests in `backend/tests/` for new or changed behavior.
- **TypeScript & React (Frontend)**:
  - Clean functional components with React Hooks.
  - Strict type definitions (`interface` / `type`).
  - No `any` types unless strictly necessary for third-party library boundaries.
  - Maintain the sleek, futuristic JARVIS HUD aesthetic.

---

## 3. Adding a New Tool to JARVIS

To register a new capability:
1. Create a module in `app/services/tools/` (e.g., `app/services/tools/my_tool.py`).
2. Register the function and JSON schema in `app/services/tools/registry.py`.
3. Add or update its capability policy in `app/services/permissions.py`; there is no separate risk-level map.
4. Add focused success, error, and permission tests under `backend/tests/`.

---

## 4. Running Test Suites

### Backend Tests (pytest)
```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

### Frontend Type-Check & Build
```bash
cd frontend
npm test
npm run lint
npm run build
```

`npm run lint` is a TypeScript check, not an ESLint invocation. See [TESTING.md](TESTING.md) for the current commands.

---

## 5. Pull Request Process

1. Create a descriptive feature branch: `git checkout -b feature/new-document-generator`
2. Commit your changes with clear messages.
3. Ensure all tests pass.
4. Submit a Pull Request detailing the changes, motivation, and verification steps.
