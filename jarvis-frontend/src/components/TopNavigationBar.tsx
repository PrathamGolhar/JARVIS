import React, { useState, useEffect } from 'react';
import { AssistantMode } from '../api/chat';

interface TopNavigationBarProps {
  systemStatus: 'online' | 'degraded' | 'offline';
  activeMode: AssistantMode;
  onChangeMode: (mode: AssistantMode) => void;
  onOpenCommandPalette: () => void;
  onToggleFocusMode: () => void;
  isFocusMode: boolean;
  notificationCount?: number;
  onOpenNotifications: () => void;
  activeProjectName?: string;
}

export const TopNavigationBar: React.FC<TopNavigationBarProps> = ({
  systemStatus,
  activeMode,
  onChangeMode,
  onOpenCommandPalette,
  onToggleFocusMode,
  isFocusMode,
  notificationCount = 0,
  onOpenNotifications,
  activeProjectName,
}) => {
  const [timeString, setTimeString] = useState('');

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setTimeString(
        now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true })
      );
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  const statusConfig = {
    online: { label: 'ONLINE', dotClass: 'bg-emerald-400 shadow-emerald-500/50', textClass: 'text-emerald-300' },
    degraded: { label: 'DEGRADED', dotClass: 'bg-amber-400 shadow-amber-500/50', textClass: 'text-amber-300' },
    offline: { label: 'OFFLINE', dotClass: 'bg-rose-500 shadow-rose-500/50', textClass: 'text-rose-400' },
  }[systemStatus];

  return (
    <header className="glass-panel border-b border-cyan-500/20 px-4 py-2.5 flex items-center justify-between z-30 select-none font-mono">
      {/* Left: Brand Identity & Active Project */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2">
          <span className="font-extrabold text-cyan-200 tracking-wider text-xs hidden sm:inline">JARVIS 2.0</span>
          <span className="text-cyan-600 hidden sm:inline">/</span>
          <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-slate-950/60 border border-cyan-500/30">
            <span className={`w-2 h-2 rounded-full ${statusConfig.dotClass} animate-pulse shadow-sm`} />
            <span className={`text-[10px] font-bold ${statusConfig.textClass}`}>{statusConfig.label}</span>
          </div>
        </div>

        {activeProjectName && (
          <div className="hidden md:flex items-center space-x-1 px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/30 text-blue-300 text-[11px]">
            <span>Project:</span>
            <span className="font-semibold text-blue-100 truncate max-w-[120px]">{activeProjectName}</span>
          </div>
        )}
      </div>

      {/* Middle: Mode Selector Pills */}
      <div className="hidden lg:flex items-center space-x-1 bg-slate-950/70 p-1 rounded-lg border border-cyan-500/20 text-[11px]">
        {(['general', 'study', 'research', 'coding'] as AssistantMode[]).map((m) => (
          <button
            key={m}
            onClick={() => onChangeMode(m)}
            className={`px-2.5 py-0.5 rounded-md transition-all uppercase text-[10px] font-semibold ${
              activeMode === m
                ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/50 shadow-sm shadow-cyan-500/20'
                : 'text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10'
            }`}
          >
            {m}
          </button>
        ))}
      </div>

      {/* Right: Clock, Command Palette Button, Focus Toggle & Notifications */}
      <div className="flex items-center space-x-2.5">
        {/* Real-time Clock */}
        <div className="text-xs text-cyan-300/90 font-mono tracking-widest px-2 py-1 rounded bg-slate-950/60 border border-cyan-500/20 hidden sm:block">
          {timeString || '03:42:00 AM'}
        </div>

        {/* Command Palette Trigger */}
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center space-x-1 px-2.5 py-1 rounded bg-cyan-500/10 hover:bg-cyan-500/25 border border-cyan-500/40 text-cyan-300 text-xs transition-colors cursor-pointer"
          title="Command Palette (Ctrl+K)"
        >
          <svg className="w-3 h-3 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <span className="text-[11px] font-bold">⌘K</span>
        </button>

        {/* Focus Mode Toggle */}
        <button
          onClick={onToggleFocusMode}
          className={`p-1.5 rounded transition-colors border ${
            isFocusMode
              ? 'bg-cyan-500/20 text-cyan-100 border-cyan-500/50'
              : 'text-slate-400 hover:text-cyan-300 border-transparent hover:bg-cyan-500/10'
          }`}
          title={isFocusMode ? 'Exit Focus Mode' : 'Enter Focus Mode (Distraction-Free)'}
        >
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
          </svg>
        </button>

        {/* Notifications */}
        <button
          onClick={onOpenNotifications}
          className="relative p-1.5 rounded text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10 transition-colors"
          title="Notifications"
        >
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
            <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
          </svg>
          {notificationCount > 0 && (
            <span className="absolute top-0 right-0 w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
          )}
        </button>
      </div>
    </header>
  );
};
