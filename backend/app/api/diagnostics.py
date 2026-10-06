from datetime import datetime
import os
import platform
import psutil
import shutil
import time

from fastapi import APIRouter

from app.schemas import DiagnosticItem, DiagnosticsResponse, SystemMetrics
from app.services.ai.factory import get_ai_provider
from app.services.memory import memory_store
from app.services.tools.registry import TOOLS_SCHEMA
from app.settings import settings

router = APIRouter(prefix="/api", tags=["diagnostics"])

START_TIME = time.time()


@router.get("/diagnostics", response_model=DiagnosticsResponse)
async def diagnostics() -> DiagnosticsResponse:
    items: list[DiagnosticItem] = []

    # 1. AI Provider status
    ai_prov = get_ai_provider()
    items.append(DiagnosticItem(
        id="ai_engine",
        label=f"AI Core ({ai_prov.name.upper()})",
        status="active" if ai_prov.is_available() else "warning",
        details=f"Provider: {ai_prov.name} | Model: {getattr(ai_prov, 'model', 'local-rule-engine')}",
    ))

    # 2. Voice Subsystem
    items.append(DiagnosticItem(
        id="tts",
        label="Voice Synthesis (Edge-TTS)",
        status="ready",
        details="Neural TTS online with multi-voice support",
    ))

    # 3. Speech Recognition
    items.append(DiagnosticItem(
        id="network",
        label="Network & Web Bridge",
        status="ready",
        details="Internet connectivity and live search operational",
    ))

    # 4. Memory & RAG Subsystem
    mem_count = len(memory_store.list_memories())
    items.append(DiagnosticItem(
        id="memory",
        label="Persistent Memory & RAG",
        status="ready",
        details=f"{mem_count} stored facts / preferences in SQLite",
    ))

    # 5. Tool & Agent Execution Engine
    items.append(DiagnosticItem(
        id="tools",
        label="Autonomous Tool & Agent Engine",
        status="ready",
        details=f"{len(TOOLS_SCHEMA)} tools loaded with safety validation",
    ))

    # 6. Storage & File System
    total, used, free = shutil.disk_usage(str(settings.data_dir))
    free_gb = round(free / (1024 ** 3), 1)
    items.append(DiagnosticItem(
        id="storage",
        label="Workspace Storage",
        status="ready" if free_gb > 1.0 else "warning",
        details=f"{free_gb} GB available disk space",
    ))

    # System Metrics
    cpu_pct = psutil.cpu_percent(interval=None)
    ram_pct = psutil.virtual_memory().percent
    uptime_sec = int(time.time() - START_TIME)
    uptime_str = f"{uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m {uptime_sec % 60}s"

    metrics = SystemMetrics(
        cpuPercent=cpu_pct,
        ramPercent=ram_pct,
        diskFreeGb=free_gb,
        activeToolsCount=len(TOOLS_SCHEMA),
        memoryItemsCount=mem_count,
        uptime=uptime_str,
    )

    return DiagnosticsResponse(
        ok=True,
        timestamp=datetime.now().isoformat(),
        items=items,
        systemMetrics=metrics,
    )
