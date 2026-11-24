# JARVIS Architecture

This is the canonical, source-checked overview of the current implementation. For endpoint contracts, see [API.md](API.md); for storage details, see [DATABASE.md](DATABASE.md). Historical audits and roadmaps are not current implementation specifications.

## Runtime shape

```text
React/Vite frontend (frontend/)
        │ authenticated HTTP/JSON
        ▼
FastAPI application (backend/app/main.py)
        ├── Chat API → orchestrator
        │              ├── intent/mode planner
        │              ├── SQLite conversation and user memory
        │              ├── SQLite FTS5 document retrieval
        │              ├── ModelRouter → provider factory/failover
        │              └── registered chat tools
        │                    ├── capability policy and confirmation
        │                    └── execution → result/file verification
        ├── Separate APIs: files, research, coding, study, projects,
        │                  reminders, settings, speech, diagnostics
        └── SQLite stores + JSON project/reminder files
```

The browser uses REST requests, not a streaming tool-event connection. The chat response contains the final reply, status, tool events, citations, plan steps, and generated-file metadata.

## Chat request path

`POST /api/chat` validates session and principal ownership, then calls `run_orchestration_async`. The orchestrator detects intent/mode, searches document RAG and persistent memory, selects a provider with `ModelRouter`, and sends the assembled context to the provider. Chat tools are defined in `app/services/tools/registry.py`; permission decisions come from `app/services/permissions.py`. Pending actions require a session-bound confirmation before execution. Tool-backed work is reported with execution and verification status; a model response by itself is not proof that an external operation succeeded.

`TaskGraph` is used for batches of independent tool calls. The current planner supplies steps for display and routing; it does not construct a general dependency graph for complex plans. The `EventBus` publishes execution events and health diagnostics read its event history; there are no production event subscribers.

## Providers and offline behavior

The provider factory supports Gemini, Groq, OpenAI, Anthropic, and `LocalProvider`. `ModelRouter` selects providers based on the request, configured credentials, and required capabilities. Cloud failures may fall through to another eligible provider and ultimately to `LocalProvider`; authentication and quota failures are treated specially. `LocalProvider` is a deterministic rule-based fallback, not an offline general-purpose language model.

## Files, memory, and research

- Conversation/session records and user memories are stored in `jarvis_memory.db`.
- Document text chunks and an SQLite FTS5 full-text index are stored in `jarvis_documents.db`. Retrieval is lexical; it is not vector-embedding search.
- Projects and reminders are persisted as JSON files. See [DATABASE.md](DATABASE.md) for exact locations and limitations.
- Text-capable document uploads are extracted and indexed. Image uploads are stored, but the upload route does not OCR or index image text.
- The chat API accepts up to four uploaded image IDs for vision-capable providers. The current frontend upload flow does not pass those IDs into chat, so end-to-end image understanding is not available through that UI flow.
- Research uses web search and safe page retrieval. Citations link to search results; the system does not independently verify the truth of cited claims.

## Other implemented services and boundaries

- Document generation includes PDF, PPTX, DOCX, and XLSX.
- Study APIs provide notes and question generation; project and reminder APIs provide their own services.
- Voice capture uses browser speech support and/or the audio transcription API; backend transcription uses Groq, while TTS uses Edge TTS. The HUD includes a Three.js globe and visual/audio controls.
- Code execution uses an AST-restricted subprocess with a timeout, temporary working directory, output caps, and a scrubbed environment. It is not container or kernel isolation; configured memory/CPU values are diagnostic labels, not enforced resource limits.
- `MultiDocumentReasoner`, `VisionAnalyzer`, `OCRService`, `MathEngine`, and the plugin registry exist, but are not wired into the main chat tool execution path. The calculator is the registered chat math tool. The plugin registry is exposed by diagnostics/health, not used to supply chat tools.

## Deployment

The default Docker Compose service serves the built frontend and API on port `8765`. The optional `dev` profile runs Vite on port `1420`; a local Vite development server also proxies API requests to the backend. See [DEPLOYMENT.md](DEPLOYMENT.md).
