import React, { useState, useEffect } from "react";

interface CommandItem {
  id: string;
  title: string;
  category: string;
  icon: React.ReactNode;
  action: () => void;
  shortcut?: string;
}

interface CommandPaletteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectAction: (actionType: string, payload?: any) => void;
}

export const CommandPaletteModal: React.FC<CommandPaletteModalProps> = ({
  isOpen,
  onClose,
  onSelectAction,
}) => {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const commands: CommandItem[] = [
    {
      id: "study-mode",
      title: "Launch Academic Study Mode (Notes & Quiz)",
      category: "Intelligence",
      icon: (
        <svg className="w-4 h-4 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
          <path d="M6 6h10" />
          <path d="M6 10h10" />
        </svg>
      ),
      action: () => onSelectAction("mode", "study"),
      shortcut: "S",
    },
    {
      id: "deep-research",
      title: "Initiate Deep Web Research & Citations",
      category: "Intelligence",
      icon: (
        <svg className="w-4 h-4 text-purple-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.3-4.3" />
        </svg>
      ),
      action: () => onSelectAction("mode", "research"),
      shortcut: "R",
    },
    {
      id: "gen-pdf",
      title: "Generate Publication PDF Report Document",
      category: "Document Synthesis",
      icon: (
        <svg className="w-4 h-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      ),
      action: () => onSelectAction("generate", "pdf"),
      shortcut: "P",
    },
    {
      id: "gen-pptx",
      title: "Generate 16:9 Presentation Deck (PPTX)",
      category: "Document Synthesis",
      icon: (
        <svg className="w-4 h-4 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect width="18" height="12" x="3" y="4" rx="2" />
          <path d="M8 20h8" />
          <path d="M12 16v4" />
        </svg>
      ),
      action: () => onSelectAction("generate", "pptx"),
    },
    {
      id: "code-sandbox",
      title: "Open Code Assistant & Execution Sandbox",
      category: "Engineering",
      icon: (
        <svg className="w-4 h-4 text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="4 17 10 11 4 5" />
          <line x1="12" x2="20" y1="19" y2="19" />
        </svg>
      ),
      action: () => onSelectAction("mode", "coding"),
      shortcut: "C",
    },
    {
      id: "memory-inspector",
      title: "Inspect Long-Term Memory & RAG Vectors",
      category: "System",
      icon: (
        <svg className="w-4 h-4 text-pink-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2a6 6 0 0 0-6 6c0 3 2 5.5 5 5.9V18h2v-4.1c3-.4 5-2.9 5-5.9a6 6 0 0 0-6-6Z" />
          <path d="M9 22h6" />
        </svg>
      ),
      action: () => onSelectAction("modal", "memory"),
      shortcut: "M",
    },
    {
      id: "system-diagnostics",
      title: "System Diagnostics & Real-Time Probes",
      category: "System",
      icon: (
        <svg className="w-4 h-4 text-cyan-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </svg>
      ),
      action: () => onSelectAction("modal", "diagnostics"),
      shortcut: "D",
    },
  ];

  const filteredCommands = commands.filter(
    (c) =>
      c.title.toLowerCase().includes(query.toLowerCase()) ||
      c.category.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % (filteredCommands.length || 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filteredCommands.length) % (filteredCommands.length || 1));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          filteredCommands[selectedIndex].action();
          onClose();
        }
      } else if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, filteredCommands, selectedIndex, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-black/70 backdrop-blur-md">
      <div className="w-full max-w-xl bg-slate-900/95 border border-cyan-500/40 rounded-xl shadow-2xl shadow-cyan-500/20 overflow-hidden font-mono text-cyan-100">
        {/* Search Bar */}
        <div className="flex items-center px-4 py-3 border-b border-cyan-500/20 bg-slate-950/80">
          <svg className="w-5 h-5 text-cyan-400 mr-3 animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            type="text"
            className="flex-1 bg-transparent text-cyan-100 placeholder-cyan-600 focus:outline-none text-sm"
            placeholder="Search JARVIS 2.0 capabilities & tools... (ESC to dismiss)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          <button onClick={onClose} className="text-cyan-500 hover:text-cyan-300">
            ✕
          </button>
        </div>

        {/* Command List */}
        <div className="max-h-80 overflow-y-auto p-2 divide-y divide-cyan-500/10">
          {filteredCommands.length === 0 ? (
            <div className="py-6 text-center text-cyan-600 text-xs">
              No matching command found in JARVIS command center.
            </div>
          ) : (
            filteredCommands.map((item, idx) => (
              <div
                key={item.id}
                onClick={() => {
                  item.action();
                  onClose();
                }}
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition-colors text-xs ${
                  idx === selectedIndex
                    ? "bg-cyan-500/20 text-cyan-200 border border-cyan-500/40"
                    : "text-cyan-400/80 hover:bg-cyan-500/10"
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className="p-1.5 rounded-md bg-slate-950/60 border border-cyan-500/20">
                    {item.icon}
                  </div>
                  <div>
                    <div className="font-semibold text-cyan-100">{item.title}</div>
                    <div className="text-[10px] text-cyan-500/60">{item.category}</div>
                  </div>
                </div>
                {item.shortcut && (
                  <span className="px-2 py-0.5 rounded bg-slate-950/80 border border-cyan-500/30 text-cyan-400 text-[10px]">
                    {item.shortcut}
                  </span>
                )}
              </div>
            ))
          )}
        </div>

        {/* Footer Navigation */}
        <div className="px-4 py-2 bg-slate-950/90 border-t border-cyan-500/20 flex items-center justify-between text-[11px] text-cyan-600">
          <span>JARVIS 2.0 Command Center</span>
          <span>Use ↑ ↓ to navigate · ↵ to trigger</span>
        </div>
      </div>
    </div>
  );
};
