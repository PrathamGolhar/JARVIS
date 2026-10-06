import { AssistantState } from "../services/aiVisualController";

type ActivityMonitorProps = {
  state: AssistantState;
  activeTool?: string;
  recentTools?: string[];
  recentCommands?: string[];
};

const activityDetails: Record<AssistantState, { label: string; defaultEntries: string[] }> = {
  idle: {
    label: "STANDING BY",
    defaultEntries: ["CORE SYSTEMS OPTIMAL", "VOICE LINK ARMED", "AWAITING COMMAND"],
  },
  listening: {
    label: "VOICE CAPTURE",
    defaultEntries: ["MICROPHONE STREAM ACTIVE", "DSP TRACKING", "LIVE TRANSCRIPT"],
  },
  transcribing: {
    label: "TRANSCRIBING",
    defaultEntries: ["SPEECH PARSE", "VAD LOCKED", "FINALIZING"],
  },
  understanding: {
    label: "UNDERSTANDING",
    defaultEntries: ["INTENT PARSE", "CONTEXT LOAD", "PROMPT DISPATCH"],
  },
  thinking: {
    label: "ORCHESTRATING",
    defaultEntries: ["PLAN CONSTRUCTION", "MODEL ROUTING", "DAG PREP"],
  },
  searching: {
    label: "WEB RESEARCH",
    defaultEntries: ["LIVE SEARCH", "SOURCE PARSE", "CITATION CHECK"],
  },
  executing: {
    label: "TOOL EXECUTION",
    defaultEntries: ["ACTION DISPATCH", "SANDBOX VERIFY", "AWAITING RESULT"],
  },
  speaking: {
    label: "SYNTHESIZING",
    defaultEntries: ["NEURAL AUDIO", "WAVEFORM LOCK", "OUTPUT STREAM"],
  },
  error: {
    label: "ATTENTION REQUIRED",
    defaultEntries: ["SUBSYSTEM ALERT", "DIAGNOSTIC LOGGED", "STANDBY"],
  },
};

export function ActivityMonitor({ state, activeTool, recentTools = [], recentCommands = [] }: ActivityMonitorProps) {
  const current = activityDetails[state] || activityDetails.idle;

  const displayEntries = activeTool
    ? [`ACTIVE: ${activeTool.toUpperCase()}`, ...recentTools.slice(-2).map((t) => `RECENT: ${t.toUpperCase()}`)]
    : recentTools.length > 0
    ? recentTools.slice(-3).map((t) => `DONE: ${t.toUpperCase()}`)
    : current.defaultEntries;

  return (
    <aside className={`activity-monitor state-${state}`} aria-label="AI activity">
      <div className="monitor-heading">
        <span>AI ACTIVITY</span>
        <i aria-hidden="true" />
      </div>
      <strong className="activity-live-label">{current.label}</strong>
      <ol>
        {displayEntries.map((entry, index) => (
          <li key={`${entry}-${index}`}>{entry}</li>
        ))}
      </ol>
      <p className="activity-commands-label">RECENT COMMANDS</p>
      {recentCommands.length === 0 ? (
        <p className="hud-state hud-state-empty">No commands yet</p>
      ) : (
        <ul className="recent-commands">
          {recentCommands.slice(0, 4).map((command, index) => (
            <li key={`${command}-${index}`} title={command}>
              {command}
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
