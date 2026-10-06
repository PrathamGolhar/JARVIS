import React, { useState } from 'react';
import { performDeepResearch, ResearchResult } from '../api/research';
import { CitationsList } from './CitationsList';
import { showToast } from './ToastNotificationSystem';

export const ResearchWorkspace: React.FC = () => {
  const [query, setQuery] = useState('');
  const [depth, setDepth] = useState<'fast' | 'deep' | 'academic'>('deep');
  const [docFormat, setDocFormat] = useState<'none' | 'pdf' | 'docx' | 'pptx' | 'markdown'>('none');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    setIsLoading(true);
    setError(null);
    try {
      showToast({
        title: 'Research Dispatched',
        message: `Investigating "${query}" across verified web sources...`,
        type: 'cyber',
      });
      const data = await performDeepResearch(query, depth, docFormat);
      setResult(data);
      showToast({
        title: 'Research Complete',
        message: `Synthesized findings with ${data.citations?.length ?? 0} citations.`,
        type: 'success',
      });
    } catch (err: any) {
      const msg = err?.message || 'Failed to complete research query';
      setError(msg);
      showToast({
        title: 'Research Error',
        message: msg,
        type: 'error',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const sampleTopics = [
    'Latest breakthroughs in Solid-State Battery technology 2026',
    'Quantum computing fault-tolerance and error correction mechanisms',
    'Autonomous Multi-Agent DAG architectures and verification loops',
    'Edge AI hardware accelerators and NPU benchmarks comparison',
  ];

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 font-sans text-slate-100 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="glass-panel p-6 rounded-2xl border border-cyan-500/30 shadow-xl shadow-cyan-950/20">
        <div className="flex items-center space-x-3 mb-2">
          <div className="w-9 h-9 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-300">
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-black tracking-tight text-white font-mono">
              DEEP RESEARCH & SYNTHESIS CENTER
            </h1>
            <p className="text-xs text-slate-400">
              Live DuckDuckGo scraping, multi-source verification, citation grounding, and automated document compilation.
            </p>
          </div>
        </div>

        {/* Search Form */}
        <form onSubmit={handleSearch} className="mt-4 space-y-3">
          <div className="flex flex-col md:flex-row gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter research topic, question, or technology (e.g. 'Photonic computing vs electronic computing')..."
              className="flex-1 px-4 py-3 rounded-xl bg-slate-950/80 border border-cyan-500/30 focus:border-cyan-400 focus:outline-none text-white text-sm placeholder-slate-500 font-mono shadow-inner"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-slate-950 font-mono font-bold text-xs uppercase tracking-wider flex items-center justify-center space-x-2 transition-all cursor-pointer shadow-lg shadow-cyan-500/20"
            >
              {isLoading ? (
                <>
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <circle cx="12" cy="12" r="4" />
                  </svg>
                  <span>INVESTIGATING...</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M5 12h14" />
                    <path d="m12 5 7 7-7 7" />
                  </svg>
                  <span>DISPATCH RESEARCH</span>
                </>
              )}
            </button>
          </div>

          {/* Depth & Format Options */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 text-xs font-mono text-slate-400">
            <div className="flex items-center space-x-2">
              <span className="text-cyan-400 font-bold">DEPTH:</span>
              {(['fast', 'deep', 'academic'] as const).map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDepth(d)}
                  className={`px-2.5 py-1 rounded-lg uppercase text-[11px] transition-all cursor-pointer ${
                    depth === d
                      ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-500/50'
                      : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-cyan-400 font-bold">EXPORT DOCUMENT:</span>
              {(['none', 'pdf', 'docx', 'pptx', 'markdown'] as const).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setDocFormat(f)}
                  className={`px-2.5 py-1 rounded-lg uppercase text-[11px] transition-all cursor-pointer ${
                    docFormat === f
                      ? 'bg-blue-500/20 text-blue-200 border border-blue-500/50'
                      : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
        </form>

        {/* Quick Topic Chips */}
        <div className="mt-4 pt-3 border-t border-cyan-500/10 flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-mono text-slate-400">Quick queries:</span>
          {sampleTopics.map((topic, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setQuery(topic)}
              className="text-[11px] px-2.5 py-1 rounded-md bg-slate-900/80 hover:bg-cyan-500/10 border border-cyan-500/20 text-slate-300 hover:text-cyan-200 transition-colors cursor-pointer text-left truncate max-w-xs"
            >
              {topic}
            </button>
          ))}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/40 text-rose-300 text-xs font-mono">
          <strong>Research Error:</strong> {error}
        </div>
      )}

      {/* Research Output View */}
      {result && (
        <div className="space-y-6">
          {/* Executive Summary Card */}
          <div className="glass-panel p-6 rounded-2xl border border-cyan-500/30 space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-cyan-500/20 pb-4">
              <div>
                <span className="text-[10px] font-mono font-bold text-cyan-400 uppercase tracking-wider">
                  EXECUTIVE RESEARCH DOSSIER
                </span>
                <h2 className="text-xl font-bold text-white mt-1">{result.topic || query}</h2>
              </div>
              {result.generatedFileUrl && (
                <a
                  href={result.generatedFileUrl}
                  download
                  className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/50 text-emerald-300 text-xs font-mono font-bold transition-all"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  <span>DOWNLOAD ARTIFACT</span>
                </a>
              )}
            </div>

            <div>
              <h3 className="text-xs font-bold font-mono text-cyan-300 uppercase tracking-wider mb-2">
                Executive Synthesis
              </h3>
              <p className="text-sm text-slate-200 leading-relaxed bg-slate-950/50 p-4 rounded-xl border border-cyan-500/10">
                {result.summary}
              </p>
            </div>

            {/* Key Takeaways */}
            {result.keyTakeaways && result.keyTakeaways.length > 0 && (
              <div>
                <h3 className="text-xs font-bold font-mono text-emerald-300 uppercase tracking-wider mb-2">
                  Key Takeaways & Core Insights
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {result.keyTakeaways.map((item, idx) => (
                    <div
                      key={idx}
                      className="flex items-start space-x-2 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-xs text-slate-200"
                    >
                      <span className="text-emerald-400 font-bold mt-0.5">&bull;</span>
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Detailed Findings Markdown */}
          {result.findingsMarkdown && (
            <div className="glass-panel p-6 rounded-2xl border border-cyan-500/20 space-y-3">
              <h3 className="text-xs font-bold font-mono text-cyan-300 uppercase tracking-wider">
                Full Investigated Findings
              </h3>
              <div className="prose prose-invert prose-cyan max-w-none text-xs text-slate-300 leading-relaxed font-sans whitespace-pre-wrap bg-slate-950/60 p-5 rounded-xl border border-slate-800">
                {result.findingsMarkdown}
              </div>
            </div>
          )}

          {/* Grounded Citations List */}
          {result.citations && result.citations.length > 0 && (
            <div className="glass-panel p-6 rounded-2xl border border-cyan-500/20 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold font-mono text-cyan-300 uppercase tracking-wider">
                  Verified Citations ({result.citations.length})
                </h3>
                <span className="text-[10px] text-slate-400 font-mono">100% Grounded Sources</span>
              </div>
              <CitationsList citations={result.citations} />
            </div>
          )}
        </div>
      )}
    </div>
  );
};
