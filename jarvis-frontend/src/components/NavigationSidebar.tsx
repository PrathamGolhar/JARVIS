import React from 'react';

export type WorkspaceView =
  | 'dashboard'
  | 'core'
  | 'projects'
  | 'files'
  | 'research'
  | 'study'
  | 'coding'
  | 'automation'
  | 'memory'
  | 'integrations'
  | 'diagnostics'
  | 'settings';

interface NavigationSidebarProps {
  currentView: WorkspaceView;
  onSelectView: (view: WorkspaceView) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  fileCount?: number;
  activeProjectName?: string;
  isListening?: boolean;
}

export const NavigationSidebar: React.FC<NavigationSidebarProps> = ({
  currentView,
  onSelectView,
  isCollapsed,
  onToggleCollapse,
  fileCount = 0,
  activeProjectName,
  isListening = false,
}) => {
  const navItems: {
    id: WorkspaceView;
    label: string;
    icon: React.ReactNode;
    badge?: string | number;
    accentColor: string;
  }[] = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect width="7" height="9" x="3" y="3" rx="1" />
          <rect width="7" height="5" x="14" y="3" rx="1" />
          <rect width="7" height="9" x="14" y="12" rx="1" />
          <rect width="7" height="5" x="3" y="16" rx="1" />
        </svg>
      ),
      accentColor: 'text-cyan-400',
    },
    {
      id: 'core',
      label: 'JARVIS Core',
      icon: (
        <svg className={`w-4 h-4 ${isListening ? 'animate-spin text-yellow-400' : 'text-cyan-300'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2" />
          <path d="M12 20v2" />
          <path d="M2 12h2" />
          <path d="M20 12h2" />
        </svg>
      ),
      badge: isListening ? 'VOICE' : undefined,
      accentColor: 'text-cyan-300',
    },
    {
      id: 'projects',
      label: 'Projects',
      icon: (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z" />
        </svg>
      ),
      badge: activeProjectName ? '1' : undefined,
      accentColor: 'text-blue-400',
    },
    {
      id: 'files',
      label: 'Files & Artifacts',
      icon: (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      ),
      badge: fileCount > 0 ? fileCount : undefined,
      accentColor: 'text-emerald-400',
    },
    {
      id: 'research',
      label: 'Deep Research',
      icon: (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.3-4.3" />
        </svg>
      ),
      accentColor: 'text-purple-400',
    },
    {
      id: 'study',
      label: 'Study & Academics',
      icon: (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
          <path d="M6 6h10" />
          <path d="M6 10h10" />
        </svg>
      ),
      accentColor: 'text-amber-400',
    },
    {
      id: 'coding',
      label: 'Code Sandbox',
      icon: (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="4 17 10 11 4 5" />
          <line x1="12" x2="20" y1="19" y2="19" />
        </svg>
      ),
      accentColor: 'text-cyan-400',
    },
    {
      id: 'automation',
      label: 'Automations',
      icon: (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2v4" />
          <path d="M12 18v4" />
          <path d="M4.93 4.93l2.83 2.83" />
          <path d="M16.24 16.24l2.83 2.83" />
          <path d="M2 12h4" />
          <path d="M18 12h4" />
          <path d="M4.93 19.07l2.83-2.83" />
          <path d="M16.24 7.76l2.83-2.83" />
        </svg>
      ),
      accentColor: 'text-violet-400',
    },
    {
      id: 'memory',
      label: 'Memory Center',
      icon: (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2a6 6 0 0 0-6 6c0 3 2 5.5 5 5.9V18h2v-4.1c3-.4 5-2.9 5-5.9a6 6 0 0 0-6-6Z" />
          <path d="M9 22h6" />
        </svg>
      ),
      accentColor: 'text-pink-400',
    },
    {
      id: 'integrations',
      label: 'Integrations',
      icon: (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
          <polyline points="15 3 21 3 21 9" />
          <line x1="10" x2="21" y1="14" y2="3" />
        </svg>
      ),
      accentColor: 'text-teal-400',
    },
    {
      id: 'diagnostics',
      label: 'System Health',
      icon: (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </svg>
      ),
      accentColor: 'text-green-400',
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: (
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      ),
      accentColor: 'text-slate-400',
    },
  ];

  return (
    <aside
      aria-label="JARVIS navigation"
      className={`glass-panel flex flex-col justify-between border-r border-cyan-500/20 transition-all duration-300 z-30 select-none ${
        isCollapsed ? 'w-16' : 'w-60'
      } h-full`}
    >
      {/* Brand Header */}
      <div>
        <div className="p-3.5 flex items-center justify-between border-b border-cyan-500/20">
          {!isCollapsed && (
            <div className="flex items-center space-x-2 overflow-hidden">
              <div className="w-7 h-7 rounded-lg bg-cyan-500/20 border border-cyan-500/50 flex items-center justify-center neon-border-cyan shrink-0">
                <span className="font-mono font-black text-cyan-300 text-sm">J</span>
              </div>
              <div className="truncate">
                <div className="font-mono font-extrabold text-cyan-100 text-xs tracking-wider">JARVIS 2.0</div>
                <div className="text-[9px] font-mono text-cyan-500/70 tracking-tight">AI Operating Assistant</div>
              </div>
            </div>
          )}

          {isCollapsed && (
            <div className="w-8 h-8 mx-auto rounded-lg bg-cyan-500/20 border border-cyan-500/50 flex items-center justify-center neon-border-cyan">
              <span className="font-mono font-black text-cyan-300 text-sm">J</span>
            </div>
          )}

          {!isCollapsed && (
            <button
              onClick={onToggleCollapse}
              className="text-cyan-500 hover:text-cyan-300 p-1 rounded hover:bg-cyan-500/10 transition-colors"
              title="Collapse Sidebar"
              aria-label="Collapse sidebar"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
          )}
        </div>

        {/* Navigation Items */}
        <nav className="p-2 space-y-1 overflow-y-auto max-h-[calc(100vh-140px)]">
          {navItems.map((item) => {
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectView(item.id)}
                aria-current={isActive ? 'page' : undefined}
                aria-label={isCollapsed ? item.label : undefined}
                className={`w-full flex items-center ${
                  isCollapsed ? 'justify-center px-0' : 'justify-between px-3'
                } py-2 rounded-lg transition-all text-xs font-mono group relative ${
                  isActive
                    ? 'bg-cyan-500/20 text-cyan-100 border border-cyan-500/50 shadow-sm shadow-cyan-500/20 font-semibold'
                    : 'text-slate-400 hover:text-cyan-200 hover:bg-cyan-500/10 border border-transparent'
                }`}
                title={isCollapsed ? item.label : undefined}
              >
                <div className="flex items-center space-x-2.5">
                  <div className={`p-1 rounded ${isActive ? item.accentColor : 'text-slate-400 group-hover:text-cyan-300'}`}>
                    {item.icon}
                  </div>
                  {!isCollapsed && <span className="truncate">{item.label}</span>}
                </div>

                {!isCollapsed && item.badge && (
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30" aria-hidden="true">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Collapse Footer Toggle (when collapsed) */}
      <div className="p-2 border-t border-cyan-500/20">
        <button
          onClick={onToggleCollapse}
          className="w-full flex items-center justify-center py-2 text-cyan-500 hover:text-cyan-300 hover:bg-cyan-500/10 rounded-lg transition-colors text-xs font-mono"
          title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          <svg className={`w-4 h-4 transition-transform duration-300 ${isCollapsed ? 'rotate-180' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
      </div>
    </aside>
  );
};
