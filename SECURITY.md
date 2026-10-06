# JARVIS Security Architecture & Threat Model

Security is a foundational pillar of JARVIS. Because JARVIS is designed as an autonomous operating assistant capable of executing tools, managing files, and interacting with external services, rigorous multi-layered defense mechanisms are enforced across all tiers.

---

## 1. Safety Tiers & Action Confirmation

JARVIS implements three explicit permission tiers configured via `JARVIS_SAFETY_TIER`:

| Tier | Characteristics | Permitted Actions |
| :--- | :--- | :--- |
| **`READ ONLY`** | Completely passive. No filesystem changes or external command execution. | Chat, reading files, document analysis, calculations, memory inspection. |
| **`ASSISTED`** *(Default)* | Interactive confirmation required for destructive or high-impact actions. | Triggers confirmation modal with detailed parameter payload before executing writes, app launches, or modifications. |
| **`FULL CONTROL`** | Autonomous tool execution enabled for authorized administrative environments. | Direct tool chaining with audit logging. |

### High-Impact Tool Classification
Tools requiring explicit confirmation in `ASSISTED` mode:
- `open_application` / OS command triggers
- `write_file` / File modifications outside temporary scratchpad
- High-impact web scraping or external webhook calls

---

## 2. Execution Sandbox & Isolation

Untrusted user code or AI-generated scripts are executed in an isolated runtime environment (`app/services/coding/sandbox.py`):
- **Process Isolation**: Code runs in a spawned sub-process with bounded permissions.
- **Resource Constraints**: Strict timeout limits (`JARVIS_SANDBOX_TIMEOUT`, default 15s) prevent infinite loops or CPU exhaustion.
- **Output Buffering**: Stdout and stderr streams are capped at 50,000 characters to prevent memory buffer overflows.
- **AST Sanitization**: Mathematical evaluations via the calculator tool use Python AST parsing rather than `eval()`, preventing code injection.

---

## 3. Filesystem Security & Path Traversal Defense

JARVIS strictly confines all file reads, writes, and searches to designated workspace directories:
- **Canonical Path Resolution**: All paths are resolved to their canonical absolute representation (`path.resolve()`).
- **Workspace Boundary Enforcement**: Checks verify that target filepaths start with the authorized workspace root prefix (`os.path.commonpath`).
- **Traversal Rejection**: Sequences such as `../../etc/passwd` or `..\..\Windows\System32` are rejected with explicit permission violations.

---

## 4. SSRF & Network Protection

The web scraping and research engine (`app/services/tools/web_reader.py`) protects against Server-Side Request Forgery (SSRF):
- **Protocol Whitelisting**: Only `http://` and `https://` schemes are permitted.
- **Private IP & Loopback Blocking**: Requests to `127.0.0.1`, `localhost`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, and cloud metadata endpoints (`169.254.169.254`) are intercepted and rejected.

---

## 5. API Key & Credential Hygiene

- **No Hardcoded Keys**: All credentials are dynamically loaded from environment variables or `.env`.
- **Gitignore Protection**: `.env`, `.venv`, and `data/` caches are excluded from version control.
- **Diagnostics Masking**: Diagnostics and settings endpoints mask sensitive API keys before returning payloads to the frontend.

---

## 6. Reporting Security Issues

If you discover a potential security vulnerability in JARVIS, please report it privately to the maintainers or open a restricted security advisory rather than submitting public issues.
