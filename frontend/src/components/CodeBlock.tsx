import React, { useState } from "react";
import { executeCode } from "../api/coding";

type CodeBlockProps = {
  code: string;
  language?: string;
};

export function CodeBlock({ code, language = "python" }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [output, setOutput] = useState<{ stdout: string; stderr: string; timeMs: number; ok?: boolean } | null>(null);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExecute = async () => {
    setExecuting(true);
    try {
      const res = await executeCode(code, language);
      setOutput({
        stdout: res.stdout,
        stderr: res.stderr,
        timeMs: res.executionTimeMs,
        ok: res.ok,
      });
    } catch (err) {
      setOutput({
        stdout: "",
        stderr: `Execution error: ${err instanceof Error ? err.message : String(err)}`,
        timeMs: 0,
        ok: false,
      });
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="my-2.5 rounded-xl border border-cyan-500/25 bg-slate-950/90 overflow-hidden shadow-lg shadow-cyan-950/20 font-mono text-xs">
      {/* Code Header Bar */}
      <div className="flex items-center justify-between px-3.5 py-2 bg-slate-900/90 border-b border-cyan-500/15">
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400/80 shadow-sm shadow-cyan-400/50" />
          <span className="font-bold text-cyan-300 uppercase tracking-wider text-[11px]">
            {language}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleExecute}
            disabled={executing}
            className="px-2.5 py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/50 text-emerald-300 font-bold text-[10px] tracking-wider transition-colors cursor-pointer disabled:opacity-50"
          >
            {executing ? "▶ RUNNING..." : "▶ RUN IN SANDBOX"}
          </button>
          <button
            onClick={handleCopy}
            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-[10px] font-semibold transition-colors cursor-pointer"
          >
            {copied ? "✓ COPIED" : "📋 COPY"}
          </button>
        </div>
      </div>

      {/* Code Body */}
      <pre className="p-3.5 overflow-x-auto text-[12px] leading-relaxed text-slate-100 selection:bg-cyan-500/30 selection:text-white">
        <code>{code}</code>
      </pre>

      {/* Execution Output Drawer */}
      {output && (
        <div className="p-3 bg-slate-950 border-t border-cyan-500/20 text-xs">
          <div className="flex items-center justify-between text-slate-400 mb-1.5 text-[10px]">
            <span className="font-bold text-cyan-300">SANDBOX TERMINAL OUTPUT</span>
            <span>{output.timeMs} ms</span>
          </div>
          {output.stdout && (
            <pre className="text-emerald-400 whitespace-pre-wrap font-mono text-[11px] leading-relaxed">{output.stdout}</pre>
          )}
          {output.stderr && (
            <pre className="text-rose-400 whitespace-pre-wrap font-mono text-[11px] leading-relaxed">{output.stderr}</pre>
          )}
        </div>
      )}
    </div>
  );
}
