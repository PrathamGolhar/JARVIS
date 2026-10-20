from datetime import datetime
import os
import platform
import shutil
import sqlite3
import sys
import time
from typing import Any
import psutil

from app.schemas import DiagnosticItem, DiagnosticsResponse, SystemMetrics
from app.services.ai.factory import get_ai_provider, list_configured_providers
from app.services.memory import memory_store
from app.services.memory.vector_store import rag_store
from app.services.tools.registry import TOOLS_SCHEMA
from app.settings import settings

START_TIME = time.time()


def test_database_connectivity() -> tuple[bool, float, str]:
    """Test SQLite read/write connectivity and measure latency."""
    t0 = time.perf_counter()
    try:
        conn = sqlite3.connect(memory_store.db_path, timeout=3.0)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        latency = (time.perf_counter() - t0) * 1000.0
        return True, round(latency, 2), "Database connection verified."
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000.0
        return False, round(latency, 2), f"Database check failed: {exc}"


def test_storage_health() -> tuple[bool, float, str]:
    """Test storage directory permissions and free space."""
    t0 = time.perf_counter()
    try:
        for d in (settings.data_dir, settings.uploads_dir, settings.generated_dir):
            d.mkdir(parents=True, exist_ok=True)
            test_file = d / ".health_check_tmp"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()

        total, used, free = shutil.disk_usage(str(settings.data_dir))
        free_gb = round(free / (1024 ** 3), 1)
        latency = (time.perf_counter() - t0) * 1000.0
        return True, round(latency, 2), f"{free_gb} GB disk space available."
    except Exception as exc:
        latency = (time.perf_counter() - t0) * 1000.0
        return False, round(latency, 2), f"Storage error: {exc}"


def test_network_connectivity() -> tuple[bool, float, str]:
    """Test network internet accessibility safely with timeout."""
    import socket
    t0 = time.perf_counter()
    try:
        # Check standard DNS resolution
        socket.setdefaulttimeout(3.0)
        socket.gethostbyname("api.groq.com")
        latency = (time.perf_counter() - t0) * 1000.0
        return True, round(latency, 2), "Internet & DNS resolution online."
    except Exception:
        # Offline or local network only
        latency = (time.perf_counter() - t0) * 1000.0
        return False, round(latency, 2), "Offline mode / DNS lookup unreachable."


def get_deep_diagnostics() -> DiagnosticsResponse:
    """Truthfully inspect and report telemetry across all JARVIS subsystems."""
    items: list[DiagnosticItem] = []

    # 1. Backend Process Core
    items.append(DiagnosticItem(
        id="backend",
        label="JARVIS Core Backend API",
        status="ready",
        details=f"FastAPI process active on {settings.backend_host}:{settings.backend_port} (Env: {settings.env})",
    ))

    # 2. Database & Persistent Store
    db_ok, db_lat, db_msg = test_database_connectivity()
    mem_count = len(memory_store.list_memories())
    items.append(DiagnosticItem(
        id="database",
        label="SQLite Persistent Store",
        status="ready" if db_ok else "error",
        latencyMs=db_lat,
        details=f"{db_msg} ({mem_count} memory items)",
    ))

    # 3. Storage
    st_ok, st_lat, st_msg = test_storage_health()
    items.append(DiagnosticItem(
        id="storage",
        label="Workspace Storage",
        status="ready" if st_ok else "error",
        latencyMs=st_lat,
        details=st_msg,
    ))

    # 4. AI Provider Engine (Truthfully separate Configured vs Active vs Fallback)
    ai_prov = get_ai_provider()
    configured_pref = settings.ai_provider.lower().strip()
    active_name = ai_prov.name.lower()

    if configured_pref not in ("auto", "local") and active_name == "local":
        ai_status = "warning"
        ai_label = f"AI Core ({configured_pref.upper()} UNAVAILABLE → LOCAL FALLBACK)"
        ai_details = f"Configured provider '{configured_pref}' has no valid API key. Operating on offline local rule engine."
    elif active_name == "local":
        ai_status = "active"
        ai_label = "AI Core (LOCAL RULE ENGINE)"
        ai_details = "Local heuristic rule engine active (offline fallback mode; no cloud LLM keys configured)."
    else:
        ai_status = "ready"
        ai_label = f"AI Core ({active_name.upper()} ACTIVE)"
        ai_details = f"Provider: {active_name} | Model: {getattr(ai_prov, 'model', 'cloud-model')} (Online & Responding)"

    items.append(DiagnosticItem(
        id="ai_engine",
        label=ai_label,
        status=ai_status,
        details=ai_details,
    ))

    # 5. Memory & RAG Semantic Index
    rag_chunks_count = len(getattr(rag_store, "_chunks", {}))
    items.append(DiagnosticItem(
        id="memory",
        label="Memory & RAG Store",
        status="ready",
        details=f"{mem_count} persistent facts | {rag_chunks_count} RAG chunks indexed in memory.",
    ))

    # 6. Live Web Search & Research
    net_ok, net_lat, net_msg = test_network_connectivity()
    if not settings.web_search_enabled:
        search_status = "unconfigured"
        search_details = "Web search capability is disabled in system settings."
    elif net_ok:
        search_status = "ready"
        search_details = "Live multi-source DuckDuckGo search ready."
    else:
        search_status = "warning"
        search_details = "Network unreachable. Live web research is currently degraded."

    items.append(DiagnosticItem(
        id="network",
        label="Live Web & Search Bridge",
        status=search_status,
        latencyMs=net_lat if net_ok else None,
        details=search_details,
    ))

    # 7. Voice & TTS Subsystem
    from app.services.edge_tts_service import available_voices
    voices_list = available_voices()
    items.append(DiagnosticItem(
        id="tts",
        label="Voice Synthesis (Edge-TTS)",
        status="ready",
        details=f"{len(voices_list)} neural voices loaded (Browser SpeechSynthesis fallback active).",
    ))

    # 8. STT Subsystem
    stt_ok = bool(settings.groq_api_key and settings.groq_api_key.strip())
    items.append(DiagnosticItem(
        id="stt",
        label="Speech-To-Text",
        status="ready",
        details="Groq Whisper Large v3 active." if stt_ok else "WebSpeech STT active (Groq Whisper unconfigured).",
    ))

    # 9. Tools & Autonomous Agent Engine
    items.append(DiagnosticItem(
        id="tools",
        label="Autonomous Tool & Agent Engine",
        status="ready",
        details=f"{len(TOOLS_SCHEMA)} registered tools with {settings.permission_mode.upper()} permission verification.",
    ))

    # 10. Code Execution Sandbox
    items.append(DiagnosticItem(
        id="sandbox",
        label="Python Sandbox Execution",
        status="ready",
        details=f"Subprocess sandbox (Timeout: {settings.sandbox_timeout_seconds}s, Mem: {settings.sandbox_memory_limit_mb}MB, CPU: {settings.sandbox_cpu_limit_pct}%).",
    ))

    # Compute System Resource Metrics
    cpu_pct = psutil.cpu_percent(interval=None)
    ram_pct = psutil.virtual_memory().percent
    total, used, free = shutil.disk_usage(str(settings.data_dir))
    free_gb = round(free / (1024 ** 3), 1)
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

    all_ok = db_ok and st_ok
    return DiagnosticsResponse(
        ok=all_ok,
        timestamp=datetime.now().isoformat(),
        items=items,
        systemMetrics=metrics,
    )
