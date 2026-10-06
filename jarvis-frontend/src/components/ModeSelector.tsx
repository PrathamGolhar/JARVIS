import { AssistantMode } from "../api/chat";

type ModeSelectorProps = {
  activeMode: AssistantMode;
  onSelectMode: (mode: AssistantMode) => void;
};

const MODES: { id: AssistantMode; label: string; icon: string; desc: string }[] = [
  { id: "general", label: "GENERAL", icon: "⚡", desc: "Adaptive general assistant" },
  { id: "study", label: "STUDY", icon: "📚", desc: "Notes, formulas & exam MCQs" },
  { id: "research", label: "RESEARCH", icon: "🌐", desc: "Deep web research with citations" },
  { id: "coding", label: "CODING", icon: "💻", desc: "Code analysis & sandbox execution" },
  { id: "project", label: "PROJECT", icon: "📁", desc: "Project tasks & context memory" },
  { id: "document", label: "DOCUMENT", icon: "📄", desc: "PDF & DOCX report generation" },
  { id: "presentation", label: "SLIDES", icon: "📊", desc: "16:9 Widescreen PowerPoint" },
  { id: "automation", label: "AUTOMATION", icon: "⏰", desc: "Reminders & workflows" },
  { id: "voice", label: "VOICE", icon: "🎤", desc: "Hands-free continuous voice" },
];

export function ModeSelector({ activeMode, onSelectMode }: ModeSelectorProps) {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: "6px",
      overflowX: "auto",
      padding: "6px 12px",
      background: "rgba(10, 20, 35, 0.75)",
      backdropFilter: "blur(12px)",
      border: "1px solid rgba(0, 217, 255, 0.25)",
      borderRadius: "12px",
      scrollbarWidth: "none",
      boxShadow: "0 4px 20px rgba(0, 0, 0, 0.4)",
    }}>
      <span style={{ fontSize: "11px", fontWeight: 700, color: "#64ffda", letterSpacing: "1px", marginRight: "6px" }}>
        MODE:
      </span>
      {MODES.map((m) => {
        const isActive = activeMode === m.id;
        return (
          <button
            key={m.id}
            onClick={() => onSelectMode(m.id)}
            title={m.desc}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "5px",
              padding: "5px 11px",
              background: isActive ? "linear-gradient(135deg, rgba(0, 217, 255, 0.3), rgba(100, 255, 218, 0.15))" : "rgba(15, 30, 50, 0.5)",
              border: isActive ? "1px solid #00d9ff" : "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "8px",
              color: isActive ? "#ffffff" : "rgba(204, 214, 246, 0.7)",
              fontSize: "11px",
              fontWeight: 600,
              letterSpacing: "0.5px",
              cursor: "pointer",
              transition: "all 0.2s ease",
              boxShadow: isActive ? "0 0 12px rgba(0, 217, 255, 0.4)" : "none",
              whiteSpace: "nowrap",
            }}
          >
            <span>{m.icon}</span>
            <span>{m.label}</span>
          </button>
        );
      })}
    </div>
  );
}
