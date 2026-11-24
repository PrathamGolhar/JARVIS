# JARVIS REST API Specification

Comprehensive documentation for all endpoints exposed by the FastAPI backend on port `8765`.

---

## 1. Chat & Orchestration

### `POST /api/chat`
Send conversational or complex goal instructions.
- **Request Body**:
  ```json
  {
    "sessionId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "text": "JARVIS, scan my electronics PDF and generate 20 exam questions with formulas.",
    "mode": "study",
    "responseStyle": "balanced",
    "projectId": "optional_project_id",
    "confirmedActionId": null,
    "imageIds": [],
    "providerOverride": "auto",
    "idempotencyKey": "unique-key-for-this-user-request"
  }
  ```
- **Response**:
  ```json
  {
    "sessionId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "reply": "<assistant response text>",
    "mode": "study",
    "executionStatus": "unverified",
    "verification": {
      "status": "unverified",
      "incomplete": []
    },
    "turnsRetained": 0,
    "citations": [],
    "toolEvents": [],
    "planSteps": [],
    "pendingAction": null,
    "generatedFiles": []
  }
  ```
- `providerOverride` can select `auto`, `gemini`, `groq`, `openai`, `anthropic`, or `local`; provider failover remains enabled for cloud providers.
- `responseStyle` accepts `concise`, `balanced`, or `detailed`; the default is `balanced`. JARVIS responds in English with a calm, professional, natural tone.
- `imageIds` accepts up to four image file IDs returned by `POST /api/files/upload`. The request routes only to vision-capable providers. Upload does not OCR or index images, and the current frontend upload flow does not pass image IDs to chat; this capability is currently available only to API clients that supply `imageIds`.
- `idempotencyKey` (or the `Idempotency-Key` header) makes retries of the same session request return the original result without repeating tool side effects. Reusing the key for different request content returns `409`.
- `executionStatus` distinguishes `success`, `partial_success`, `failure`, and `unverified`; a model response alone does not mark tool-backed work successful.

---

## 2. File Processing & Downloads

### `POST /api/files/upload`
Upload a supported document, code file, or image (`PDF`, `DOCX`, `PPTX`, `XLSX`, `CSV`, `JSON`, `TXT`, supported code extensions, `PNG`, `JPG`, `WEBP`).
- **Form Data**: `file: File`, `session_id: string (optional)`, `project_id: string (optional)`
- Uploaded documents are scoped to the authenticated principal and, when provided, its session/project.
- Text-capable uploads may be extracted and indexed. Images are stored, but the upload route explicitly does not OCR or index them.
- **Response**: `FileUploadResponse`

### `GET /api/files/generated`
List all generated files with timestamps and file sizes.

### `GET /api/files/download/{filename}`
Stream download of any uploaded or generated artifact.

### `DELETE /api/files/{filename}`
Delete a file from the workspace cache.

### Conversation sessions
- `POST /api/sessions` with `{ "sessionId": "<uuid>" }` binds a client-generated ID to the authenticated principal.
- `GET /api/sessions` lists that principal's session metadata.
- `GET /api/sessions/{sessionId}/history` restores conversation history after reload.
- `POST /api/sessions/{sessionId}/reset` clears history but keeps the session.
- `DELETE /api/sessions/{sessionId}` removes the session history and its session-scoped uploads/artifacts.
- A client-supplied ID is never authorization: each request verifies the server-side owner binding.

---

## 3. Document Generation

### `POST /api/generate/pdf`
- **Request Body**: `{ "title": "Title", "contentMarkdown": "Markdown...", "subtitle": "" }`
- **Response**: `{ "ok": true, "filename": "report.pdf", "downloadUrl": "..." }`

### `POST /api/generate/pptx`
- **Request Body**: `{ "topic": "Quantum Computing", "numSlides": 8, "themeColor": "cyan" }`
- **Response**: `{ "ok": true, "file": { "filename": "presentation.pptx", "downloadUrl": "..." } }`

### `POST /api/generate/docx`
- **Request Body**: `{ "title": "Report", "contentMarkdown": "..." }`

### `POST /api/generate/xlsx`
- **Request Body**: `{ "filename": "data.xlsx", "headers": ["A", "B"], "rows": [[1, 2]] }`

---

## 4. Study Mode & Academics

### `POST /api/study/notes`
- **Request Body**: `{ "topicOrText": "Material...", "subject": "Physics", "formatOutput": "pdf" }`
- **Response**: `StudyNotesResponse` (definitions, formulas, notes, MCQs, flashcards).

### `POST /api/study/mcqs`
- **Query Params**: `topic_or_text: string`, `count: int`, `difficulty: string`
- **Response**: Array of `MCQItem`.

---

## 5. Deep Web Research

### `POST /api/research/deep`
- **Request Body**: `{ "query": "Latest advances in solid state batteries", "depth": "deep", "generate_document": "pdf" }`
- **Response**: `ResearchResponse` includes `status` (`success`, `partial_success`, `failure`, or `unverified`), `synthesisStatus` (`success`, `failure`, or `not_attempted`), `sourceStatus` (`none`, `search_results`, or `page_content_retrieved`), and `documentStatus` (`not_requested`, `generated`, `not_generated`, or `unsupported`).
- Citation links originate from search results. Retrieved page content is reported separately and is not an independent fact-check; citations must not be described as verified sources.
- PDF export is supported. A requested unsupported document format is returned as `partial_success` with `documentStatus: "unsupported"` and no download URL.

---

## 6. Code Execution Sandbox

### `POST /api/code/execute`
- **Request Body**: `{ "code": "print('hello')", "language": "python", "timeoutSeconds": 10 }`
- **Response**: `{ "ok": true, "stdout": "hello\n", "stderr": "", "exitCode": 0, "executionTimeMs": 24.5 }`

### `POST /api/code/analyze`
- **Request Body**: `{ "code": "def foo(): ...", "language": "python", "task": "debug" }`
- **Response**: `CodeAnalysisResponse` on successful analysis. Provider errors or incomplete output return an error; no placeholder analysis or test result is generated.

---

## 7. Projects, Memory & Automation

- `GET /api/projects`, `POST /api/projects`, `POST /api/projects/{id}/tasks`
- `GET /api/memory`, `POST /api/memory`, `DELETE /api/memory/{key}`
- Projects, memories, uploaded documents, and generated artifacts are filtered by the authenticated principal.
- Memory entries include provenance and source metadata. `POST /api/memory` reports whether a conflicting prior value was replaced.
- Conversation history is session-scoped; long-term preferences are principal-scoped; project notes/tasks remain project-scoped; uploaded content is retrieved only from the same owner's session/project or personal scope.
- `GET /api/automation/reminders`, `POST /api/automation/reminders`
- `GET /api/settings`, `POST /api/settings`
- `GET /api/diagnostics`
