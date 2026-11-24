# JARVIS Deployment

The repository currently documents local development and Docker Compose. It does not include Kubernetes manifests, a Gunicorn dependency, or a supported cloud deployment recipe. Review [SECURITY.md](SECURITY.md) before exposing the service beyond a trusted local network.

## Local development

Follow [SETUP.md](SETUP.md). The FastAPI backend listens on port `8765`; Vite serves the frontend on port `1420` and proxies `/api` to the backend.

## Docker Compose

The default Compose service builds the frontend into the backend image and serves both UI and API on port `8765`. Before starting, copy `.env.example` to `.env` at the repository root and set `JARVIS_API_KEY` plus any provider keys you intend to use.

```powershell
docker compose up --build
```

Open `http://localhost:8765`. To run a separate Vite development server in a container, use the optional profile:

```powershell
docker compose --profile dev up --build
```

The development frontend is at `http://localhost:1420`; the API remains on `http://localhost:8765`. The Compose backend disables local application launching.

## Persistence

Compose mounts the named `jarvis-data` volume at `/app/data`. This contains two SQLite databases, project/reminder JSON files, uploads, and generated files. See [DATABASE.md](DATABASE.md); backing up only `jarvis_memory.db` is insufficient.

## Exposure and operations

- Configure a strong `JARVIS_API_KEY`; do not rely on the generated ephemeral key, which is currently logged if no key is set.
- Configure exact allowed origins and TLS at a trusted reverse proxy before remote access.
- The code-execution service is not an OS/container sandbox. Do not expose it to untrusted users.
- No production readiness, scaling, backup automation, secret-manager integration, or high-availability guarantee is asserted by this repository.
