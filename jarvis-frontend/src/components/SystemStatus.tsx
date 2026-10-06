import { DiagnosticItem, SystemMetrics } from "../api/diagnostics";

type SystemStatusProps = {
  items: DiagnosticItem[];
  metrics?: SystemMetrics;
  onRefresh?: () => void;
  isLoading?: boolean;
};

export function SystemStatus({ items, metrics, onRefresh, isLoading }: SystemStatusProps) {
  return (
    <aside className="system-status" aria-label="System status">
      <div className="status-title-row">
        <p className="status-title">SYSTEM STATUS</p>
        {onRefresh && (
          <button type="button" className="status-refresh-btn" onClick={onRefresh} disabled={isLoading}>
            {isLoading ? "SYNC…" : "SYNC"}
          </button>
        )}
      </div>

      {isLoading && items.length === 0 ? (
        <div className="hud-state hud-state-loading" role="status">
          <span className="hud-spinner" aria-hidden="true" />
          Linking diagnostics…
        </div>
      ) : items.length === 0 ? (
        <div className="hud-state hud-state-empty">No subsystem telemetry</div>
      ) : (
        <div className="status-grid">
          {items.map((item) => (
            <div className="status-tile" key={item.id} title={item.details}>
              <span className={`status-light ${item.status}`} />
              <span className="status-tile-label">{item.label}</span>
              <strong>
                {item.status.toUpperCase()}
                {item.latencyMs !== undefined && item.latencyMs !== null && ` (${item.latencyMs}ms)`}
              </strong>
            </div>
          ))}
        </div>
      )}

      {metrics && (
        <div className="system-metrics-card">
          <div className="metric-row">
            <span>CPU</span>
            <strong>
              {metrics.cpu_usage_percent ?? 0}% · {metrics.cpu_cores ?? 0} cores
            </strong>
          </div>
          <div className="metric-row">
            <span>MEMORY</span>
            <strong>
              {metrics.ram_used_gb ?? 0} / {metrics.ram_total_gb ?? 0} GB
            </strong>
          </div>
          <div className="metric-row">
            <span>DISK</span>
            <strong>
              {metrics.disk_free_gb ?? 0} GB free
            </strong>
          </div>
          {metrics.system_uptime && (
            <div className="metric-row">
              <span>UPTIME</span>
              <strong>{metrics.system_uptime}</strong>
            </div>
          )}
        </div>
      )}

      <p className="status-key">
        <i className="status-light ready" /> live
        <i className="status-light warning" /> alert
        <i className="status-light error" /> offline
      </p>
    </aside>
  );
}
