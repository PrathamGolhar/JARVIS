import React from "react";

interface QuickActionsBarProps {
  onSelectAction: (actionType: string, payload?: any) => void;
  onOpenCommandPalette: () => void;
}

export const QuickActionsBar: React.FC<QuickActionsBarProps> = ({
  onSelectAction,
  onOpenCommandPalette,
}) => {
  const actions = [
    {
      id: "study",
      label: "Study & Quiz",
      icon: (
        <svg className="w-3.5 h-3.5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
        </svg>
      ),
      onClick: () => onSelectAction("mode", "study"),
    },
    {
      id: "research",
      label: "Deep Research",
      icon: (
        <svg className="w-3.5 h-3.5 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.3-4.3" />
        </svg>
      ),
      onClick: () => onSelectAction("mode", "research"),
    },
    {
      id: "pdf",
      label: "PDF Report",
      icon: (
        <svg className="w-3.5 h-3.5 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      ),
      onClick: () => onSelectAction("generate", "pdf"),
    },
    {
      id: "pptx",
      label: "16:9 Deck",
      icon: (
        <svg className="w-3.5 h-3.5 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect width="18" height="12" x="3" y="4" rx="2" />
        </svg>
      ),
      onClick: () => onSelectAction("generate", "pptx"),
    },
    {
      id: "sandbox",
      label: "Code Sandbox",
      icon: (
        <svg className="w-3.5 h-3.5 text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="4 17 10 11 4 5" />
          <line x1="12" x2="20" y1="19" y2="19" />
        </svg>
      ),
      onClick: () => onSelectAction("mode", "coding"),
    },
  ];

  return (
    <div className="flex items-center space-x-2 overflow-x-auto py-1.5 px-2 bg-slate-950/40 border border-cyan-500/20 rounded-lg backdrop-blur-sm text-xs font-mono">
      <button
        onClick={onOpenCommandPalette}
        className="flex items-center space-x-1 px-2.5 py-1 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 rounded-md transition-all shrink-0 cursor-pointer"
        title="Command Palette (Ctrl+K)"
      >
        <span className="text-[10px] font-bold">⌘K</span>
      </button>

      <div className="h-4 w-px bg-cyan-500/20 shrink-0" />

      {actions.map((act) => (
        <button
          key={act.id}
          onClick={act.onClick}
          className="flex items-center space-x-1.5 px-2.5 py-1 bg-slate-900/60 hover:bg-cyan-500/10 text-cyan-200/80 hover:text-cyan-100 border border-cyan-500/20 hover:border-cyan-500/40 rounded-md transition-all shrink-0 cursor-pointer"
        >
          {act.icon}
          <span>{act.label}</span>
        </button>
      ))}
    </div>
  );
};
