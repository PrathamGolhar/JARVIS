# JARVIS Chat Tools

This page describes the tools exposed to the chat model by `backend/app/services/tools/registry.py`. That file is authoritative for JSON schemas and handlers. API endpoints outside the chat registry provide additional functionality and are documented in [API.md](API.md).

## Authorization

Tool impact and permission requirements come from the capability policy in `backend/app/services/permissions.py`; there is no separate risk-level registry. The registry validates tool names and arguments, and execution re-checks permission before invoking a handler. Depending on the active permission mode and capability, an operation may be denied or require explicit confirmation. Unknown tools fail closed.

## Registered chat tools

| Tool | Required arguments | Purpose |
| --- | --- | --- |
| `web_search` | `query` | Search the web; search results are not independently fact-checked. |
| `read_webpage` | `url` | Retrieve and extract text from a safe HTTP(S) page. |
| `calculator` | `expression` | Evaluate supported arithmetic and mathematical expressions. |
| `get_weather` | `location` | Request current weather information. |
| `system_diagnostics` | None | Read available system diagnostics. |
| `search_files` | `pattern` | Search within the authorized workspace. |
| `read_file` | `file_path` | Read a supported workspace file. |
| `write_file` | `file_path`, `content` | Write a workspace file, subject to permission policy. |
| `open_application` | `app_id` | Request an allowlisted local application action. |
| `generate_presentation` | `topic` | Generate a PPTX presentation; `theme_color` is optional. |
| `generate_pdf_report` | `title`, `content_markdown` | Generate a PDF; `subtitle` is optional. |
| `execute_python_code` | `code` | Run code through the restricted subprocess service. |
| `set_user_preference` | `key`, `value` | Store an owner-scoped memory entry. |
| `generate_word_doc` | `title`, `content_markdown` | Generate a DOCX; `subtitle` and `author` are optional. |
| `deep_web_research` | `query` | Run the research service; `depth` is optional. |
| `create_reminder` | `title`, `scheduled_time` | Create a reminder. |

## Integration boundaries

- The registered `calculator` is the chat math tool. The separate `MathEngine` is not registered here.
- `MultiDocumentReasoner`, `VisionAnalyzer`, and `OCRService` are not chat tools. Image upload does not perform OCR.
- A plugin registry exists, but plugin tools are not currently added to this chat registry.
- The chat tool-call list and schemas are not a complete list of API capabilities. See [API.md](API.md) for standalone endpoints.
