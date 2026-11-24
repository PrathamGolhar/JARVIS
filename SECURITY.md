# JARVIS Security

This document describes security controls visible in the current source, not a certification or guarantee that the application is safe for untrusted multi-tenant use.

## Authentication

With authentication enabled (the default outside test mode), operational API routes use `require_auth` or the principal dependency. Requests may use a configured API key (`JARVIS_API_KEY`) or an in-memory session token. `POST /api/auth/token` exchanges a valid API key for a session token; tokens expire after 24 hours and are held in process memory, so a restart invalidates them. Health and auth bootstrap/status routes have separate access behavior.

**Important current limitation:** if `JARVIS_API_KEY` is empty, the backend generates an ephemeral key and logs its value. Configure a strong key before exposing the service, and protect logs. The key is not persistent across restarts.

Credential checks use constant-time comparison. Elevating the permission mode to `full_control` through settings requires valid re-authentication or a confirmation token.

## Permissions and confirmations

`JARVIS_PERMISSION_MODE` supports `read_only`, `assisted` (default), and `full_control`. The authoritative capability policy is in `backend/app/services/permissions.py`; chat tool schemas and dispatch are in `backend/app/services/tools/registry.py`. Unknown tools fail closed. Policy outcomes depend on the capability and mode; do not infer a separate numeric risk tier.

Confirmation actions are session-bound, expire after 300 seconds, are single-use, and include an argument hash. The API also exposes authenticated emergency-stop and reset routes. Docker Compose disables local application launching.

## Code execution boundary

The code service applies Python AST checks, runs Python with isolated mode (`-I`), uses a temporary working directory, passes a reduced environment, enforces a timeout, and caps captured output. The environment still includes platform support variables such as `PATH` and `SYSTEMROOT`. It does not impose operating-system memory or CPU quotas and is not a container, VM, or kernel sandbox. Do not use it as a security boundary for hostile multi-tenant code.

## Files and outbound requests

Uploads require authentication/principal ownership, enforce an extension allowlist and a 50 MB size limit, and reject uploads in `read_only` mode. Text-extractable documents can be indexed with owner/session/project scope. Images are not OCR'd or indexed by the upload route. Workspace file operations apply path-boundary checks and restrict sensitive file types.

External page retrieval uses HTTP(S), validates resolved addresses, rejects private/reserved destinations, checks redirects, and applies response-size and timeout limits. This does not make retrieved content trustworthy: treat page text as untrusted input and citations as links, not verified evidence.

## Remaining security work

- Remove the ephemeral API key from logs or require an explicit key outside development.
- Add OS-level isolation/resource limits before offering code execution to untrusted or multi-tenant users.
- Review reverse-proxy, TLS, secret storage, and data-at-rest protections for each deployment; the repository does not provide application-level encryption at rest.

Report suspected vulnerabilities privately to maintainers rather than publishing exploit details.
