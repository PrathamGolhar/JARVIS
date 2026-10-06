import { HolographicGlobe } from "./HolographicGlobe";
import { VoiceWaveform } from "./VoiceWaveform";
import { AssistantState } from "../services/aiVisualController";

type OrbControlProps = {
  disabled: boolean;
  onStart: () => void;
  onStop: () => void;
  state: AssistantState;
};

export function OrbControl({ disabled, onStart, onStop, state }: OrbControlProps) {
  const label =
    state === "listening"
      ? "Listening. Release to send"
      : state === "thinking"
      ? "Orchestrating plan"
      : state === "searching"
      ? "Searching live web"
      : state === "executing"
      ? "Executing subsystem action"
      : state === "speaking"
      ? "JARVIS is speaking. Click to interrupt"
      : "Hold to talk with JARVIS";

  const statusLabel =
    state === "listening"
      ? "VOICE LINK OPEN"
      : state === "thinking"
      ? "NEURAL REASONING"
      : state === "searching"
      ? "LIVE RESEARCH"
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
      disabled={disabled}
      onPointerDown={(event) => {
        event.currentTarget.setPointerCapture(event.pointerId);
        onStart();
      }}
      onPointerUp={onStop}
      onPointerCancel={onStop}
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
