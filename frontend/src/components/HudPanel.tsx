import { ReactNode } from "react";

type HudPanelProps = {
  title: string;
  children: ReactNode;
  className?: string;
  action?: ReactNode;
  empty?: boolean;
  emptyLabel?: string;
  loading?: boolean;
  error?: string;
};

export function HudPanel({
  title,
  children,
  className = "",
  action,
  empty,
  emptyLabel = "No telemetry yet",
  loading,
  error,
}: HudPanelProps) {
  return (
    <section className={`hud-panel hud-corner-brackets ${className}`}>
      <header className="hud-panel-header">
        <span className="hud-panel-title">{title}</span>
        {action}
      </header>
      {loading ? (
        <div className="hud-state hud-state-loading" role="status">
          <span className="hud-spinner" aria-hidden="true" />
          Syncing subsystems…
        </div>
      ) : error ? (
        <div className="hud-state hud-state-error" role="alert">
          {error}
        </div>
      ) : empty ? (
        <div className="hud-state hud-state-empty">{emptyLabel}</div>
      ) : (
        children
      )}
    </section>
  );
}
