"""
Authoritative Capability, Permission, and Approved Action Registry for JARVIS.

Defines all legitimate, verified capabilities across Voice, AI, Tools, Web, Files, Desktop, TTS, and Visualizers.
Ensures every intended system action is correctly approved, while sensitive operations strictly require user confirmation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


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
    tool_name: str | None = None


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
        description="Real-time Voice Activity Detection with 3-tier pause tolerance (1.2s short pause, 2.2s long pause, 2.8s end-of-speech).",
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
        description="Inject contextual entity memory, pronouns, and system grounding rules into LLM orchestration.",
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
        description="Generate articulate, spoken plain-text voice replies via Groq LLM models.",
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

    # 5. Workspace Files
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
    ),
    "files.write": Capability(
        name="files.write",
        category=CapabilityCategory.FILES,
        description="Create or overwrite files in the workspace (Sensitive: requires explicit user confirmation).",
        requires_confirmation=True,
        tool_name="write_file",
    ),

    # 6. Desktop Automation
    "desktop.open_application": Capability(
        name="desktop.open_application",
        category=CapabilityCategory.DESKTOP,
        description="Launch allowlisted Windows desktop applications (Calculator, Notepad, File Explorer, VS Code).",
        requires_confirmation=True,
        tool_name="open_application",
    ),

    # 7. Text-to-Speech (TTS)
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

    # 8. Visualizer & UI
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


def validate_tool_approval(tool_name: str) -> tuple[bool, bool, str]:
    """
    Validate whether a tool is approved for execution.
    Returns: (is_approved, requires_confirmation, message)
    """
    cap = get_capability_for_tool(tool_name)
    if not cap:
        return False, False, f"Tool '{tool_name}' is not in the approved capabilities registry."
    
    if cap.requires_confirmation:
        return True, True, f"Capability '{cap.name}' requires explicit user confirmation."
    
    return True, False, f"Capability '{cap.name}' is approved for immediate execution."
