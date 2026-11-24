import { HolographicGlobe } from "./HolographicGlobe";
import { VoiceWaveform } from "./VoiceWaveform";
import { AssistantState } from "../services/aiVisualController";

type OrbControlProps = {
  disabled: boolean;
  onActivate: () => void;
  state: AssistantState;
};

export function OrbControl({ disabled, onActivate, state }: OrbControlProps) {
  const label =
    state === "connecting"
      ? "Requesting microphone access. Activate to cancel"
      : state === "listening"
      ? "Voice input active. Activate to stop or send"
      : state === "transcribing"
      ? "Finalizing voice input"
      : state === "understanding"
      ? "Understanding request"
      : state === "thinking"
      ? "Processing request"
      : state === "confirmation"
      ? "Waiting for your confirmation"
      : state === "searching"
      ? "Searching sources"
      : state === "executing"
      ? "Executing requested tools"
      : state === "speaking"
      ? "JARVIS is speaking. Click to interrupt"
      : "Activate to start voice input";

  const statusLabel =
    state === "connecting"
      ? "MICROPHONE ACCESS"
      : state === "listening"
      ? "VOICE INPUT ACTIVE"
      : state === "transcribing"
      ? "TRANSCRIBING"
      : state === "understanding"
      ? "UNDERSTANDING"
      : state === "thinking"
      ? "PROCESSING REQUEST"
      : state === "confirmation"
      ? "CONFIRMATION REQUIRED"
      : state === "searching"
      ? "SOURCE SEARCH"
      : state === "executing"
      ? "TOOL DISPATCH"
      : state === "speaking"
      ? "NEURAL SYNTHESIS"
      : state === "error"
      ? "ATTENTION REQUIRED"
      : "AWAITING COMMAND";

  return (
    <button
      type="button"
      className={`orb-control state-${state}`}
      aria-label={label}
      aria-pressed={state === "listening" || state === "connecting"}
      disabled={disabled}
      onClick={onActivate}
    >
      <div className="orb-ring orb-ring-slow" aria-hidden="true" />
      <div className="orb-ring orb-ring-mid" aria-hidden="true" />
      <div className="orb-ring orb-ring-fast" aria-hidden="true" />
      <VoiceWaveform />
      <div className="orb-hologram-wrapper" aria-hidden="true">
        <HolographicGlobe size={300} />
      </div>
      <div className="orb-hud-overlay" aria-hidden="true">
        <span className="orb-crosshair top-left" />
        <span className="orb-crosshair top-right" />
        <span className="orb-crosshair bottom-left" />
        <span className="orb-crosshair bottom-right" />
        <span className="orb-status-text">{statusLabel}</span>
      </div>
    </button>
  );
}
