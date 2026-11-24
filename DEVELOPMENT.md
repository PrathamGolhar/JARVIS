# JARVIS Development

## Repository layout

```text
backend/
  app/api/                 FastAPI routers
  app/services/            Providers, orchestration, tools, memory, files, voice
  tests/                   Pytest tests
frontend/
  src/api/                 Typed backend clients
  src/components/          Chat, HUD, panels, and dialogs
  src/services/             Speech, permissions, and visual controller
  src/App.tsx               Frontend interaction and view state
```

`backend/app/main.py` registers API routers. `frontend/src/main.tsx` mounts the React application. See [ARCHITECTURE.md](ARCHITECTURE.md) for verified runtime boundaries.

## Local development

Install backend dependencies from the repository root:

```powershell
python -m pip install -r backend/requirements-dev.txt
Copy-Item backend/.env.example backend/.env
```

Set `JARVIS_API_KEY` and at least one cloud-provider key in `backend/.env` if you want authenticated cloud-backed operation. If no cloud provider is configured, chat may use the rule-based LocalProvider; it is not a general offline model.

Start the backend from `backend/`:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:1420`. The Vite proxy forwards `/api` to port `8765`.

## Adding a chat tool

1. Implement the handler and schema in `backend/app/services/tools/registry.py`.
2. Add or update the capability policy in `backend/app/services/permissions.py`.
3. Ensure permission checks and confirmation behavior are appropriate.
4. Add focused tests under `backend/tests/` for success, failure, and denial behavior.
5. Update [TOOLS.md](TOOLS.md) and [API.md](API.md) if the user-facing contract changes.

The plugin registry exists, but plugin tools are not currently integrated into chat execution. Do not treat registering a plugin as adding a callable chat tool.

## Validation commands

```powershell
python -m pytest backend/tests -v
cd frontend
npm test
npm run lint
npm run build
```

`npm run lint` is currently the TypeScript compiler check. See [TESTING.md](TESTING.md) for the automated validation scope.

## Interface

- `Ctrl+K` / `Cmd+K` opens the command palette.
- `Escape` closes the active dialog or drawer.
- The HUD globe and voice controls are UI features; they do not imply background listening or a general frontend-managed task DAG.
