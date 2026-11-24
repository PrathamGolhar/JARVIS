# JARVIS Testing

Tests live in `backend/tests/` and `frontend/src/`. Test counts are intentionally omitted because they change as the suite evolves; historical audit reports may contain stale totals.

## Backend

Install runtime and test dependencies from the repository root:

```powershell
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -v
```

CI runs the backend suite on Python 3.11 with the local provider selected.

## Frontend

From `frontend/`:

```powershell
npm ci
npm test
npm run lint
npm run build
```

`npm run lint` currently performs the TypeScript project check (`tsc -b`); it is not an ESLint run. `npm test` runs Vitest. The build performs the TypeScript check and Vite production build.

These commands verify automated tests and build/type correctness. They do not establish that external providers, search services, OCR, or production deployment are available. No fixed benchmark suite is claimed here.
