from contextlib import asynccontextmanager
import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.auth import router as auth_router
from app.api.automation import router as automation_router
from app.api.capabilities import router as capabilities_router
from app.api.chat import router as chat_router
from app.api.coding import router as coding_router
from app.api.diagnostics import router as diagnostics_router
from app.api.files import router as files_router
from app.api.generation import router as generation_router
from app.api.local_actions import router as local_actions_router
from app.api.memory import router as memory_router
from app.api.projects import router as projects_router
from app.api.research import router as research_router
from app.api.settings_api import router as settings_router
from app.api.speech import router as speech_router
from app.api.study import router as study_router
from app.api.web_actions import router as web_actions_router
from app.core.errors import register_exception_handlers
from app.core.middleware import register_middleware
from app.services.maintenance import clean_stale_files
from app.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("jarvis.main")

# ---------------------------------------------------------------------------
# Daily disk-cleanup scheduler
# Runs once at startup (dry_run so we can log what would be removed) then
# every 24 h for real deletion.  Uses stdlib asyncio — no new dependency.
# ---------------------------------------------------------------------------
_CLEANUP_INTERVAL_SECONDS: int = 86_400  # 24 hours


async def _run_daily_cleanup() -> None:
    """Background task: clean stale generated and uploaded files every 24 h."""
    # Immediate startup pass — real deletion to recover disk space after restarts
    for target in (settings.generated_dir, settings.uploads_dir):
        try:
            summary = clean_stale_files(target_dir=target, max_age_days=7, dry_run=False)
            if summary.files_removed or summary.errors:
                logger.info(
                    "Startup cleanup [%s]: removed=%d files, reclaimed=%d bytes, errors=%d",
                    target.name,
                    summary.files_removed,
                    summary.bytes_reclaimed,
                    len(summary.errors),
                )
                for err in summary.errors:
                    logger.warning("Cleanup error: %s", err)
        except Exception:
            logger.exception("Startup cleanup failed for %s", target)

    # Recurring daily pass
    while True:
        await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
        for target in (settings.generated_dir, settings.uploads_dir):
            try:
                summary = clean_stale_files(target_dir=target, max_age_days=7, dry_run=False)
                logger.info(
                    "Daily cleanup [%s]: removed=%d files, reclaimed=%d bytes, errors=%d",
                    target.name,
                    summary.files_removed,
                    summary.bytes_reclaimed,
                    len(summary.errors),
                )
                for err in summary.errors:
                    logger.warning("Cleanup error: %s", err)
            except Exception:
                logger.exception("Daily cleanup failed for %s", target)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("==================================================")
    logger.info("  JARVIS PRODUCTION AI ASSISTANT CORE ONLINE")
    logger.info("  Workspace Root: %s", settings.workspace_root)
    logger.info("  Data Dir: %s", settings.data_dir)
    logger.info("  Active AI Provider: %s", settings.ai_provider)
    logger.info("==================================================")

    # Launch disk-cleanup background task; cancel it cleanly on shutdown
    cleanup_task = asyncio.create_task(_run_daily_cleanup(), name="jarvis-disk-cleanup")
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        logger.info("JARVIS Assistant shutting down.")


app = FastAPI(
    title="JARVIS Production AI Assistant",
    description="An elite, highly capable, serious, and joyful AI personal assistant for Windows inspired by JARVIS.",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register Observability Middleware & Centralized Exception Handlers
register_middleware(app)
register_exception_handlers(app)

from app.api.health import router as health_router

# Include All Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(files_router)
app.include_router(generation_router)
app.include_router(study_router)
app.include_router(research_router)
app.include_router(coding_router)
app.include_router(projects_router)
app.include_router(memory_router)
app.include_router(automation_router)
app.include_router(settings_router)
app.include_router(diagnostics_router)
app.include_router(capabilities_router)
app.include_router(local_actions_router)
app.include_router(speech_router)
app.include_router(web_actions_router)


@app.get("/api/health")
async def health_api_alias() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Production: serve the pre-built React frontend from /app/static
# This activates only when the dist directory exists (i.e., inside Docker).
# In local dev the Vite proxy handles /api routing; the frontend runs on 1420.
# ---------------------------------------------------------------------------
_STATIC_DIR = Path("/app/static")
if _STATIC_DIR.is_dir():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(_STATIC_DIR / "assets")), name="frontend-assets")

    # SPA catch-all: every non-/api path serves index.html so React Router works
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        index = _STATIC_DIR / "index.html"
        return FileResponse(str(index))
