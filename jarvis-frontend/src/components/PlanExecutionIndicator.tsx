import { PlanStep } from "../api/chat";

type PlanExecutionIndicatorProps = {
  steps: PlanStep[];
};

export function PlanExecutionIndicator({ steps }: PlanExecutionIndicatorProps) {
  if (!steps || steps.length === 0) return null;

  return (
    <div style={{
      margin: "12px 0",
      padding: "12px 16px",
      background: "rgba(10, 25, 45, 0.75)",
      border: "1px solid rgba(0, 217, 255, 0.3)",
      borderRadius: "10px",
      backdropFilter: "blur(10px)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
        <span style={{ fontSize: "14px" }}>⚡</span>
        <span style={{ fontSize: "11px", fontWeight: 700, color: "#64ffda", letterSpacing: "1px" }}>
          AUTONOMOUS EXECUTION PLAN
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        {steps.map((s) => {
          const isDone = s.status === "completed";
          const isCurrent = s.status === "in_progress";

          return (
            <div
              key={s.stepNumber}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                fontSize: "12px",
                color: isDone ? "#94a3b8" : isCurrent ? "#ffffff" : "#64748b",
              }}
            >
              <span style={{
                width: "18px",
                height: "18px",
                borderRadius: "50%",
                background: isDone ? "rgba(16, 185, 129, 0.2)" : isCurrent ? "rgba(0, 217, 255, 0.3)" : "rgba(255, 255, 255, 0.05)",
                border: isDone ? "1px solid #10b981" : isCurrent ? "1px solid #00d9ff" : "1px solid rgba(255, 255, 255, 0.1)",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "10px",
                color: isDone ? "#10b981" : isCurrent ? "#00d9ff" : "#64748b",
                fontWeight: 700,
              }}>
                {isDone ? "✓" : isCurrent ? "⟳" : s.stepNumber}
              </span>
              <span style={{ fontWeight: isCurrent ? 600 : 400 }}>{s.title}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
