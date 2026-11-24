# JARVIS Security Architecture & Threat Model

Security is a foundational pillar of JARVIS. Because JARVIS is designed as an autonomous operating assistant capable of executing tools, managing files, and interacting with external services, rigorous multi-layered defense mechanisms are enforced across all tiers.

---

## 1. Authentication & API Access Control

JARVIS implements fail-closed authentication for all administrative, conversational, coding, file, and system endpoints (`app/services/auth.py`):

- **Master API Key**: High-entropy cryptographically generated key configured via `JARVIS_API_KEY`. If unconfigured, a secure ephemeral key is generated on startup.
- **Session Tokens**: Temporary, high-entropy tokens issued via `POST /api/auth/token` for authenticated browser/client sessions.
- **Constant-Time Verification**: All credentials are evaluated using constant-time comparisons (`hmac.compare_digest`) to prevent timing side-channel attacks.
- **Authentication Dependency**: FastAPI dependency `require_auth` protects `/api/chat`, `/api/settings`, `/api/code/*`, `/api/files/*`, `/api/projects/*`, `/api/memory/*`, `/api/automation/*`, and `/api/local-actions/*`. Unauthenticated requests receive `401 Unauthorized`.
- **Public Endpoints**: Only `/health`, `/api/health`, and `/api/auth/status` are publicly accessible.

---

## 2. Safety Tiers & Action Confirmation

JARVIS implements three explicit permission tiers configured via the canonical environment variable `JARVIS_PERMISSION_MODE` (with `JARVIS_SAFETY_TIER` supported as a backward-compatible alias):

| Mode / Tier | Setting Value | Characteristics | Permitted Actions |
| :--- | :--- | :--- | :--- |
| **`READ ONLY`** | `read_only` | Completely passive. No filesystem modifications, code execution, or app launches. | Chat, reading authorized workspace files, document extraction, calculator, memory inspection. Writes, code runs, app launches, uploads, and deletions are strictly rejected. |
| **`ASSISTED`** *(Default)* | `assisted` | Interactive confirmation required for destructive or high-impact actions. | Triggers HUD confirmation modal with detailed parameter payload before executing writes, app launches, code execution, or external actions. |
| **`FULL CONTROL`** | `full_control` | Autonomous tool execution enabled for authorized personal engineering environments. | Direct tool chaining with audit logging and verification loops. Requires deliberate user opt-in. |

### Emergency Stop Kill-Switch
- At any time, an authenticated client can trigger `POST /api/auth/emergency-stop`.
- Instantly activates `settings.emergency_stop_active = True`.
- Halts all tool execution, autonomous task steps, code execution, and application launches fail-closed across all systems.
- Normal operation is restored only via authenticated `POST /api/auth/emergency-reset`.

### Confirmation Security Architecture (`app/services/confirmation.py`)
1. **Cryptographically Secure IDs**: Action IDs are generated using `secrets.token_urlsafe(24)` with prefix `act_`.
2. **Session-Bound Confirmation**: Each confirmation token is strictly bound to the requesting session ID. Cross-session confirmations are rejected.
3. **Expiration (TTL)**: Confirmations expire automatically after 300 seconds (5 minutes). Expired confirmations cannot be executed.
4. **One-Time Use & Replay Protection**: Confirmation tokens are atomically consumed upon execution; replay attempts are rejected.
5. **Argument Integrity**: Tool arguments are fingerprinted with a SHA-256 canonical hash upon creation. Attempting to execute with tampered arguments is blocked.
6. **Thread-Safe Storage**: Internal state is guarded by locks with automatic purging of stale actions.

---

## 3. Tool Registry & Authorization (`app/services/tools/registry.py`)

- **Default-Deny Policy**: Any unregistered or unknown tool is denied by default. Unknown tools never inherit low-risk permissions.
- **High-Impact Classification**: `write_file`, `open_application`, and `execute_python_code` are strictly classified as `RiskLevel.HIGH`.
- **Pre-Execution Validation**: Permissions and capability approvals are validated immediately before running any tool inside `execute_tool_call`.
- **Strict Schema Validation**: Tool arguments are validated against strict type and format constraints prior to invocation.

---

## 4. Execution Sandbox & Isolation (`app/services/coding/sandbox.py`)

Untrusted user code or AI-generated scripts are executed under defense-in-depth restrictions:
- **Static AST Pre-Execution Analysis**: Python code is parsed into an Abstract Syntax Tree before any execution. Code attempting to import hazardous modules (`os`, `sys`, `subprocess`, `socket`, `shutil`, `ctypes`, `importlib`, etc.), call dangerous built-ins (`eval`, `exec`, `open`, `__import__`, `compile`), or perform dunder introspection (`__subclasses__`, `__mro__`, `__globals__`) is rejected with a `CodeSecurityError` before any process is spawned.
- **Python Isolated Mode (`-I`)**: Python subprocess runs with `-I`, which isolates Python from `PYTHONPATH`, user site-packages, and external python environment modifications.
- **Environment Scrubbing**: Host secrets, API keys, and database URLs are scrubbed—the child subprocess receives only `PYTHONIOENCODING=utf-8` and clean execution paths.
- **Ephemeral Filesystem**: Code executes inside a temporary directory (`tempfile.TemporaryDirectory()`) that is wiped upon execution finish.
- **Resource Constraints**: Strict timeout limits (`JARVIS_SANDBOX_TIMEOUT`, default 15s) terminate runaway processes.
- **Output Buffering**: Stdout and stderr streams are capped at 50 KB to prevent buffer exhaustion.
- **Isolation Disclosure**: Identifies execution tier as `restricted_ast_subprocess`. Kernel container isolation (Docker/gVisor) is recommended for untrusted multi-tenant workloads.

---

## 5. Filesystem Security & Path Traversal Defense (`app/services/tools/file_tools.py` & `app/api/files.py`)

- **Canonical Path Resolution**: All paths are resolved to their canonical absolute representation (`path.resolve()`).
- **Workspace Boundary Enforcement**: Checks verify that target filepaths are relative to the authorized workspace root prefix (`candidate.is_relative_to(root)`).
- **Symlink & Traversal Rejection**: Null bytes, sequences like `../../`, and symlinks targeting external directories are blocked with permission violations.
- **Protected File Defense**: Direct reads, writes, downloads, or deletions of `.env`, `.env.*`, `*.db`, `*.sqlite`, `.pem`, and `.key` files are strictly blocked.
- **Upload Restrictions**: Uploads enforce a 50 MB size limit, filename sanitization, and an extension allowlist (`.pdf`, `.docx`, `.pptx`, `.xlsx`, `.csv`, `.json`, `.txt`, `.md`, `.py`, `.js`, `.ts`, `.html`, `.css`).

---

## 6. SSRF & Safe Web Retrieval (`app/services/security_network.py` & `app/services/tools/web_reader.py`)

The web scraping and research engine enforces comprehensive Server-Side Request Forgery (SSRF) defenses:
- **Protocol Allowlist**: Only `http://` and `https://` schemes are permitted.
- **Private & Reserved IP Blocking**: All private RFC1918, loopback (`127.0.0.0/8`, `::1`), link-local (`169.254.0.0/16`, `fe80::/10`), carrier-grade NAT (`100.64.0.0/10`), multicast (`224.0.0.0/4`), and reserved ranges are blocked.
- **Cloud Metadata Defense**: Cloud metadata hostnames (`169.254.169.254`, `metadata.google.internal`, `instance-data`) are explicitly blocked.
- **DNS Resolution & Rebinding Defense**: Hostnames are resolved to IP addresses via `socket.getaddrinfo`. If *any* resolved address is restricted, the connection is aborted.
- **Redirect Hop Inspection**: Redirects are followed manually with `allow_redirects=False` (max 3 hops). Every redirect destination is re-validated against DNS and IP restrictions before connecting.
- **Response Size Caps**: Web responses stream up to 5 MB max before truncation, preventing denial-of-service memory exhaustion.
- **Strict Timeouts**: Enforces connection (3.5s) and read (7.5s) timeouts.

---

## 7. Reporting Security Issues

If you discover a potential security vulnerability in JARVIS, please report it privately to the maintainers or open a restricted security advisory rather than submitting public issues.
