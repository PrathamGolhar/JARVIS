# JARVIS Frontend

The current frontend is a React 19, TypeScript, and Vite application. It provides the JARVIS HUD, chat, workspace panels, voice controls, file upload UI, and Three.js globe.

## Prerequisites and startup

- Node.js 20 or newer
- The FastAPI backend at `http://127.0.0.1:8765`

From `frontend/`:

```powershell
npm ci
npm run dev
```

Open `http://localhost:1420`. The Vite server proxies `/api` to the backend. `VITE_API_BASE_URL` can override the default API base.

## Runtime integration limits

- The application has no working standalone demo mode. `DEMO_MODE` is hard-coded to `false`; `VITE_DEMO_MODE` in older setup guidance is ignored.
- The chat client supports an `imageIds` field, but the current upload UI does not forward the upload response's image ID to chat. Image upload does not provide OCR or searchable text.
- Voice capture is user-initiated. Backend transcription currently uses Groq; backend speech synthesis uses Edge TTS, with browser speech synthesis available as a UI fallback.
- The backend response includes plan steps and tool events, but the frontend does not execute a task DAG or stream tool events.

See the root [FRONTEND_ARCHITECTURE.md](../FRONTEND_ARCHITECTURE.md) for the current client/API flow.

## Scripts

```powershell
npm run dev      # Start Vite
npm test         # Run Vitest
npm run lint     # Run TypeScript project check (not ESLint)
npm run build    # TypeScript check and Vite production build
npm run preview  # Preview the built frontend
```
