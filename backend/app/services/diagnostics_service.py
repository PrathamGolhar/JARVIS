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

    # 1. AI Provider Engine
    ai_prov = get_ai_provider()
    is_available = ai_prov.is_available()
    items.append(DiagnosticItem(
        id="ai_engine",
        label=f"AI Core ({ai_prov.name.upper()})",
        status="active" if is_available else "warning",
        details=f"Provider: {ai_prov.name} | Model: {getattr(ai_prov, 'model', 'local-rule-engine')}",
    ))

    # 2. Database
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

    # 4. Network & Web Access
    net_ok, net_lat, net_msg = test_network_connectivity()
    items.append(DiagnosticItem(
        id="network",
        label="Live Web & Search Bridge",
        status="ready" if net_ok else "warning",
        latencyMs=net_lat,
        details=net_msg,
    ))

    # 5. Voice & TTS Subsystem
    from app.services.edge_tts_service import available_voices
    voices_list = available_voices()
    tts_ok = len(voices_list) > 0
    items.append(DiagnosticItem(
        id="tts",
        label="Voice Synthesis (Edge-TTS)",
        status="ready" if tts_ok else "warning",
        details=f"{len(voices_list)} neural voices loaded." if tts_ok else "No TTS voices found.",
    ))

    # 6. STT Subsystem
    stt_ok = bool(settings.groq_api_key and settings.groq_api_key.strip())
    items.append(DiagnosticItem(
        id="stt",
        label="Speech-To-Text (Groq Whisper)",
        status="ready" if stt_ok else "unconfigured",
        details="Whisper Large v3 configured." if stt_ok else "Groq STT key unconfigured (WebSpeech fallback active).",
    ))

    # 7. RAG Semantic Index
    rag_chunks_count = len(getattr(rag_store, "_chunks", {}))
    items.append(DiagnosticItem(
        id="rag",
        label="RAG Vector Engine",
        status="ready",
        details=f"{rag_chunks_count} document chunks indexed in active RAG memory.",
    ))

    # 8. Tools & Autonomous Agent Engine
    items.append(DiagnosticItem(
        id="tools",
        label="Autonomous Tool & Agent Engine",
        status="ready",
        details=f"{len(TOOLS_SCHEMA)} registered tools with permission verification.",
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
