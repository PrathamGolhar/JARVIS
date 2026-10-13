# JARVIS Security Architecture & Threat Model

Security is a foundational pillar of JARVIS. Because JARVIS is designed as an autonomous operating assistant capable of executing tools, managing files, and interacting with external services, rigorous multi-layered defense mechanisms are enforced across all tiers.

---

## 1. Safety Tiers & Action Confirmation

JARVIS implements three explicit permission tiers configured via the canonical environment variable `JARVIS_PERMISSION_MODE` (with `JARVIS_SAFETY_TIER` supported as a backward-compatible alias):

| Mode / Tier | Setting Value | Characteristics | Permitted Actions |
| :--- | :--- | :--- | :--- |
| **`READ ONLY`** | `read_only` | Completely passive. No filesystem modifications, code execution, or app launches. | Chat, reading authorized workspace files, document extraction, calculator, memory inspection. |
| **`ASSISTED`** *(Default)* | `assisted` | Interactive confirmation required for destructive or high-impact actions. | Triggers HUD confirmation modal with detailed parameter payload before executing writes, app launches, or external actions. |
| **`FULL CONTROL`** | `full_control` | Autonomous tool execution enabled for authorized personal engineering environments. | Direct tool chaining with audit logging and verification loops. |

### Security Boundaries & Tool Enforcement
- **Read-Only Mode Enforcement**: In `read_only` mode, `write_workspace_file`, `execute_sandboxed_code`, and `execute_local_action` are immediately rejected with security exception responses.
- **Environment Protection**: `write_workspace_file` strictly blocks writing or overwriting `.env` configuration files to prevent credential hijacking or settings tampering.
- **High-Impact Tools**: Tools requiring explicit confirmation in `assisted` mode:
  - `open_application` / OS desktop triggers
  - `write_file` / File modifications outside temporary scratchpads
  - High-impact web actions and system operations

---

## 2. Execution Sandbox & Isolation

Untrusted user code or AI-generated scripts are executed in an isolated runtime environment (`app/services/coding/sandbox.py`):
- **Python Isolated Mode (`-I`)**: Python scripts run with `-I`, which isolates Python from `PYTHONPATH`, user site-packages, and external python environment modifications.
- **Environment Sanitization**: Host secrets, API keys, and database URLs are scrubbed—the child subprocess receives only `PYTHONIOENCODING=utf-8` and `PATH`.
- **Ephemeral Filesystem**: Code executes inside a temporary directory (`tempfile.TemporaryDirectory()`) that is wiped upon execution finish.
- **Resource Constraints**: Strict timeout limits (`JARVIS_SANDBOX_TIMEOUT`, default 15s) terminate runaway processes.
- **Output Buffering**: Stdout and stderr streams are capped at 50,000 characters to prevent buffer exhaustion.
- **AST Sanitization**: Mathematical evaluations via the calculator tool use Python AST parsing rather than `eval()`, preventing code injection.

> ⚠️ **Known Sandbox Limitation (P2 — Security):**
> The current sandbox uses `subprocess.run` with a temporary directory. This is **process-level isolation only** — it is **not** a full container or VM-level sandbox. Malicious code could potentially access the host filesystem, network, or environment variables (except PATH, which is the only env var passed). This design is appropriate for a **personal assistant on a trusted personal computer**.
>
> **To run JARVIS in an environment with untrusted code execution, deploy inside Docker** (which adds OS-level isolation) and consider further restricting the container with seccomp/AppArmor profiles.
>
> Code execution is disabled in Docker by default (`JARVIS_LOCAL_ACTIONS_ENABLED=false` in docker-compose).

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
