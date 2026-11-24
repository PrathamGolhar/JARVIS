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
    defaultEntries: ["No active request"],
  },
  connecting: {
    label: "MICROPHONE ACCESS",
    defaultEntries: ["Waiting for browser permission"],
  },
  listening: {
    label: "VOICE INPUT ACTIVE",
    defaultEntries: ["Microphone stream active"],
  },
  transcribing: {
    label: "TRANSCRIBING",
    defaultEntries: ["Finalizing captured speech"],
  },
  understanding: {
    label: "UNDERSTANDING",
    defaultEntries: ["Preparing request"],
  },
  thinking: {
    label: "PROCESSING REQUEST",
    defaultEntries: ["Waiting for the assistant response"],
  },
  searching: {
    label: "SEARCHING SOURCES",
    defaultEntries: ["Source search in progress"],
  },
  executing: {
    label: "TOOL EXECUTION",
    defaultEntries: ["Requested tool is running"],
  },
  confirmation: {
    label: "WAITING FOR CONFIRMATION",
    defaultEntries: ["No action will continue until you decide"],
  },
  speaking: {
    label: "SYNTHESIZING",
    defaultEntries: ["Voice response playing"],
  },
  error: {
    label: "ATTENTION REQUIRED",
    defaultEntries: ["Check the message above for details"],
  },
};

export function ActivityMonitor({ state, activeTool, recentTools = [], recentCommands = [] }: ActivityMonitorProps) {
  const current = activityDetails[state] || activityDetails.idle;

  const displayEntries = activeTool
    ? [`ACTIVE: ${activeTool.toUpperCase()}`, ...recentTools.slice(-2).map((t) => `RECENT: ${t.toUpperCase()}`)]
    : recentTools.length > 0
    ? recentTools.slice(-3).map((t) => `RECENT: ${t.toUpperCase()}`)
    : current.defaultEntries;

  return (
    <aside className={`activity-monitor state-${state}`} aria-label="AI activity">
      <div className="monitor-heading">
        <span>AI ACTIVITY</span>
        <i aria-hidden="true" />
      </div>
      <strong className="activity-live-label" aria-live="polite">{current.label}</strong>
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
