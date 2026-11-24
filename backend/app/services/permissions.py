"""
Authoritative Capability, Permission, and Action Security Policy Engine for JARVIS.

Defines all legitimate, verified capabilities across Voice, AI, Tools, Web, Files, Desktop, TTS, and Visualizers.
Enforces server-side permissions across READ_ONLY, ASSISTED, and FULL_CONTROL modes.
Provides fail-closed tool execution validation, audit logging, and an emergency stop kill-switch.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from typing import Any, Optional

from app.settings import settings

logger = logging.getLogger("jarvis.permissions")
audit_logger = logging.getLogger("jarvis.audit")


class PermissionMode(str, Enum):
    READ_ONLY = "read_only"
    ASSISTED = "assisted"
    FULL_CONTROL = "full_control"


class CapabilityCategory(str, Enum):
    VOICE = "voice"
    AI = "ai"
    WEB = "web"
    MATH = "math"
    SYSTEM = "system"
    FILES = "files"
    DESKTOP = "desktop"
    TTS = "tts"
    VISUALIZER = "visualizer"
    CODING = "coding"


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    DENIED = "denied"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Capability:
    name: str
    category: CapabilityCategory
    description: str
    requires_confirmation: bool = False
    is_destructive_or_sensitive: bool = False
    tool_name: Optional[str] = None


# Authoritative Registry of ALL Legitimate Application Capabilities
APPROVED_CAPABILITIES: dict[str, Capability] = {
    # 1. Voice & Audio Capture Pipeline
    "voice.microphone.listen": Capability(
        name="voice.microphone.listen",
        category=CapabilityCategory.VOICE,
        description="Access device microphone with studio audio constraints (echoCancellation, noiseSuppression, autoGainControl).",
        requires_confirmation=False,
    ),
    "voice.audio.capture": Capability(
        name="voice.audio.capture",
        category=CapabilityCategory.VOICE,
        description="Capture and buffer microphone PCM/WebM/Opus audio streams for analysis and recognition.",
        requires_confirmation=False,
    ),
    "voice.vad.detect": Capability(
        name="voice.vad.detect",
        category=CapabilityCategory.VOICE,
        description="Real-time Voice Activity Detection with 3-tier pause tolerance.",
        requires_confirmation=False,
    ),
    "voice.speech.stream": Capability(
        name="voice.speech.stream",
        category=CapabilityCategory.VOICE,
        description="Continuous real-time speech-to-text recognition streaming via WebSpeech API.",
        requires_confirmation=False,
    ),
    "voice.speech.interim": Capability(
        name="voice.speech.interim",
        category=CapabilityCategory.VOICE,
        description="Real-time interim speech transcript streaming and in-place authoritative hypothesis revisions.",
        requires_confirmation=False,
    ),
    "voice.speech.final": Capability(
        name="voice.speech.final",
        category=CapabilityCategory.VOICE,
        description="Assembly and validation of finalized speech transcripts upon end-of-speech detection.",
        requires_confirmation=False,
    ),
    "voice.speech.fallback": Capability(
        name="voice.speech.fallback",
        category=CapabilityCategory.VOICE,
        description="Automatic transcription fallback using Backend Groq Whisper Large v3.",
        requires_confirmation=False,
    ),
    "voice.audio.dsp_analysis": Capability(
        name="voice.audio.dsp_analysis",
        category=CapabilityCategory.VOICE,
        description="Web Audio API DSP extraction of RMS amplitude, 16-band spectrum, pitch centroid Hz, and transient emphasis.",
        requires_confirmation=False,
    ),

    # 2. AI Reasoning & Conversation Memory
    "ai.conversation.read": Capability(
        name="ai.conversation.read",
        category=CapabilityCategory.AI,
        description="Read multi-turn conversation history from persistent SQLite memory.",
        requires_confirmation=False,
    ),
    "ai.conversation.write": Capability(
        name="ai.conversation.write",
        category=CapabilityCategory.AI,
        description="Persist user queries and assistant responses to SQLite memory.",
        requires_confirmation=False,
    ),
    "ai.conversation.context": Capability(
        name="ai.conversation.context",
        category=CapabilityCategory.AI,
        description="Inject contextual entity memory, preferences, and system grounding rules into LLM orchestration.",
        requires_confirmation=False,
    ),
    "ai.intent.understand": Capability(
        name="ai.intent.understand",
        category=CapabilityCategory.AI,
        description="Deconstruct complex multi-part user instructions into sub-tasks and tool invocations.",
        requires_confirmation=False,
    ),
    "ai.response.generate": Capability(
        name="ai.response.generate",
        category=CapabilityCategory.AI,
        description="Generate articulate, spoken plain-text voice replies via Groq/Gemini models.",
        requires_confirmation=False,
    ),

    # 3. Web & Live Internet Research
    "web.search": Capability(
        name="web.search",
        category=CapabilityCategory.WEB,
        description="Perform live internet searches for news, documentation, prices, and facts.",
        requires_confirmation=False,
        tool_name="web_search",
    ),
    "web.read": Capability(
        name="web.read",
        category=CapabilityCategory.WEB,
        description="Extract and summarize clean text content from webpage URLs.",
        requires_confirmation=False,
        tool_name="read_webpage",
    ),
    "web.weather": Capability(
        name="web.weather",
        category=CapabilityCategory.WEB,
        description="Fetch live real-time weather forecasts and temperature for any location.",
        requires_confirmation=False,
        tool_name="get_weather",
    ),
    "web.action.plan": Capability(
        name="web.action.plan",
        category=CapabilityCategory.WEB,
        description="Plan safe browser navigation destinations, YouTube, and Spotify search URLs.",
        requires_confirmation=False,
    ),
    "web.deep_research": Capability(
        name="web.deep_research",
        category=CapabilityCategory.WEB,
        description="Multi-source deep research with citation extraction.",
        requires_confirmation=False,
        tool_name="deep_web_research",
    ),

    # 4. Safe Computation & System Diagnostics
    "math.calculator": Capability(
        name="math.calculator",
        category=CapabilityCategory.MATH,
        description="Safely evaluate mathematical calculations, formulas, and conversions via AST.",
        requires_confirmation=False,
        tool_name="calculator",
    ),
    "system.diagnostics": Capability(
        name="system.diagnostics",
        category=CapabilityCategory.SYSTEM,
        description="Retrieve hardware telemetry: CPU %, RAM %, Disk free space, Uptime, Battery.",
        requires_confirmation=False,
        tool_name="system_diagnostics",
    ),
    "system.status.check": Capability(
        name="system.status.check",
        category=CapabilityCategory.SYSTEM,
        description="Check backend service connectivity, latency, and operational health.",
        requires_confirmation=False,
    ),

    # 5. Workspace Files & Document Generation
    "files.search": Capability(
        name="files.search",
        category=CapabilityCategory.FILES,
        description="Search authorized workspace directories for files matching pattern criteria.",
        requires_confirmation=False,
        tool_name="search_files",
    ),
    "files.read": Capability(
        name="files.read",
        category=CapabilityCategory.FILES,
        description="Read file contents within workspace boundary (PDF, TXT, Code, Markdown, CSV, JSON).",
        requires_confirmation=False,
        tool_name="read_file",
    ),
    "files.upload": Capability(
        name="files.upload",
        category=CapabilityCategory.FILES,
        description="Upload and analyze user documents within workspace boundary.",
        requires_confirmation=False,
        is_destructive_or_sensitive=True,
    ),
    "files.write": Capability(
        name="files.write",
        category=CapabilityCategory.FILES,
        description="Create or overwrite files in the workspace (Sensitive: requires explicit user confirmation).",
        requires_confirmation=True,
        is_destructive_or_sensitive=True,
        tool_name="write_file",
    ),
    "files.generate_presentation": Capability(
        name="files.generate_presentation",
        category=CapabilityCategory.FILES,
        description="Generate PowerPoint slides in generated folder.",
        requires_confirmation=False,
        tool_name="generate_presentation",
    ),
    "files.generate_pdf": Capability(
        name="files.generate_pdf",
        category=CapabilityCategory.FILES,
        description="Generate PDF document in generated folder.",
        requires_confirmation=False,
        tool_name="generate_pdf_report",
    ),
    "files.generate_word": Capability(
        name="files.generate_word",
        category=CapabilityCategory.FILES,
        description="Generate Word document in generated folder.",
        requires_confirmation=False,
        tool_name="generate_word_doc",
    ),

    # 6. Desktop Automation
    "desktop.open_application": Capability(
        name="desktop.open_application",
        category=CapabilityCategory.DESKTOP,
        description="Launch allowlisted Windows desktop applications (Calculator, Notepad, File Explorer, VS Code).",
        requires_confirmation=True,
        is_destructive_or_sensitive=True,
        tool_name="open_application",
    ),

    # 7. Code Execution & Sandboxing
    "coding.execute": Capability(
        name="coding.execute",
        category=CapabilityCategory.CODING,
        description="Execute code in sandboxed subprocess with strict AST validation.",
        requires_confirmation=True,
        is_destructive_or_sensitive=True,
        tool_name="execute_python_code",
    ),

    # 8. Memory & Scheduler
    "memory.set_preference": Capability(
        name="memory.set_preference",
        category=CapabilityCategory.AI,
        description="Save user project preference or memory item.",
        requires_confirmation=False,
        tool_name="set_user_preference",
    ),
    "scheduler.create_reminder": Capability(
        name="scheduler.create_reminder",
        category=CapabilityCategory.SYSTEM,
        description="Schedule user reminder.",
        requires_confirmation=False,
        tool_name="create_reminder",
    ),

    # 9. Text-to-Speech (TTS)
    "tts.synthesize": Capability(
        name="tts.synthesize",
        category=CapabilityCategory.TTS,
        description="Generate high-fidelity neural audio speech via Edge TTS.",
        requires_confirmation=False,
    ),
    "tts.playback": Capability(
        name="tts.playback",
        category=CapabilityCategory.TTS,
        description="Play neural audio output through browser AudioContext with visualizer tap.",
        requires_confirmation=False,
    ),
    "tts.stop": Capability(
        name="tts.stop",
        category=CapabilityCategory.TTS,
        description="Stop and reset active speech audio playback immediately.",
        requires_confirmation=False,
    ),
    "tts.interrupt": Capability(
        name="tts.interrupt",
        category=CapabilityCategory.TTS,
        description="Instant barge-in speech interruption on detected user vocalization.",
        requires_confirmation=False,
    ),

    # 10. Visualizer & UI
    "visualizer.audio_reactive": Capability(
        name="visualizer.audio_reactive",
        category=CapabilityCategory.VISUALIZER,
        description="Drive 3D holographic core and background HUD from live Web Audio DSP telemetry.",
        requires_confirmation=False,
    ),
    "visualizer.hud_telemetry": Capability(
        name="visualizer.hud_telemetry",
        category=CapabilityCategory.VISUALIZER,
        description="Render real-time 16-band spectrum equalizer, waveforms, and operational states.",
        requires_confirmation=False,
    ),
    "diagnostics.overlay": Capability(
        name="diagnostics.overlay",
        category=CapabilityCategory.VISUALIZER,
        description="Display developer real-time DSP, VAD, STT, and capability authorization telemetry.",
        requires_confirmation=False,
    ),
}

# Reverse lookup from tool name to Capability
TOOL_TO_CAPABILITY: dict[str, Capability] = {
    cap.tool_name: cap for cap in APPROVED_CAPABILITIES.values() if cap.tool_name is not None
}


def is_capability_approved(capability_name: str) -> bool:
    """Check if a capability is in the authoritative approved list."""
    return capability_name in APPROVED_CAPABILITIES


def get_capability_status(capability_name: str) -> ApprovalStatus:
    """Return the approval status of a capability."""
    cap = APPROVED_CAPABILITIES.get(capability_name)
    if not cap:
        return ApprovalStatus.DENIED
    if cap.requires_confirmation:
        return ApprovalStatus.REQUIRES_CONFIRMATION
    return ApprovalStatus.APPROVED


def get_capability_for_tool(tool_name: str) -> Capability | None:
    """Look up the capability associated with a tool name."""
    return TOOL_TO_CAPABILITY.get(tool_name)


def get_effective_permission_mode() -> PermissionMode:
    """Retrieve current permission mode, guaranteed to fail-closed to READ_ONLY if invalid."""
    mode_str = getattr(settings, "permission_mode", "assisted").lower().strip()
    try:
        return PermissionMode(mode_str)
    except ValueError:
        logger.error("Invalid permission mode '%s' in settings; failing closed to 'read_only'", mode_str)
        return PermissionMode.READ_ONLY


def trigger_emergency_stop() -> None:
    """Instantly activate the emergency stop kill switch, halting all autonomous actions."""
    settings.emergency_stop_active = True
    logger.critical("EMERGENCY STOP TRIGGERED: All autonomous actions and tools disabled immediately.")
    log_action_audit("SYSTEM", "emergency_stop_triggered", {}, "HALTED")


def reset_emergency_stop() -> None:
    """Deactivate emergency stop kill switch."""
    settings.emergency_stop_active = False
    logger.info("Emergency stop reset: Standard permission enforcement restored.")
    log_action_audit("SYSTEM", "emergency_stop_reset", {}, "RESTORED")


def log_action_audit(session_id: str, action: str, details: dict[str, Any], status: str) -> None:
    """Structured audit log entry for security and compliance."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": str(session_id),
        "action": action,
        "mode": getattr(settings, "permission_mode", "unknown"),
        "status": status,
        "details": details,
    }
    audit_logger.info("AUDIT: %s", json.dumps(record, default=str))


def validate_tool_approval(
    tool_name: str,
    arguments: Optional[dict[str, Any]] = None,
    session_id: str = "general",
) -> tuple[bool, bool, str]:
    """
    Validate whether a tool is approved for execution under the active security policy.
    Returns: (is_approved, requires_confirmation, message)

    Enforces:
    1. Emergency Stop: Everything denied.
    2. Unknown Tools: Denied by default (fail-closed, never inherits low-risk permissions).
    3. READ_ONLY: Destructive/modifying tools strictly denied.
    4. ASSISTED: Sensitive tools require explicit confirmation.
    5. FULL_CONTROL: Allowed with audit logging.
    """
    if getattr(settings, "emergency_stop_active", False):
        log_action_audit(session_id, tool_name, arguments or {}, "DENIED_EMERGENCY_STOP")
        return False, False, "Operation denied: Emergency stop is active across all systems."

    cap = TOOL_TO_CAPABILITY.get(tool_name)
    if not cap:
        # Fail closed for any unknown or unregistered tool
        log_action_audit(session_id, tool_name, arguments or {}, "DENIED_UNKNOWN_TOOL")
        return False, False, f"Tool '{tool_name}' is not in the approved capabilities registry (denied by default)."

    mode = get_effective_permission_mode()

    # Rule 1: READ_ONLY mode
    if mode == PermissionMode.READ_ONLY:
        if cap.is_destructive_or_sensitive:
            log_action_audit(session_id, tool_name, arguments or {}, "DENIED_READ_ONLY")
            return (
                False,
                False,
                f"Action '{tool_name}' is prohibited in 'read_only' permission mode (no modifications, code execution, or app launching permitted).",
            )
        log_action_audit(session_id, tool_name, arguments or {}, "APPROVED_READ_ONLY")
        return True, False, f"Capability '{cap.name}' is approved for read-only execution."

    # Rule 2: ASSISTED mode
    if mode == PermissionMode.ASSISTED:
        if cap.requires_confirmation or cap.is_destructive_or_sensitive:
            log_action_audit(session_id, tool_name, arguments or {}, "REQUIRES_CONFIRMATION")
            return True, True, f"Capability '{cap.name}' requires explicit user confirmation."
        log_action_audit(session_id, tool_name, arguments or {}, "APPROVED_ASSISTED")
        return True, False, f"Capability '{cap.name}' is auto-approved."

    # Rule 3: FULL_CONTROL mode
    if mode == PermissionMode.FULL_CONTROL:
        log_action_audit(session_id, tool_name, arguments or {}, "APPROVED_FULL_CONTROL")
        return True, False, f"Capability '{cap.name}' is approved under full control."

    # Fallback fail-closed
    return False, False, "Access denied by default security policy."
