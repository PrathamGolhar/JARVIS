import { useEffect, useState } from "react";
import { aiVisualController, AIVisualState } from "../services/aiVisualController";
import { speechManager, VoiceState } from "../services/speechManager";
import { permissionManager, DiagnosticEvent } from "../services/permissionManager";

type DeveloperDiagnosticsOverlayProps = {
  isOpen: boolean;
  onClose: () => void;
  interimTranscript?: string;
  finalTranscript?: string;
  voiceState?: VoiceState;
};

export function DeveloperDiagnosticsOverlay({
  isOpen,
  onClose,
  interimTranscript = "",
  finalTranscript = "",
  voiceState = "IDLE",
}: DeveloperDiagnosticsOverlayProps) {
  const [visualState, setVisualState] = useState<AIVisualState | null>(null);
  const [diagnostic, setDiagnostic] = useState<DiagnosticEvent>(permissionManager.getLatestDiagnostic());
  const [approvedCount, setApprovedCount] = useState(permissionManager.getApprovedCount());
  const [totalCount, setTotalCount] = useState(permissionManager.getTotalCount());
  const [isSynced, setIsSynced] = useState(permissionManager.isBackendSynced());

  useEffect(() => {
    if (!isOpen) return;

    const unsubscribeVisual = aiVisualController.subscribe((state) => {
      setVisualState(state);
    });

    const unsubscribePermissions = permissionManager.subscribe(() => {
      setDiagnostic(permissionManager.getLatestDiagnostic());
      setApprovedCount(permissionManager.getApprovedCount());
      setTotalCount(permissionManager.getTotalCount());
      setIsSynced(permissionManager.isBackendSynced());
    });

    return () => {
      unsubscribeVisual();
      unsubscribePermissions();
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const amp = visualState?.amplitude?.toFixed(3) ?? "0.000";
  const rawAmp = visualState?.rawAmplitude?.toFixed(3) ?? "0.000";
  const pitchHz = visualState?.pitchHz ?? 0;
  const pitchCentroid = visualState?.pitch?.toFixed(3) ?? "0.000";
  const bass = visualState?.bass?.toFixed(3) ?? "0.000";
  const mid = visualState?.mid?.toFixed(3) ?? "0.000";
  const high = visualState?.high?.toFixed(3) ?? "0.000";
  const emphasis = visualState?.emphasis?.toFixed(3) ?? "0.000";
  const isSpeaking = visualState?.isSpeaking ? "VOICE ACTIVE" : "SILENCE";
  const operationalState = visualState?.state?.toUpperCase() ?? "IDLE";
  const source = visualState?.source?.toUpperCase() ?? "IDLE";
  const scale = visualState?.scale?.toFixed(3) ?? "1.000";
  const glow = visualState?.glow?.toFixed(3) ?? "0.400";
  const rotation = visualState?.rotationSpeed?.toFixed(3) ?? "0.400";
  const deformation = visualState?.waveDeformation?.toFixed(3) ?? "0.000";

  const sttStatus = speechManager.getStatus();
  const sttProvider = speechManager.getActiveProvider();
  const sttError = speechManager.getLastError();
  const retryCount = speechManager.getRetryCount();
  const networkStatus = navigator.onLine ? "ONLINE" : "OFFLINE";

  let vadStateClass = "";
  if (voiceState === "VOICE_DETECTED" || voiceState === "TRANSCRIBING") {
    vadStateClass = "is-active";
  } else if (voiceState === "SHORT_PAUSE" || voiceState === "WAITING_FOR_END_OF_SPEECH") {
    vadStateClass = "is-paused";
  }

  return (
    <div className="dev-diagnostics-overlay" role="dialog" aria-label="Developer Diagnostics">
      <div className="dev-diag-header">
        <div>
          <span className="dev-diag-title">JARVIS DSP & CAPABILITY DIAGNOSTICS</span>
          <small className="dev-diag-shortcut">[Ctrl + Shift + D]</small>
        </div>
        <button type="button" className="dev-diag-close-btn" onClick={onClose} title="Close Diagnostics">
          ✕
        </button>
      </div>

      <div className="dev-diag-grid">
        {/* Section 1: Audio Signal Analysis */}
        <div className="dev-diag-card">
          <h4>AUDIO DSP SIGNAL</h4>
          <div className="dev-diag-row">
            <span>RMS Amplitude:</span>
            <strong>{rawAmp} (Smooth: {amp})</strong>
          </div>
          <div className="dev-diag-row">
            <span>Spectral Centroid:</span>
            <strong>{pitchCentroid} (~{pitchHz} Hz)</strong>
          </div>
          <div className="dev-diag-row">
            <span>Low Band (Bass):</span>
            <strong>{bass}</strong>
          </div>
          <div className="dev-diag-row">
            <span>Mid Band (Vowels):</span>
            <strong>{mid}</strong>
          </div>
          <div className="dev-diag-row">
            <span>High Band (Air):</span>
            <strong>{high}</strong>
          </div>
          <div className="dev-diag-row">
            <span>Transient Emphasis:</span>
            <strong>{emphasis}</strong>
          </div>
          <div className="dev-diag-row">
            <span>Audio Tap Source:</span>
            <strong>{source}</strong>
          </div>
        </div>

        {/* Section 2: Speech & VAD Engine */}
        <div className="dev-diag-card">
          <h4>VOICE ENGINE & STT PROVIDER</h4>
          <div className="dev-diag-row">
            <span>Active STT Provider:</span>
            <strong>{sttProvider.toUpperCase()}</strong>
          </div>
          <div className="dev-diag-row">
            <span>STT Service State:</span>
            <strong className={sttStatus === "STT_READY" ? "is-active" : ""}>{sttStatus}</strong>
          </div>
          <div className="dev-diag-row">
            <span>Voice State Machine:</span>
            <strong className={vadStateClass}>{voiceState}</strong>
          </div>
          <div className="dev-diag-row">
            <span>Voice Activity (VAD):</span>
            <strong className={visualState?.isSpeaking ? "is-active" : ""}>{isSpeaking}</strong>
          </div>
          <div className="dev-diag-row">
            <span>Assistant State:</span>
            <strong>{operationalState}</strong>
          </div>
          <div className="dev-diag-row">
            <span>Network Link:</span>
            <strong className={networkStatus === "ONLINE" ? "is-active" : ""}>{networkStatus}</strong>
          </div>
          {retryCount > 0 && (
            <div className="dev-diag-row">
              <span>Retry Attempts:</span>
              <strong>{retryCount}</strong>
            </div>
          )}
          {sttError && (
            <div className="dev-diag-row">
              <span>Last Error:</span>
              <strong style={{ color: "var(--danger)" }}>{sttError}</strong>
            </div>
          )}
          <div className="dev-diag-transcript-box">
            <span className="transcript-label">STREAMING INTERIM TRANSCRIPT:</span>
            <p className="transcript-preview">
              {interimTranscript || <em className="dim-text">No active speech input...</em>}
            </p>
          </div>
          {finalTranscript && (
            <div className="dev-diag-transcript-box">
              <span className="transcript-label">LAST FINAL TRANSCRIPT:</span>
              <p className="transcript-preview">{finalTranscript}</p>
            </div>
          )}
        </div>

        {/* Section 3: Capability & Authorization Registry */}
        <div className="dev-diag-card">
          <h4>CAPABILITY & AUTHORIZATION STATUS</h4>
          <div className="dev-diag-row">
            <span>Approved Capabilities:</span>
            <strong className="is-active">{approvedCount} / {totalCount} Active</strong>
          </div>
          <div className="dev-diag-row">
            <span>Allowlist Sync:</span>
            <strong className={isSynced ? "is-active" : ""}>{isSynced ? "BACKEND SYNCED" : "LOCAL REGISTRY"}</strong>
          </div>
          <div className="dev-diag-row">
            <span>Requested Capability:</span>
            <strong>{diagnostic.capability}</strong>
          </div>
          <div className="dev-diag-row">
            <span>Mapped Tool:</span>
            <strong>{diagnostic.tool ?? "NONE"}</strong>
          </div>
          <div className="dev-diag-row">
            <span>Approval Status:</span>
            <strong className={diagnostic.approvalStatus === "approved" ? "is-active" : ""}>
              {diagnostic.approvalStatus.toUpperCase()}
            </strong>
          </div>
          <div className="dev-diag-row">
            <span>Authorization:</span>
            <strong className={diagnostic.authorizationStatus === "GRANTED" ? "is-active" : "is-paused"}>
              {diagnostic.authorizationStatus}
            </strong>
          </div>
          <div className="dev-diag-row">
            <span>Execution Status:</span>
            <strong>{diagnostic.executionStatus}</strong>
          </div>
          {diagnostic.error && (
            <div className="dev-diag-row">
              <span>Diag Error:</span>
              <strong style={{ color: "var(--danger)" }}>{diagnostic.error}</strong>
            </div>
          )}
        </div>

        {/* Section 4: Visualizer Harmonics */}
        <div className="dev-diag-card">
          <h4>VISUAL ENGINE HARMONICS</h4>
          <div className="dev-diag-row">
            <span>Core Scale Factor:</span>
            <strong>{scale}x</strong>
          </div>
          <div className="dev-diag-row">
            <span>Fresnel Luminous Glow:</span>
            <strong>{glow}</strong>
          </div>
          <div className="dev-diag-row">
            <span>Rotation Velocity:</span>
            <strong>{rotation} rad/s</strong>
          </div>
          <div className="dev-diag-row">
            <span>Wave Displacement:</span>
            <strong>{deformation}</strong>
          </div>
        </div>
      </div>
    </div>
  );
}

