"""
JARVIS 2.0 — Extended Subsystem Health & Readiness Probes.
Provides dedicated diagnostic health endpoints for orchestration, AI providers, database, storage, and background workers.
"""
from typing import Any
import os
import shutil
from fastapi import APIRouter

from app.services.ai.factory import list_configured_providers
from app.services.memory.persistent_memory import PersistentMemoryStore
from app.settings import settings

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get("")
@router.get("/")
async def health_root() -> dict[str, str]:
    return {"status": "ok", "system": "JARVIS 2.0", "version": "2.0.0"}


@router.get("/ai")
async def health_ai() -> dict[str, Any]:
    providers = list_configured_providers()
    return {
        "status": "healthy" if len(providers) > 0 else "degraded",
        "configuredProviders": providers,
        "primaryProvider": settings.ai_provider,
        "geminiConfigured": bool(settings.google_api_key),
        "groqConfigured": bool(settings.groq_api_key),
        "openaiConfigured": bool(settings.openai_api_key),
    }


@router.get("/database")
async def health_database() -> dict[str, Any]:
    try:
        mem_store = PersistentMemoryStore()
        exists = os.path.exists(mem_store.db_path)
        return {
            "status": "healthy",
            "databaseType": "SQLite",
            "dbPath": mem_store.db_path,
            "connected": True,
            "fileExists": exists,
        }
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


@router.get("/storage")
async def health_storage() -> dict[str, Any]:
    data_dir = str(settings.data_dir)
    workspace_dir = str(settings.workspace_root)

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(workspace_dir, exist_ok=True)

    disk = shutil.disk_usage(data_dir)
    return {
        "status": "healthy",
        "dataDirectory": data_dir,
        "workspaceDirectory": workspace_dir,
        "totalDiskGb": round(disk.total / (1024**3), 2),
        "freeDiskGb": round(disk.free / (1024**3), 2),
        "usedDiskGb": round(disk.used / (1024**3), 2),
    }


@router.get("/workers")
async def health_workers() -> dict[str, Any]:
    from app.services.events.bus import event_bus
    from app.services.plugins.base import plugin_registry

    return {
        "status": "healthy",
        "activePlugins": plugin_registry.list_plugins(),
        "recentEventCount": len(event_bus.get_recent_events(limit=50)),
        "taskGraphEngine": "online",
    }
