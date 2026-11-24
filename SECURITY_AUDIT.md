# JARVIS 2.0 — COMPREHENSIVE SECURITY AUDIT

**Audit Date:** November 24, 2026
**Auditor:** Principal Application Security Engineer
**Classification:** Controlled Security Baseline

---

## 1. Threat Modeling & Attack Surface Overview

The JARVIS application operates with high host privileges, including:
- Executing Python code in a subprocess.
- Reading and writing files in the workspace.
- Launching desktop applications (calc, notepad, code, explorer).
- Making outbound HTTP requests to the internet for search and scraping.
- Managing long-term memory in SQLite.

Because of these capabilities, the threat surface is categorized into six critical vectors:
1. **API Authentication & Authorization (CWE-306)**
2. **Action Confirmation & Replay Attacks (CWE-287 / CWE-345)**
3. **Server-Side Request Forgery (SSRF) (CWE-918)**
4. **Sandboxed Code Execution & Host Escape (CWE-94 / CWE-269)**
5. **Path Traversal & Secret File Access (CWE-22 / CWE-200)**
6. **Prompt Injection & Indirect Injection (CWE-1388 / OWASP LLM01)**

---

## 2. In-Depth Vector Audits & Verification

### 2.1 API Authentication & Authorization
- **Implementation**: `backend/app/services/auth.py` defines `require_auth` verifying `Authorization: Bearer <token>`, `X-API-Key`, or `?api_key=`.
- **Constant-Time Verification**: Uses `hmac.compare_digest(token.encode(), configured_key.encode())` to prevent timing attacks.
- **Fail-Closed State**: If `auth_enabled=True` and token is missing or invalid, raises HTTP 401 with `WWW-Authenticate: Bearer`.
- **CRITICAL AUDIT VULNERABILITY**: While the backend enforces authentication, **the frontend client (`jarvis-frontend`) does not implement authentication**. All `fetch` calls in the React application omit credentials. In production/development mode, the backend generates an ephemeral key and blocks all frontend traffic.
- **Residual Speech Gap**: `backend/app/api/speech.py` lacks `dependencies=[Depends(require_auth)]`. `/api/tts` and `/api/transcribe` remain publicly accessible without authentication.

### 2.2 Action Confirmation & Two-Phase Verification
- **Implementation**: `backend/app/services/confirmation.py` manages `ConfirmationManager`.
- **Entropy & Uniqueness**: Tokens are generated using `secrets.token_urlsafe(24)` with prefix `act_`.
- **TTL Enforcement**: Enforces a strict 300-second (5-minute) expiration.
- **One-Time Consumption**: Once consumed, the token is deleted from memory, preventing replay attacks.
- **Payload Integrity**: Computes SHA-256 hash of target parameters (`_hash_arguments`). If an attacker alters the arguments post-confirmation, the action is rejected.
- **CRITICAL SERIALIZATION DEFECT**: While the token verification succeeds, `orchestrator.py` returns `{"tool_name": "confirmed_action", ...}` which fails Pydantic validation against `ToolEvent` (`alias="toolName"`), crashing the response with HTTP 500.

### 2.3 Server-Side Request Forgery (SSRF)
- **Implementation**: `backend/app/services/security_network.py` provides `safe_http_fetch()`.
- **IP Range Filtering**:
  - Rejects loopback (`127.0.0.0/8`, `::1`).
  - Rejects private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
  - Rejects link-local cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`).
  - Rejects carrier NAT (`100.64.0.0/10`) and multicast (`224.0.0.0/4`).
- **DNS Rebinding Protection**: Resolves hostname to all IP addresses and checks each one against blocked networks prior to connecting.
- **Redirect Validation**: Follows redirects manually (up to 5 hops), re-validating the resolved destination IP at each hop before fetching.
- **Response Cap**: Enforces a strict 5MB response size limit to prevent memory exhaustion attacks.
- **Audit Verdict**: **ROBUST & VERIFIED**.

### 2.4 Code Sandbox Isolation
- **Implementation**: `backend/app/services/coding/sandbox.py`.
- **Static AST Analysis**: `ASTSecurityValidator` walks the AST prior to execution.
  - Blocks dangerous modules: `os`, `sys`, `subprocess`, `socket`, `shutil`, `ctypes`, `importlib`, `multiprocessing`, `threading`, `signal`, `winreg`, `tempfile`, `pathlib`, `io`, `urllib`, `requests`, `webbrowser`.
  - Blocks dangerous builtins: `eval`, `exec`, `__import__`, `open`, `breakpoint`, `compile`, `globals`, `locals`, `vars`.
  - Blocks dunder traversal: `__subclasses__`, `__bases__`, `__mro__`, `__globals__`, `__code__`, `__dict__`, `__class__`.
- **Subprocess Confinement**: Executes with `clean_env` (no host environment variables or API keys), isolated `TemporaryDirectory`, and 15s timeout.
- **Residual Risk**: AST analysis runs inside the host Python interpreter. For multi-tenant cloud deployments, kernel-level containerization (Docker, gVisor, or seccomp) should be layered over AST validation.

### 2.5 Path Traversal & Sensitive File Protection
- **Implementation**: `backend/app/services/tools/file_tools.py`.
- **Workspace Boundary**: Confinement enforced against `settings.workspace_root.resolve()`. If a path escapes via `../`, it raises a permission error.
- **Null-Byte Filtering**: Rejects strings containing `\x00`.
- **Sensitive File Blocklist**: Rejects read, write, or delete actions targeting `.env`, `*.db`, `*.sqlite`, `*.pem`, `*.key`, `*.cert`.
- **Audit Verdict**: **VERIFIED**.

### 2.6 Prompt Injection & Indirect Poisoning
- **Implementation**: `backend/app/services/agents/verifier.py` (`sanitize_untrusted_content`).
- **Sanitization Strategy**: Strips explicit system instruction overrides (e.g. `ignore previous instructions`, `system prompt:`) and encloses external text within `<untrusted_external_data>` XML fences.
- **Audit Verdict**: **VERIFIED**.

---

## 3. Security Vulnerability Matrix

| ID | Title | Severity | CWE | Status | Action Required |
|:---|:---|:---:|:---:|:---:|:---|
| **SEC-01** | Frontend Missing API Auth Headers | P0 (Critical) | CWE-306 | Unresolved | Implement auth token handshake and header injection in frontend `client.ts`. |
| **SEC-02** | Schema Alias Crash on Confirmed Action | P0 (Critical) | CWE-398 | Unresolved | Add `populate_by_name=True` to `ToolEvent` and fix dict key in `orchestrator.py`. |
| **SEC-03** | Speech API Endpoints Unauthenticated | P2 (Medium) | CWE-306 | Unresolved | Attach `dependencies=[Depends(require_auth)]` to `speech.py`. |
| **SEC-04** | Global Preferences Injected Across Sessions | P2 (Medium) | CWE-200 | Unresolved | Scope preference injection in `build_system_context()` by session/user. |
| **SEC-05** | Host Subprocess Execution without Kernel Sandbox | P3 (Low) | CWE-250 | Hardened | Add optional Docker/seccomp runner for multi-tenant production hosting. |
