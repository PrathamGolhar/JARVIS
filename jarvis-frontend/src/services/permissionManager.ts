/**
 * Centralized Permission & Capability Manager for JARVIS Frontend.
 *
 * Maintains the client-side authoritative cache of all approved capabilities,
 * mapping tools and actions directly to approved capabilities.
 */

import { fetchCapabilities, CapabilityDto, ApprovalStatus } from "../api/capabilities";

// Authoritative local capability definitions matching backend
export const DEFAULT_APPROVED_CAPABILITIES: Record<string, CapabilityDto> = {
  // 1. Voice & Audio Capture
  "voice.microphone.listen": {
    name: "voice.microphone.listen",
    category: "voice",
    description: "Access device microphone with browser audio constraints.",
    requiresConfirmation: false,
    status: "approved",
  },
  "voice.audio.capture": {
    name: "voice.audio.capture",
    category: "voice",
    description: "Capture and buffer microphone audio stream chunks.",
    requiresConfirmation: false,
    status: "approved",
  },
  "voice.vad.detect": {
    name: "voice.vad.detect",
    category: "voice",
    description: "Real-time Voice Activity Detection with 3-tier pause tolerance.",
    requiresConfirmation: false,
    status: "approved",
  },
  "voice.speech.stream": {
    name: "voice.speech.stream",
    category: "voice",
    description: "Continuous real-time speech recognition streaming via WebSpeech API.",
    requiresConfirmation: false,
    status: "approved",
  },
  "voice.speech.interim": {
    name: "voice.speech.interim",
    category: "voice",
    description: "Real-time streaming interim transcript updates and in-place revisions.",
    requiresConfirmation: false,
    status: "approved",
  },
  "voice.speech.final": {
    name: "voice.speech.final",
    category: "voice",
    description: "Assembly and validation of finalized speech transcripts.",
    requiresConfirmation: false,
    status: "approved",
  },
  "voice.speech.fallback": {
    name: "voice.speech.fallback",
    category: "voice",
    description: "Automatic transcription fallback via Backend Groq Whisper Large v3.",
    requiresConfirmation: false,
    status: "approved",
  },
  "voice.audio.dsp_analysis": {
    name: "voice.audio.dsp_analysis",
    category: "voice",
    description: "Web Audio API DSP extraction of RMS, spectrum bands, and pitch.",
    requiresConfirmation: false,
    status: "approved",
  },

  // 2. AI Reasoning & Conversation Memory
  "ai.conversation.read": {
    name: "ai.conversation.read",
    category: "ai",
    description: "Read multi-turn conversation history from persistent SQLite memory.",
    requiresConfirmation: false,
    status: "approved",
  },
  "ai.conversation.write": {
    name: "ai.conversation.write",
    category: "ai",
    description: "Persist user queries and assistant responses to SQLite memory.",
    requiresConfirmation: false,
    status: "approved",
  },
  "ai.conversation.context": {
    name: "ai.conversation.context",
    category: "ai",
    description: "Inject contextual entity memory and grounding rules into LLM turns.",
    requiresConfirmation: false,
    status: "approved",
  },
  "ai.intent.understand": {
    name: "ai.intent.understand",
    category: "ai",
    description: "Deconstruct multi-part user instructions into discrete tool invocations.",
    requiresConfirmation: false,
    status: "approved",
  },
  "ai.response.generate": {
    name: "ai.response.generate",
    category: "ai",
    description: "Generate articulate spoken plain-text voice replies via Groq LLM.",
    requiresConfirmation: false,
    status: "approved",
  },

  // 3. Web & Live Internet Research
  "web.search": {
    name: "web.search",
    category: "web",
    description: "Perform live internet searches for news, documentation, prices, and facts.",
    requiresConfirmation: false,
    toolName: "web_search",
    status: "approved",
  },
  "web.read": {
    name: "web.read",
    category: "web",
    description: "Extract clean text content from webpage URLs.",
    requiresConfirmation: false,
    toolName: "read_webpage",
    status: "approved",
  },
  "web.weather": {
    name: "web.weather",
    category: "web",
    description: "Fetch live real-time weather forecasts and temperature.",
    requiresConfirmation: false,
    toolName: "get_weather",
    status: "approved",
  },
  "web.action.plan": {
    name: "web.action.plan",
    category: "web",
    description: "Plan safe browser navigation destinations, YouTube, and Spotify search URLs.",
    requiresConfirmation: false,
    status: "approved",
  },

  // 4. Safe Computation & System Diagnostics
  "math.calculator": {
    name: "math.calculator",
    category: "math",
    description: "Safely evaluate mathematical calculations, formulas, and conversions via AST.",
    requiresConfirmation: false,
    toolName: "calculator",
    status: "approved",
  },
  "system.diagnostics": {
    name: "system.diagnostics",
    category: "system",
    description: "Retrieve hardware telemetry: CPU %, RAM %, Disk free space, Uptime, Battery.",
    requiresConfirmation: false,
    toolName: "system_diagnostics",
    status: "approved",
  },
  "system.status.check": {
    name: "system.status.check",
    category: "system",
    description: "Check backend service connectivity, latency, and operational health.",
    requiresConfirmation: false,
    status: "approved",
  },

  // 5. Workspace Files
  "files.search": {
    name: "files.search",
    category: "files",
    description: "Search workspace directories for files matching pattern criteria.",
    requiresConfirmation: false,
    toolName: "search_files",
    status: "approved",
  },
  "files.read": {
    name: "files.read",
    category: "files",
    description: "Read file contents within workspace boundary (PDF, TXT, Code, Markdown, CSV, JSON).",
    requiresConfirmation: false,
    toolName: "read_file",
    status: "approved",
  },
  "files.upload": {
    name: "files.upload",
    category: "files",
    description: "Upload and analyze user documents within workspace boundary.",
    requiresConfirmation: false,
    status: "approved",
  },
  "files.write": {
    name: "files.write",
    category: "files",
    description: "Create or overwrite files in workspace (Sensitive: requires user confirmation).",
    requiresConfirmation: true,
    toolName: "write_file",
    status: "requires_confirmation",
  },

  // 6. Desktop Automation
  "desktop.open_application": {
    name: "desktop.open_application",
    category: "desktop",
    description: "Launch allowlisted Windows desktop applications (Calculator, Notepad, File Explorer, VS Code).",
    requiresConfirmation: true,
    toolName: "open_application",
    status: "requires_confirmation",
  },

  // 7. Text-to-Speech (TTS)
  "tts.synthesize": {
    name: "tts.synthesize",
    category: "tts",
    description: "Generate high-fidelity neural audio speech via Edge TTS.",
    requiresConfirmation: false,
    status: "approved",
  },
  "tts.playback": {
    name: "tts.playback",
    category: "tts",
    description: "Play neural audio output through browser AudioContext with visualizer tap.",
    requiresConfirmation: false,
    status: "approved",
  },
  "tts.stop": {
    name: "tts.stop",
    category: "tts",
    description: "Stop and reset active speech audio playback immediately.",
    requiresConfirmation: false,
    status: "approved",
  },
  "tts.interrupt": {
    name: "tts.interrupt",
    category: "tts",
    description: "Instant barge-in speech interruption on detected user vocalization.",
    requiresConfirmation: false,
    status: "approved",
  },

  // 8. Visualizer & UI
  "visualizer.audio_reactive": {
    name: "visualizer.audio_reactive",
    category: "visualizer",
    description: "Drive 3D holographic core and background HUD from live Web Audio DSP telemetry.",
    requiresConfirmation: false,
    status: "approved",
  },
  "visualizer.hud_telemetry": {
    name: "visualizer.hud_telemetry",
    category: "visualizer",
    description: "Render real-time 16-band spectrum equalizer, waveforms, and operational states.",
    requiresConfirmation: false,
    status: "approved",
  },
  "diagnostics.overlay": {
    name: "diagnostics.overlay",
    category: "visualizer",
    description: "Display developer real-time DSP, VAD, STT, and capability authorization telemetry.",
    requiresConfirmation: false,
    status: "approved",
  },
};

export interface DiagnosticEvent {
  capability: string;
  tool?: string;
  approvalStatus: ApprovalStatus;
  authorizationStatus: "GRANTED" | "REQUIRES_CONFIRMATION" | "DENIED";
  executionStatus: "SUCCESS" | "PENDING" | "FAILED" | "IDLE";
  error?: string;
  timestamp: string;
}

class PermissionManager {
  private capabilities: Map<string, CapabilityDto> = new Map();
  private isSynced = false;
  private listeners: Set<() => void> = new Set();
  private latestDiagnostic: DiagnosticEvent = {
    capability: "voice.speech.stream",
    tool: undefined,
    approvalStatus: "approved",
    authorizationStatus: "GRANTED",
    executionStatus: "IDLE",
    timestamp: new Date().toISOString(),
  };

  constructor() {
    // Seed with authoritative defaults
    Object.values(DEFAULT_APPROVED_CAPABILITIES).forEach((cap) => {
      this.capabilities.set(cap.name, cap);
    });
  }

  public subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(): void {
    this.listeners.forEach((listener) => {
      try {
        listener();
      } catch (err) {
        console.error("[PermissionManager] Listener error:", err);
      }
    });
  }

  public async syncWithBackend(): Promise<void> {
    try {
      const items = await fetchCapabilities();
      items.forEach((cap) => {
        this.capabilities.set(cap.name, cap);
      });
      this.isSynced = true;
      this.notify();
    } catch (err) {
      console.warn("[PermissionManager] Backend capability sync warning, using local registry:", err);
    }
  }

  public isBackendSynced(): boolean {
    return this.isSynced;
  }

  public isApproved(capabilityName: string): boolean {
    const cap = this.capabilities.get(capabilityName);
    return cap !== undefined && cap.status !== "denied";
  }

  public requiresConfirmation(capabilityName: string): boolean {
    const cap = this.capabilities.get(capabilityName);
    return cap?.requiresConfirmation ?? false;
  }

  public getStatus(capabilityName: string): ApprovalStatus {
    const cap = this.capabilities.get(capabilityName);
    return cap?.status ?? "unknown";
  }

  public getCapabilityForTool(toolName: string): CapabilityDto | undefined {
    for (const cap of this.capabilities.values()) {
      if (cap.toolName === toolName) return cap;
    }
    return undefined;
  }

  public getAllCapabilities(): CapabilityDto[] {
    return Array.from(this.capabilities.values());
  }

  public getApprovedCount(): number {
    return Array.from(this.capabilities.values()).filter((c) => c.status === "approved").length;
  }

  public getTotalCount(): number {
    return this.capabilities.size;
  }

  public recordDiagnostic(event: Partial<DiagnosticEvent> & { capability: string }): void {
    const cap = this.capabilities.get(event.capability);
    const approvalStatus = event.approvalStatus ?? cap?.status ?? "unknown";
    const authStatus =
      event.authorizationStatus ??
      (cap?.requiresConfirmation ? "REQUIRES_CONFIRMATION" : approvalStatus === "approved" ? "GRANTED" : "DENIED");

    this.latestDiagnostic = {
      capability: event.capability,
      tool: event.tool ?? cap?.toolName,
      approvalStatus,
      authorizationStatus: authStatus,
      executionStatus: event.executionStatus ?? "SUCCESS",
      error: event.error,
      timestamp: new Date().toISOString(),
    };
    this.notify();
  }

  public getLatestDiagnostic(): DiagnosticEvent {
    return this.latestDiagnostic;
  }
}

export const permissionManager = new PermissionManager();

