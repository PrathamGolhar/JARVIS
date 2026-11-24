# JARVIS Frontend Architecture

The current frontend is a React 19, TypeScript, and Vite application in `frontend/`. It uses local React state and typed API modules; this document describes live source behavior rather than aspirational workspace or DAG features.

## Runtime shape

```text
frontend/src/main.tsx → App.tsx
                         ├── api/* → authenticated HTTP/JSON requests
                         ├── components/* → HUD, panels, dialogs, file drawer
                         └── services/* → speech, permissions, visual controller
                                      │
                                      ▼
                         FastAPI backend (default local API port 8765)
```

The Vite development server listens on port `1420` and proxies `/api` to the backend. `VITE_API_BASE_URL` can override the default `/api`. The default Docker build bundles the frontend into the backend image and serves it from port `8765`.

## Source layout

- `src/api/`: clients for chat, files, coding, generation, memory, projects, research, settings, speech, study, system, and reminders.
- `src/components/`: reusable UI, including `HolographicGlobe`, `AmbientHud`, chat, upload, and workspace panels.
- `src/services/`: `speechManager.ts`, `permissionManager.ts`, and `aiVisualController.ts`.
- `src/config/` and `src/styles/`: design tokens and global CSS.
- `src/App.tsx`: application state, view selection, chat submission, and interaction wiring.

The package scripts are defined by `frontend/package.json`. `npm run lint` is currently a TypeScript check, not ESLint. `@types/three` is a development/type dependency; `three` is the runtime package.

## Chat and file flow

`App.tsx` calls `sendChatMessage()` in `src/api/chat.ts`, which posts JSON to `/api/chat`. Responses are rendered with their execution status, tool events, citations, pending action, plan steps, and generated-file metadata. Requests are not streamed over SSE or WebSocket.

`FileUploadDrawer` uploads to `/api/files/upload`, then invokes a callback with a filename and extracted-text preview. The UI does not forward the returned `fileId` as `imageIds` in chat. The backend accepts image IDs through the API, but the current UI flow therefore does not provide image bytes to the model. Image upload itself does not run OCR or index image text.

## Voice and visuals

`speechManager.ts` owns browser speech recognition/microphone interactions and voice state. Audio can also be sent to the backend transcription endpoint, which currently uses Groq. `src/api/speech.ts` requests Edge TTS audio from `/api/tts`; browser speech synthesis can be used as a fallback by the UI. `aiVisualController.ts` coordinates visual state with audio, and `HolographicGlobe` supplies the Three.js HUD visualization.

The frontend does not contain a separate `speechRecognition.ts` service. Wake-word and background listening claims should be checked against the current `speechManager.ts` implementation and user interaction; do not describe the app as continuously listening by default.

## Current limitations

- `VITE_DEMO_MODE` is not read by the application; `DEMO_MODE` is hard-coded to `false`. Demo/mock behavior is not a supported startup mode.
- UI plan steps are display data returned by the API, not a frontend-managed dependency DAG.
- An image upload callback currently submits extracted text/preview as a prompt; it does not submit image IDs to the multimodal chat API.
