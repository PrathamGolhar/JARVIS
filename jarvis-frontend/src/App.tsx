import { FormEvent, useEffect, useRef, useState } from "react";
import { AssistantMode, Citation, GeneratedFile, PendingAction, PlanStep, sendChatMessage, ToolEvent } from "./api/chat";
import { fetchVoices, requestSpeech, Voice } from "./api/speech";
import { fetchDiagnostics, DiagnosticItem, SystemMetrics } from "./api/diagnostics";
import { waitForBackend } from "./api/system";

import { AmbientHud } from "./components/AmbientHud";
import { ActivityMonitor } from "./components/ActivityMonitor";
import { SystemStatus } from "./components/SystemStatus";
import { BriefingPanel } from "./components/BriefingPanel";
import { OrbControl } from "./components/OrbControl";
import { CitationsList } from "./components/CitationsList";
import { ActionConfirmationModal } from "./components/ActionConfirmationModal";
import { FileUploadDrawer } from "./components/FileUploadDrawer";
import { DeveloperDiagnosticsOverlay } from "./components/DeveloperDiagnosticsOverlay";
import { StudyModePanel } from "./components/StudyModePanel";
import { GeneratedFilesDrawer } from "./components/GeneratedFilesDrawer";
import { ProjectManagerModal } from "./components/ProjectManagerModal";
import { MemoryInspectorModal } from "./components/MemoryInspectorModal";
import { AutomationModal } from "./components/AutomationModal";
import { SettingsModal } from "./components/SettingsModal";
import { CodeBlock } from "./components/CodeBlock";
import { PlanExecutionIndicator } from "./components/PlanExecutionIndicator";
import { CommandPaletteModal } from "./components/CommandPaletteModal";
import { QuickActionsBar } from "./components/QuickActionsBar";
import { NavigationSidebar, WorkspaceView } from "./components/NavigationSidebar";
import { TopNavigationBar } from "./components/TopNavigationBar";
import { ToastNotificationSystem, showToast } from "./components/ToastNotificationSystem";
import { DashboardWorkspace } from "./components/DashboardWorkspace";
import { ResearchWorkspace } from "./components/ResearchWorkspace";
import { CodeWorkspace } from "./components/CodeWorkspace";
import { IntegrationsWorkspace } from "./components/IntegrationsWorkspace";

import backgroundVideo from "./assets/Futuristic,_cinematic_AI_interface_featuring_20260914215301.mp4";
import { aiVisualController, AssistantState } from "./services/aiVisualController";
import { speechManager, VoiceState } from "./services/speechManager";
import { permissionManager } from "./services/permissionManager";

type Message = {
  author: "user" | "jarvis";
  text: string;
  citations?: Citation[];
  planSteps?: PlanStep[];
  generatedFiles?: GeneratedFile[];
  codeBlocks?: { code: string; language: string }[];
  id: string;
};

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {
    // Silent fallback
  });
}

export function App() {
  const sessionId = useRef(crypto.randomUUID());
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const autoListenTimerRef = useRef<number | null>(null);

  // Core navigation view
  const [currentView, setCurrentView] = useState<WorkspaceView>("core");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);
  const [isFocusMode, setIsFocusMode] = useState(false);

  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<AssistantState>("idle");
  const [activeMode, setActiveMode] = useState<AssistantMode>("general");
  const [activeProjectId, setActiveProjectId] = useState<string | undefined>();
  const [voiceEngineState, setVoiceEngineState] = useState<VoiceState>("IDLE");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [finalTranscript, setFinalTranscript] = useState("");
  const [continuousMode, setContinuousMode] = useState(true);
  const [wakeWordEnabled, setWakeWordEnabled] = useState(true);
  const [activeTool, setActiveTool] = useState<string | undefined>();
  const [recentTools, setRecentTools] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [voices, setVoices] = useState<Voice[]>([]);
  const [voiceId, setVoiceId] = useState("en-US-GuyNeural");

  const [backendStarting, setBackendStarting] = useState(true);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [diagnosticsItems, setDiagnosticsItems] = useState<DiagnosticItem[]>([]);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | undefined>();
  const [isDiagnosticsLoading, setIsDiagnosticsLoading] = useState(false);

  // Modals state
  const [isStudyOpen, setIsStudyOpen] = useState(false);
  const [isFilesOpen, setIsFilesOpen] = useState(false);
  const [isProjectsOpen, setIsProjectsOpen] = useState(false);
  const [isMemoryOpen, setIsMemoryOpen] = useState(false);
  const [isAutomationOpen, setIsAutomationOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isDevDiagnosticsOpen, setIsDevDiagnosticsOpen] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  // Global Ctrl+K Command Palette hotkey
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  const handleCommandPaletteAction = (actionType: string, payload?: any) => {
    if (actionType === 'mode') {
      if (payload === 'study') {
        setIsStudyOpen(true);
      } else if (payload === 'research') {
        setCurrentView('research');
        setActiveMode('research');
      } else if (payload === 'coding') {
        setCurrentView('coding');
        setActiveMode('coding');
      } else {
        setActiveMode(payload as AssistantMode);
        setCurrentView('core');
      }
    } else if (actionType === 'modal') {
      if (payload === 'memory') setIsMemoryOpen(true);
      else if (payload === 'diagnostics') setIsDevDiagnosticsOpen(true);
      else if (payload === 'projects') setIsProjectsOpen(true);
      else if (payload === 'settings') setIsSettingsOpen(true);
      else if (payload === 'files') setIsFilesOpen(true);
      else if (payload === 'automation') setIsAutomationOpen(true);
    } else if (actionType === 'generate') {
      if (payload === 'pdf') {
        setInput('Generate a comprehensive PDF report on our current project topics.');
        setCurrentView('core');
      } else if (payload === 'pptx') {
        setInput('Generate a 16:9 PowerPoint presentation deck on this topic.');
        setCurrentView('core');
      }
    } else if (actionType === 'voice') {
      if (status === 'speaking') stopSpeech();
      else void startListening();
    }
  };

  const handleSelectView = (view: WorkspaceView) => {
    if (view === 'projects') {
      setIsProjectsOpen(true);
    } else if (view === 'files') {
      setIsFilesOpen(true);
    } else if (view === 'study') {
      setIsStudyOpen(true);
    } else if (view === 'memory') {
      setIsMemoryOpen(true);
    } else if (view === 'automation') {
      setIsAutomationOpen(true);
    } else if (view === 'settings') {
      setIsSettingsOpen(true);
    } else if (view === 'diagnostics') {
      setIsDevDiagnosticsOpen(true);
    } else {
      setCurrentView(view);
    }
  };

  // Sync state to central AI visual controller
  useEffect(() => {
    aiVisualController.setState(status);
  }, [status]);

  // Initial load & diagnostics
  const refreshDiagnostics = async () => {
    setIsDiagnosticsLoading(true);
    try {
      const data = await fetchDiagnostics();
      setDiagnosticsItems(data.items);
      setSystemMetrics(data.systemMetrics);
    } catch {
      // Offline
    } finally {
      setIsDiagnosticsLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const healthy = await waitForBackend();
      if (cancelled) return;
      setBackendStarting(false);
      if (!healthy) {
        setError("JARVIS backend is offline. Verify Python server is running on port 8765.");
        showToast({
          title: "Core Disconnected",
          message: "Could not reach FastAPI backend on port 8765.",
          type: "error",
        });
        return;
      }

      showToast({
        title: "JARVIS 2.0 Core Online",
        message: "Autonomous multi-agent orchestration ready.",
        type: "cyber",
      });

      await refreshDiagnostics();
      await speechManager.checkAvailability();
      await permissionManager.syncWithBackend();

      try {
        const items = await fetchVoices();
        if (cancelled) return;
        setVoices(items);
        if (!items.some((item) => item.id === voiceId)) {
          setVoiceId(items[0]?.id ?? voiceId);
        }
      } catch {
        if (!cancelled) setError("Edge voice synthesis unavailable. Text interaction is online.");
      }
    })();

    const pollInterval = window.setInterval(() => {
      void refreshDiagnostics();
    }, 25_000);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && (e.key === "D" || e.key === "d")) {
        e.preventDefault();
        setIsDevDiagnosticsOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      cancelled = true;
      window.clearInterval(pollInterval);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  useEffect(() => () => {
    stopSpeech();
    speechManager.cancelListening();
    if (autoListenTimerRef.current !== null) {
      clearTimeout(autoListenTimerRef.current);
    }
  }, []);

  useEffect(() => {
    requestAnimationFrame(() => {
      messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: "smooth" });
    });
  }, [messages, status, pendingAction, interimTranscript]);

  function stopSpeech() {
    aiVisualController.stopSpeechSimulation();
    aiVisualController.disconnectTTS();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    if (autoListenTimerRef.current !== null) {
      clearTimeout(autoListenTimerRef.current);
      autoListenTimerRef.current = null;
    }
  }

  async function playSpeech(text: string) {
    try {
      stopSpeech();
      // Clean markdown code blocks from speech output
      const cleanSpokenText = text.replace(/```[\s\S]*?```/g, "Code block provided in terminal.").replace(/[#*`_]/g, "");
      const url = URL.createObjectURL(await requestSpeech(cleanSpokenText, voiceId));
      const audio = new Audio(url);
      audio.crossOrigin = "anonymous";

      aiVisualController.connectTTSAudio(audio);
      audioRef.current = audio;
      audioUrlRef.current = url;

      audio.onended = () => {
        if (audioUrlRef.current === url) URL.revokeObjectURL(url);
        aiVisualController.disconnectTTS();
        setStatus("idle");
        speechManager.setVoiceState("IDLE");

        if (continuousMode) {
          autoListenTimerRef.current = window.setTimeout(() => {
            autoListenTimerRef.current = null;
            void startListening();
          }, 450);
        }
      };

      await audio.play();
      setStatus("speaking");
      speechManager.setVoiceState("SPEAKING");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Speech playback unavailable.");
      setStatus("idle");
      speechManager.setVoiceState("IDLE");
    }
  }

  function extractCodeBlocks(text: string): { code: string; language: string }[] {
    const blocks: { code: string; language: string }[] = [];
    const regex = /```([a-zA-Z0-9_\-+]*)\n([\s\S]*?)```/g;
    let match;
    while ((match = regex.exec(text)) !== null) {
      blocks.push({
        language: match[1] || "python",
        code: match[2].trim(),
      });
    }
    return blocks;
  }

  async function askJarvis(text: string, confirmedActionId?: string) {
    stopSpeech();
    setInterimTranscript("");
    setFinalTranscript(text);
    setError("");
    setPendingAction(null);

    if (!confirmedActionId) {
      setMessages((current) => [...current, { author: "user", text, id: crypto.randomUUID() }]);
    }

    setStatus("thinking");
    speechManager.setVoiceState("PROCESSING");
    permissionManager.recordDiagnostic({ capability: "ai.response.generate", executionStatus: "PENDING" });

    try {
      const result = await sendChatMessage({
        sessionId: sessionId.current,
        text,
        mode: activeMode,
        projectId: activeProjectId,
        confirmedActionId,
      });

      if (result.toolEvents && result.toolEvents.length > 0) {
        const toolsUsed = result.toolEvents.map((t: ToolEvent) => t.toolName);
        setRecentTools((prev) => [...prev, ...toolsUsed]);

        if (toolsUsed.includes("web_search") || toolsUsed.includes("read_webpage")) {
          setStatus("searching");
          setActiveTool("web_search");
        } else {
          setStatus("executing");
          setActiveTool(toolsUsed[0]);
        }
      } else {
        permissionManager.recordDiagnostic({ capability: "ai.response.generate", executionStatus: "SUCCESS" });
      }

      const extractedCodes = extractCodeBlocks(result.reply);

      setMessages((current) => [
        ...current,
        {
          author: "jarvis",
          text: result.reply,
          citations: result.citations && result.citations.length > 0 ? result.citations : undefined,
          planSteps: result.planSteps && result.planSteps.length > 0 ? result.planSteps : undefined,
          generatedFiles: result.generatedFiles && result.generatedFiles.length > 0 ? result.generatedFiles : undefined,
          codeBlocks: extractedCodes.length > 0 ? extractedCodes : undefined,
          id: crypto.randomUUID(),
        },
      ]);

      if (result.pendingAction) {
        setPendingAction(result.pendingAction);
        setStatus("idle");
        speechManager.setVoiceState("IDLE");
      } else {
        void playSpeech(result.reply);
      }
    } catch (reason) {
      const msg = reason instanceof Error ? reason.message : "JARVIS could not process the request.";
      setError(msg);
      setStatus("error");
      speechManager.setVoiceState("ERROR_RECOVERY");
      showToast({
        title: "Execution Error",
        message: msg,
        type: "error",
      });
    }
  }

  async function handleConfirmAction(actionId: string) {
    setPendingAction(null);
    await askJarvis("Authorization granted. Execute action.", actionId);
  }

  function handleCancelAction() {
    setPendingAction(null);
    const reply = "Action authorization cancelled, Master.";
    setMessages((current) => [...current, { author: "jarvis", text: reply, id: crypto.randomUUID() }]);
    setStatus("idle");
    void playSpeech(reply);
  }

  function handleFileUploadSuccess(filename: string, preview: string) {
    showToast({
      title: "File Ingested",
      message: `${filename} processed into workspace context.`,
      type: "success",
    });
    const prompt = `I have uploaded '${filename}'. Read and analyze this document thoroughly:\n\n${preview}`;
    void askJarvis(prompt);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || status === "thinking" || backendStarting) return;
    setInput("");
    await askJarvis(text);
  }

  async function startListening() {
    if (status === "thinking" || backendStarting) return;
    stopSpeech();
    setError("");
    setInterimTranscript("");
    setStatus("listening");

    await speechManager.startListening({
      mode: continuousMode ? "continuous" : "push-to-talk",
      onSpeechStart: () => {
        stopSpeech();
      },
      onInterimTranscript: (interim) => {
        setInterimTranscript(interim);
      },
      onFinalTranscript: (final) => {
        setInterimTranscript("");
        void askJarvis(final);
      },
      onError: (userMessage) => {
        setInterimTranscript("");
        setError(userMessage);
        setStatus("error");
      },
      onStateChange: (state) => {
        setVoiceEngineState(state);
      },
    });
  }

  function finishListening() {
    void speechManager.stopListening();
  }

  const stateLabel = backendStarting
    ? "INITIALIZING JARVIS ORCHESTRATOR"
    : status === "listening"
    ? "LISTENING / AUDIO VAD ACTIVE"
    : status === "thinking"
    ? "ORCHESTRATING AUTONOMOUS PLAN"
    : status === "searching"
    ? "SEARCHING LIVE CITATIONS"
    : status === "executing"
    ? "EXECUTING SYSTEM WORKFLOW"
    : status === "speaking"
    ? "SYNTHESIZING NEURAL SPEECH"
    : "JARVIS ONLINE & READY";

  const recentCommands = messages.filter((message) => message.author === "user").map((message) => message.text).slice(-4).reverse();
  const isBusy = status === "thinking" || status === "searching" || status === "executing" || backendStarting;

  return (
    <main className="app-shell flex flex-col h-screen w-screen overflow-hidden select-none">
      <video className="background-video" autoPlay muted loop playsInline preload="auto" aria-hidden="true">
        <source src={backgroundVideo} type="video/mp4" />
      </video>

      {/* Synchronized Background AI HUD */}
      <AmbientHud />

      {backendStarting && (
        <div className="boot-overlay" role="status" aria-live="polite">
          <div className="boot-core" aria-hidden="true" />
          <p className="boot-kicker">JARVIS OPERATING SYSTEM</p>
          <h2>Initializing core</h2>
          <p className="boot-sub">Linking orchestrator · audio · telemetry</p>
        </div>
      )}

      {/* Top Futuristic Navigation Bar */}
      <TopNavigationBar
        systemStatus={backendStarting ? "degraded" : error ? "degraded" : "online"}
        activeMode={activeMode}
        onChangeMode={(m) => {
          setActiveMode(m);
          if (m === "study") setIsStudyOpen(true);
          else if (m === "research") setCurrentView("research");
          else if (m === "coding") setCurrentView("coding");
        }}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        onToggleFocusMode={() => setIsFocusMode((prev) => !prev)}
        isFocusMode={isFocusMode}
        onOpenNotifications={() => setIsDevDiagnosticsOpen(true)}
      />

      {/* Main Workspace Frame */}
      <div className="flex-1 flex overflow-hidden relative z-10">
        {/* Navigation Sidebar */}
        <NavigationSidebar
          currentView={currentView}
          onSelectView={handleSelectView}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
          activeProjectName={activeProjectId ? "Active" : undefined}
          isListening={status === "listening"}
        />

        {/* Dynamic Workspace Content */}
        <div className="workspace-stage flex-1 flex overflow-hidden relative">
          {currentView === "dashboard" && (
            <DashboardWorkspace
              onNavigate={handleSelectView}
              activeProjectId={activeProjectId}
              onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
            />
          )}

          {currentView === "research" && <ResearchWorkspace />}

          {currentView === "coding" && <CodeWorkspace />}

          {currentView === "integrations" && <IntegrationsWorkspace />}

          {currentView === "core" && (
            <div className={`command-center ${isFocusMode ? "is-focus" : ""}`}>
              {!isFocusMode && (
                <div className="cc-rail cc-rail-left">
                  <SystemStatus
                    items={diagnosticsItems}
                    metrics={systemMetrics}
                    onRefresh={() => void refreshDiagnostics()}
                    isLoading={isDiagnosticsLoading}
                  />
                  <ActivityMonitor
                    state={status}
                    activeTool={activeTool}
                    recentTools={recentTools}
                    recentCommands={recentCommands}
                  />
                </div>
              )}

              <div className="cc-core">
                <OrbControl
                  disabled={status === "thinking" || backendStarting}
                  state={status}
                  onStart={() => {
                    if (status === "speaking") stopSpeech();
                    void startListening();
                  }}
                  onStop={() => {
                    if (!continuousMode) finishListening();
                  }}
                />
                <p className="cc-core-status">{stateLabel}</p>
              </div>

              {!isFocusMode && (
                <div className="cc-briefing">
                  <BriefingPanel />
                </div>
              )}

              <section className="chat-card cc-console" aria-label="JARVIS Assistant">
              <div className="chat-header-row">
                  <div>
                    <p className="jarvis-brand">JARVIS // {activeMode.toUpperCase()}</p>
                    <h1>Command console</h1>
                  </div>
                  <div className="chat-header-actions">
                    <button
                      type="button"
                      className={`hud-mode-toggle-btn ${continuousMode ? "is-active" : ""}`}
                      onClick={() => setContinuousMode((prev) => !prev)}
                      title="Toggle hands-free continuous voice mode"
                      aria-pressed={continuousMode}
                    >
                      {continuousMode ? "AUTO-LISTEN" : "PUSH-TO-TALK"}
                    </button>
                    {messages.length > 0 && (
                      <button
                        type="button"
                        className="hud-diag-toggle-btn"
                        onClick={() => {
                          if (window.confirm("Clear all messages?")) {
                            setMessages([]);
                            setError("");
                          }
                        }}
                        title="Clear conversation"
                        aria-label="Clear conversation history"
                      >
                        CLEAR
                      </button>
                    )}
                    <button
                      type="button"
                      className="hud-diag-toggle-btn"
                      onClick={() => setIsDevDiagnosticsOpen((prev) => !prev)}
                      title="Toggle audio DSP diagnostics (Ctrl+Shift+D)"
                      aria-label="Toggle developer diagnostics panel"
                      aria-pressed={isDevDiagnosticsOpen}
                    >
                      {isDevDiagnosticsOpen ? "DSP ON" : "DSP"}
                    </button>
                  </div>
                </div>

                <div className="messages" ref={messagesRef} aria-live="polite">
                  {messages.length === 0 && !pendingAction && !interimTranscript && !isBusy && (
                    <div className="chat-placeholder">
                      <p>Speak, type, or attach a file to begin.</p>
                      <p style={{ marginTop: '0.5rem', fontSize: '10px', opacity: 0.7 }}>JARVIS can research, study, write code, generate PDFs, and execute system tasks.</p>
                    </div>
                  )}

                  {messages.map((message, index) => (
                    <div className={`message-wrapper ${message.author}`} key={message.id ?? `${message.author}-${index}`}>
                      {message.planSteps && message.planSteps.length > 0 && (
                        <PlanExecutionIndicator steps={message.planSteps} />
                      )}

                      <div className="message-bubble-wrapper">
                        <p className={`message ${message.author}`}>{message.text}</p>
                        {message.author === "jarvis" && (
                          <button
                            type="button"
                            className="msg-copy-btn"
                            onClick={() => copyToClipboard(message.text)}
                            aria-label="Copy message to clipboard"
                            title="Copy to clipboard"
                          >
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                              <rect width="14" height="14" x="8" y="8" rx="2" />
                              <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
                            </svg>
                          </button>
                        )}
                      </div>

                      {message.codeBlocks && message.codeBlocks.map((cb, cbIdx) => (
                        <CodeBlock key={cbIdx} code={cb.code} language={cb.language} />
                      ))}

                      {message.generatedFiles && message.generatedFiles.length > 0 && (
                        <div className="delivered-files">
                          <span className="delivered-files-label">Delivered documents</span>
                          {message.generatedFiles.map((gf) => (
                            <div key={gf.id} className="delivered-file-row">
                              <span>{gf.filename}</span>
                              <a href={gf.downloadUrl} download={gf.filename} target="_blank" rel="noreferrer" className="hud-action-link">
                                Download
                              </a>
                            </div>
                          ))}
                        </div>
                      )}

                      {message.citations && <CitationsList citations={message.citations} />}
                    </div>
                  ))}

                  {interimTranscript && (
                    <div className="message-wrapper user streaming-transcript">
                      <p className="message user interim-bubble">
                        <span className="streaming-pulse" /> {interimTranscript}
                      </p>
                    </div>
                  )}

                  {status === "thinking" && (
                    <p className="message jarvis processing-line">
                      <span className="hud-spinner" aria-hidden="true" /> Constructing plan…
                    </p>
                  )}
                  {status === "searching" && (
                    <p className="message jarvis processing-line">
                      <span className="hud-spinner" aria-hidden="true" /> Searching verified sources…
                    </p>
                  )}
                  {status === "executing" && (
                    <p className="message jarvis processing-line">
                      <span className="hud-spinner" aria-hidden="true" /> Executing authorized tools…
                    </p>
                  )}

                  {pendingAction && (
                    <ActionConfirmationModal
                      pendingAction={pendingAction}
                      onConfirm={(id) => void handleConfirmAction(id)}
                      onCancel={handleCancelAction}
                    />
                  )}
                </div>

                <button
                  className={`talk-button ${status === "listening" ? "is-listening" : ""}`}
                  type="button"
                  onPointerDown={(event) => {
                    if (status === "speaking") stopSpeech();
                    if (!continuousMode) event.currentTarget.setPointerCapture(event.pointerId);
                    void startListening();
                  }}
                  onPointerUp={() => {
                    if (!continuousMode) finishListening();
                  }}
                  onPointerCancel={() => {
                    if (!continuousMode) finishListening();
                  }}
                  disabled={status === "thinking" || backendStarting}
                >
                  {status === "listening"
                    ? continuousMode
                      ? "Listening — continuous"
                      : "Listening — release to send"
                    : status === "speaking"
                    ? "Speaking — click to interrupt"
                    : backendStarting
                    ? "Connecting to core…"
                    : continuousMode
                    ? "Start voice link"
                    : "Hold to talk"}
                </button>

                <div className="mb-2">
                  <QuickActionsBar
                    onSelectAction={handleCommandPaletteAction}
                    onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
                  />
                </div>

                <div className="composer-container">
                  <FileUploadDrawer
                    sessionId={sessionId.current}
                    onUploadSuccess={handleFileUploadSuccess}
                    onError={(err) => setError(err)}
                  />

                  <form onSubmit={handleSubmit} noValidate className="composer">
                    <label className="sr-only" htmlFor="chat-input">
                      Message JARVIS
                    </label>
                    <input
                      id="chat-input"
                      value={input}
                      maxLength={5000}
                      onChange={(event) => setInput(event.target.value)}
                      placeholder="Issue a command…"
                      disabled={status === "thinking" || backendStarting}
                    />
                    <button type="submit" disabled={!input.trim() || status === "thinking" || backendStarting}>
                      Send
                    </button>
                  </form>
                </div>

                <label className="voice-picker sr-only" htmlFor="voice-select">
                  Voice synthesis
                  <select id="voice-select" value={voiceId} onChange={(event) => setVoiceId(event.target.value)} disabled={!voices.length} tabIndex={-1} aria-hidden="true">
                    {voices.map((voice) => (
                      <option key={voice.id} value={voice.id}>
                        {voice.label}
                      </option>
                    ))}
                  </select>
                </label>

                {error && (
                  <p className="error" role="alert">
                    {error}
                  </p>
                )}
              </section>
            </div>
          )}
        </div>
      </div>

      {/* Global Toast Notification Overlay */}
      <ToastNotificationSystem />

      {/* Modals & Overlays */}
      {isStudyOpen && <StudyModePanel onClose={() => setIsStudyOpen(false)} />}
      {isFilesOpen && <GeneratedFilesDrawer onClose={() => setIsFilesOpen(false)} />}
      {isProjectsOpen && (
        <ProjectManagerModal
          activeProjectId={activeProjectId}
          onSelectProject={(id) => setActiveProjectId(id)}
          onClose={() => setIsProjectsOpen(false)}
        />
      )}
      {isMemoryOpen && <MemoryInspectorModal onClose={() => setIsMemoryOpen(false)} />}
      {isAutomationOpen && <AutomationModal onClose={() => setIsAutomationOpen(false)} />}
      {isSettingsOpen && (
        <SettingsModal
          voices={voices}
          selectedVoiceId={voiceId}
          onSelectVoice={(id) => setVoiceId(id)}
          wakeWordEnabled={wakeWordEnabled}
          onToggleWakeWord={(en) => setWakeWordEnabled(en)}
          onClose={() => setIsSettingsOpen(false)}
        />
      )}

      {/* Developer Real-Time DSP Diagnostics Overlay */}
      <DeveloperDiagnosticsOverlay
        isOpen={isDevDiagnosticsOpen}
        onClose={() => setIsDevDiagnosticsOpen(false)}
        interimTranscript={interimTranscript}
        finalTranscript={finalTranscript}
        voiceState={voiceEngineState}
      />

      {/* Command Palette (Ctrl+K) */}
      <CommandPaletteModal
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectAction={handleCommandPaletteAction}
      />
    </main>
  );
}
