# JARVIS Backend

The backend is a FastAPI application under `backend/app/`. It exposes chat, files, research, coding, study, project, memory, reminder, settings, speech, diagnostics, and local-action APIs. Current routes and request models are documented in the root [API.md](../API.md).

## Setup

Python 3.11 is used by CI. From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
```

Set `JARVIS_API_KEY` and any provider keys in `backend/.env`. Without cloud provider credentials, `LocalProvider` is available as a rule-based fallback, not a general language model.

Run the API from `backend/`:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

The API health endpoint is `http://127.0.0.1:8765/api/health`. `run-dev.ps1` provides the local Windows launcher.

## Tests

Install the test dependencies and runtime dependencies with:

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

The backend does not use a PostgreSQL ORM schema. Persistent stores and current limitations are described in [DATABASE.md](../DATABASE.md).
