from typing import Any
import os
import shutil
from fastapi import APIRouter, Response, status

from app.services.ai.factory import list_configured_providers
from app.services.diagnostics_service import test_database_connectivity, test_storage_health
from app.services.memory.persistent_memory import PersistentMemoryStore
from app.settings import settings

router = APIRouter(tags=["Health & Readiness"])


@router.get("/health")
@router.get("/health/")
@router.get("/api/health")
async def health_liveness() -> dict[str, Any]:
    """Lightweight liveness probe ensuring the web server process is responsive."""
    return {"status": "ok", "system": "JARVIS 2.0", "version": "2.0.0"}


@router.get("/ready")
@router.get("/ready/")
@router.get("/api/ready")
async def health_readiness(response: Response) -> dict[str, Any]:
    """
    Truthful dependency readiness probe. Checks database, storage, and AI engine status.
    Returns HTTP 200 if dependencies are ready, or 503 if a critical dependency is broken.
    """
    db_ok, db_lat, db_msg = test_database_connectivity()
    st_ok, st_lat, st_msg = test_storage_health()
    providers = list_configured_providers()
    ai_ok = len(providers) > 0  # Local engine is always available

    is_ready = db_ok and st_ok and ai_ok
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "degraded",
        "database": {"ready": db_ok, "latencyMs": db_lat, "message": db_msg},
        "storage": {"ready": st_ok, "latencyMs": st_lat, "message": st_msg},
        "ai": {"ready": ai_ok, "availableProviders": providers, "primary": settings.ai_provider},
    }


@router.get("/health/ai")
async def health_ai() -> dict[str, Any]:
    providers = list_configured_providers()
    return {
        "status": "healthy" if len(providers) > 0 else "degraded",
        "configuredProviders": providers,
        "primaryProvider": settings.ai_provider,
        "geminiConfigured": bool(settings.gemini_api_key),
        "groqConfigured": bool(settings.groq_api_key),
        "openaiConfigured": bool(settings.openai_api_key),
        "anthropicConfigured": bool(settings.anthropic_api_key),
    }


@router.get("/health/database")
async def health_database() -> dict[str, Any]:
    db_ok, db_lat, db_msg = test_database_connectivity()
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "databaseType": "SQLite",
        "dbPath": str(settings.data_dir / "jarvis_memory.db"),
        "connected": db_ok,
        "latencyMs": db_lat,
        "details": db_msg,
    }


@router.get("/health/storage")
async def health_storage() -> dict[str, Any]:
    data_dir = str(settings.data_dir)
    workspace_dir = str(settings.workspace_root)

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(workspace_dir, exist_ok=True)

    disk = shutil.disk_usage(data_dir)
    st_ok, st_lat, st_msg = test_storage_health()
    return {
        "status": "healthy" if st_ok else "unhealthy",
        "dataDirectory": data_dir,
        "workspaceDirectory": workspace_dir,
        "totalDiskGb": round(disk.total / (1024**3), 2),
        "freeDiskGb": round(disk.free / (1024**3), 2),
        "usedDiskGb": round(disk.used / (1024**3), 2),
        "latencyMs": st_lat,
    }


@router.get("/health/workers")
async def health_workers() -> dict[str, Any]:
    from app.services.events.bus import event_bus
    from app.services.plugins.base import plugin_registry

    return {
        "status": "healthy",
        "activePlugins": plugin_registry.list_plugins(),
        "recentEventCount": len(event_bus.get_recent_events(limit=50)),
        "taskGraphEngine": "online",
    }
