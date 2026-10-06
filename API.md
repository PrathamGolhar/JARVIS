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
    "projectId": "optional_project_id",
    "confirmedActionId": null
  }
  ```
- **Response**:
  ```json
  {
    "sessionId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "reply": "Master, I have analyzed your document and synthesized notes with 20 exam questions.",
    "mode": "study",
    "turnsRetained": 4,
    "citations": [],
    "toolEvents": [],
    "planSteps": [
      { "stepNumber": 1, "title": "Extract and understand academic material", "status": "completed" },
      { "stepNumber": 2, "title": "Generate practice questions & solution breakdown", "status": "completed" }
    ],
    "pendingAction": null,
    "generatedFiles": [
      {
        "id": "Notes.pdf",
        "filename": "Notes.pdf",
        "fileType": "pdf",
        "sizeBytes": 14200,
        "downloadUrl": "/api/files/download/Notes.pdf"
      }
    ]
  }
  ```

---

## 2. File Processing & Downloads

### `POST /api/files/upload`
Upload a document or image (`PDF`, `DOCX`, `PPTX`, `XLSX`, `CSV`, `JSON`, `TXT`, `Code`, `Image`).
- **Form Data**: `file: File`, `session_id: string (optional)`
- **Response**: `FileUploadResponse`

### `GET /api/files/generated`
List all generated files with timestamps and file sizes.

### `GET /api/files/download/{filename}`
Stream download of any uploaded or generated artifact.

### `DELETE /api/files/{filename}`
Delete a file from the workspace cache.

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
- **Request Body**: `{ "query": "Latest advances in solid state batteries", "depth": "deep", "generateDocument": "pdf" }`
- **Response**: `ResearchResponse` with summary, markdown findings, and verified citations.

---

## 6. Code Execution Sandbox

### `POST /api/code/execute`
- **Request Body**: `{ "code": "print('hello')", "language": "python", "timeoutSeconds": 10 }`
- **Response**: `{ "ok": true, "stdout": "hello\n", "stderr": "", "exitCode": 0, "executionTimeMs": 24.5 }`

### `POST /api/code/analyze`
- **Request Body**: `{ "code": "def foo(): ...", "language": "python", "task": "debug" }`
- **Response**: `CodeAnalysisResponse` with fixed code and unit tests.

---

## 7. Projects, Memory & Automation

- `GET /api/projects`, `POST /api/projects`, `POST /api/projects/{id}/tasks`
- `GET /api/memory`, `POST /api/memory`, `DELETE /api/memory/{key}`
- `GET /api/automation/reminders`, `POST /api/automation/reminders`
- `GET /api/settings`, `POST /api/settings`
- `GET /api/diagnostics`
