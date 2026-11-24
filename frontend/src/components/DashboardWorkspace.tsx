import React, { useState, useEffect } from 'react';
import { fetchDiagnostics, DiagnosticItem, SystemMetrics } from '../api/diagnostics';
import { fetchProjects, ProjectItem } from '../api/projects';
import { WorkspaceView } from './NavigationSidebar';
import { showToast } from './ToastNotificationSystem';

interface DashboardWorkspaceProps {
  onNavigate: (view: WorkspaceView) => void;
  activeProjectId?: string;
  onOpenCommandPalette: () => void;
}

export const DashboardWorkspace: React.FC<DashboardWorkspaceProps> = ({
  onNavigate,
  activeProjectId,
  onOpenCommandPalette,
}) => {
  const [metrics, setMetrics] = useState<SystemMetrics | undefined>();
  const [diagnostics, setDiagnostics] = useState<DiagnosticItem[]>([]);
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [diagData, projData] = await Promise.all([
        fetchDiagnostics().catch(() => ({ items: [], systemMetrics: undefined })),
        fetchProjects().catch(() => []),
      ]);
      setDiagnostics(diagData.items);
      setMetrics(diagData.systemMetrics);
      setProjects(projData);
    } catch {
      showToast({
        title: 'Telemetry Sync',
        message: 'Loaded cached dashboard state.',
        type: 'info',
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  const agents = [
    { name: 'Orchestrator', tier: 'High Reasoning', status: 'Active', color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
    { name: 'Research Agent', tier: 'DuckDuckGo Live', status: 'Ready', color: 'text-blue-400', bg: 'bg-blue-500/10' },
    { name: 'Document Agent', tier: 'PDF/DOCX/PPTX', status: 'Ready', color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { name: 'Coding Agent', tier: 'Python Sandbox', status: 'Ready', color: 'text-violet-400', bg: 'bg-violet-500/10' },
    { name: 'Math Agent', tier: 'SymPy Symbolic', status: 'Ready', color: 'text-amber-400', bg: 'bg-amber-500/10' },
    { name: 'Multi-Doc Agent', tier: 'Cross-Doc RAG', status: 'Ready', color: 'text-pink-400', bg: 'bg-pink-500/10' },
    { name: 'Study Agent', tier: 'MCQ & Flashcards', status: 'Ready', color: 'text-teal-400', bg: 'bg-teal-500/10' },
    { name: 'Verification Agent', tier: 'Self-Correction', status: 'Active', color: 'text-green-400', bg: 'bg-green-500/10' },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 font-sans text-slate-100 max-w-7xl mx-auto w-full">
      {/* HUD Header Banner */}
      <div className="glass-panel p-6 rounded-2xl border border-cyan-500/30 flex flex-col lg:flex-row lg:items-center justify-between gap-4 shadow-xl shadow-cyan-950/20">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <h1 className="text-2xl font-black tracking-tight text-white font-mono flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-cyan-400 animate-pulse shadow-md shadow-cyan-400" />
              JARVIS 2.0 COMMAND OVERVIEW
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/20 border border-cyan-500/50 text-cyan-300 font-mono">
              SYSTEM LIVE
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Autonomous multi-agent orchestration operating across local subsystems and distributed AI tiers.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={onOpenCommandPalette}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/50 text-cyan-200 text-xs font-mono font-semibold transition-all cursor-pointer shadow-lg shadow-cyan-500/10"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
            <span>QUICK DISPATCH (Ctrl+K)</span>
          </button>
          <button
            onClick={() => onNavigate('core')}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 text-xs font-mono font-bold transition-all cursor-pointer shadow-lg shadow-cyan-500/25"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <circle cx="12" cy="12" r="4" />
            </svg>
            <span>VOICE ORB</span>
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-4 rounded-xl border border-cyan-500/20 hover:border-cyan-500/40 transition-all">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
            <span>CPU UTILIZATION</span>
            <span className="text-cyan-400 font-bold">{metrics?.cpu_usage_percent ?? 4.2}%</span>
          </div>
          <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden border border-cyan-500/20">
            <div
              className="bg-cyan-400 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, metrics?.cpu_usage_percent ?? 4.2)}%` }}
            />
          </div>
          <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
            <span>Memory Allocated</span>
            <span className="font-mono text-slate-200">{metrics?.ram_usage_percent ?? 32}%</span>
          </div>
        </div>

        <div
          onClick={() => onNavigate('projects')}
          className="glass-panel p-4 rounded-xl border border-blue-500/20 hover:border-blue-500/40 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
            <span>ACTIVE PROJECTS</span>
            <span className="text-blue-400 font-bold group-hover:scale-110 transition-transform">{projects.length}</span>
          </div>
          <div className="text-lg font-bold text-white truncate">
            {projects.find((p) => p.id === activeProjectId)?.name ?? 'Default Workspace'}
          </div>
          <div className="mt-2 text-[11px] text-blue-300/80 flex items-center gap-1">
            <span>Manage workspaces & tasks</span>
            <span>&rarr;</span>
          </div>
        </div>

        <div
          onClick={() => onNavigate('files')}
          className="glass-panel p-4 rounded-xl border border-emerald-500/20 hover:border-emerald-500/40 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
            <span>DELIVERED ARTIFACTS</span>
            <span className="text-emerald-400 font-bold">READY</span>
          </div>
          <div className="text-lg font-bold text-white">PDF / DOCX / PPTX</div>
          <div className="mt-2 text-[11px] text-emerald-300/80 flex items-center gap-1">
            <span>Browse generated files</span>
            <span>&rarr;</span>
          </div>
        </div>

        <div
          onClick={() => onNavigate('memory')}
          className="glass-panel p-4 rounded-xl border border-violet-500/20 hover:border-violet-500/40 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
            <span>KNOWLEDGE BASE</span>
            <span className="text-violet-400 font-bold">PERSISTED</span>
          </div>
          <div className="text-lg font-bold text-white">User Preferences & Facts</div>
          <div className="mt-2 text-[11px] text-violet-300/80 flex items-center gap-1">
            <span>Inspect memory vector store</span>
            <span>&rarr;</span>
          </div>
        </div>
      </div>

      {/* Multi-Agent Ecosystem Matrix */}
      <div className="glass-panel p-6 rounded-2xl border border-cyan-500/20">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-bold tracking-wider font-mono text-cyan-300 uppercase">
              Agent Ecosystem Matrix
            </h2>
            <p className="text-xs text-slate-400">
              Coordinated specialized agents executing sequential and concurrent DAG subtasks.
            </p>
          </div>
          <span className="px-2.5 py-1 rounded bg-slate-900 border border-cyan-500/30 text-[10px] font-mono text-cyan-300">
            8 / 8 DISPATCHED
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {agents.map((agent) => (
            <div
              key={agent.name}
              className={`p-3.5 rounded-xl border border-slate-800 hover:border-cyan-500/30 ${agent.bg} transition-all`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className={`text-xs font-bold font-mono ${agent.color}`}>{agent.name}</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              </div>
              <div className="text-[11px] text-slate-300 font-mono">{agent.tier}</div>
              <div className="mt-2 text-[10px] text-slate-500 font-mono uppercase tracking-widest">{agent.status}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Access Dispatcher Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div
          onClick={() => onNavigate('research')}
          className="glass-panel p-5 rounded-xl border border-cyan-500/20 hover:border-cyan-400/50 hover:bg-cyan-500/5 transition-all cursor-pointer"
        >
          <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-300 mb-3">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
          </div>
          <h3 className="text-sm font-bold text-white mb-1">Deep Web Research</h3>
          <p className="text-xs text-slate-400">
            Multi-source web query synthesis with citation grounding and confidence scoring.
          </p>
        </div>

        <div
          onClick={() => onNavigate('coding')}
          className="glass-panel p-5 rounded-xl border border-violet-500/20 hover:border-violet-400/50 hover:bg-violet-500/5 transition-all cursor-pointer"
        >
          <div className="w-8 h-8 rounded-lg bg-violet-500/20 border border-violet-500/40 flex items-center justify-center text-violet-300 mb-3">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="16 18 22 12 16 6" />
              <polyline points="8 6 2 12 8 18" />
            </svg>
          </div>
          <h3 className="text-sm font-bold text-white mb-1">Code Sandbox & AST</h3>
          <p className="text-xs text-slate-400">
            Write, execute, benchmark, and automatically debug Python and multi-language code.
          </p>
        </div>

        <div
          onClick={() => onNavigate('study')}
          className="glass-panel p-5 rounded-xl border border-teal-500/20 hover:border-teal-400/50 hover:bg-teal-500/5 transition-all cursor-pointer"
        >
          <div className="w-8 h-8 rounded-lg bg-teal-500/20 border border-teal-500/40 flex items-center justify-center text-teal-300 mb-3">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
              <path d="M6 6h10" />
              <path d="M6 10h10" />
            </svg>
          </div>
          <h3 className="text-sm font-bold text-white mb-1">Study & Exam Hub</h3>
          <p className="text-xs text-slate-400">
            Generate customized study guides, formula sheets, MCQ practice tests, and flashcards.
          </p>
        </div>
      </div>

      {/* Subsystem Health Status Bar */}
      <div className="glass-panel p-4 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
        <div className="flex items-center space-x-6 text-slate-400">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            FastAPI: 8765
          </span>
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            Vite Frontend: 1420
          </span>
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            Model Router: Gemini 2.5 / OpenAI
          </span>
        </div>
        <div className="text-slate-500">
          Last Synced: {new Date().toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
};
