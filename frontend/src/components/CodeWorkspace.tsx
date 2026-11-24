import React, { useState } from 'react';
import { executeCode, analyzeCode, CodeExecutionResult, CodeAnalysisResult } from '../api/coding';
import { CodeBlock } from './CodeBlock';
import { showToast } from './ToastNotificationSystem';

export const CodeWorkspace: React.FC = () => {
  const [language, setLanguage] = useState('python');
  const [code, setCode] = useState(
    `# JARVIS 2.0 Python Sandbox Runtime\nimport sys\nimport math\n\ndef compute_fibonacci_primes(limit=50):\n    def is_prime(n):\n        if n < 2: return False\n        for i in range(2, int(math.isqrt(n)) + 1):\n            if n % i == 0: return False\n        return True\n\n    a, b = 0, 1\n    primes = []\n    while a < limit:\n        if is_prime(a):\n            primes.append(a)\n        a, b = b, a + b\n    return primes\n\nprint("JARVIS Sandbox Executing...")\nresult = compute_fibonacci_primes(1000)\nprint(f"Fibonacci primes < 1000: {result}")\n`
  );
  const [stdin, setStdin] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [execResult, setExecResult] = useState<CodeExecutionResult | null>(null);
  const [analysisResult, setAnalysisResult] = useState<CodeAnalysisResult | null>(null);

  const handleRun = async () => {
    if (!code.trim() || isExecuting) return;
    setIsExecuting(true);
    setExecResult(null);
    try {
      showToast({
        title: 'Sandbox Execution',
        message: `Executing ${language} script in secure sandbox runtime...`,
        type: 'cyber',
      });
      const res = await executeCode(code, language, stdin);
      setExecResult(res);
      showToast({
        title: res.ok ? 'Execution Succeeded' : 'Execution Error',
        message: `Exit Code ${res.exitCode} (${res.executionTimeMs}ms)`,
        type: res.ok ? 'success' : 'error',
      });
    } catch (err: any) {
      showToast({
        title: 'Sandbox Failed',
        message: err?.message || 'Execution failed',
        type: 'error',
      });
    } finally {
      setIsExecuting(false);
    }
  };

  const handleAnalyze = async (task: 'explain' | 'fix' | 'test') => {
    if (!code.trim() || isAnalyzing) return;
    setIsAnalyzing(true);
    try {
      showToast({
        title: 'AST AI Analysis',
        message: `Running static AST and ${task} pipeline...`,
        type: 'info',
      });
      const res = await analyzeCode(code, language, task);
      setAnalysisResult(res);
      showToast({
        title: 'Analysis Ready',
        message: `Complexity rating: ${res.complexityScore || 'Optimized'}`,
        type: 'success',
      });
    } catch (err: any) {
      showToast({
        title: 'Analysis Error',
        message: err?.message || 'Analysis failed',
        type: 'error',
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const applyFixedCode = () => {
    if (analysisResult?.fixedOrImprovedCode) {
      setCode(analysisResult.fixedOrImprovedCode);
      showToast({
        title: 'Code Updated',
        message: 'Applied AI refactored code to the active editor.',
        type: 'success',
      });
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 font-sans text-slate-100 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="glass-panel p-6 rounded-2xl border border-violet-500/30 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl shadow-violet-950/20">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-violet-500/20 border border-violet-500/40 flex items-center justify-center text-violet-300">
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="16 18 22 12 16 6" />
              <polyline points="8 6 2 12 8 18" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-black tracking-tight text-white font-mono">
              JARVIS CODE SANDBOX & AST ANALYZER
            </h1>
            <p className="text-xs text-slate-400">
              Isolated subprocess execution, static AST analysis, automated refactoring, and test synthesis.
            </p>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="px-3 py-2 rounded-xl bg-slate-950/80 border border-violet-500/30 text-xs font-mono text-violet-300 focus:outline-none"
          >
            <option value="python">Python 3.11</option>
            <option value="javascript">Node.js JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="bash">Bash / Shell</option>
            <option value="sql">SQLite / SQL</option>
          </select>

          <button
            onClick={() => handleAnalyze('fix')}
            disabled={isAnalyzing}
            className="px-3 py-2 rounded-xl bg-violet-500/20 hover:bg-violet-500/30 border border-violet-500/50 text-violet-200 text-xs font-mono font-semibold transition-all cursor-pointer"
          >
            AUTO-FIX & OPTIMIZE
          </button>

          <button
            onClick={() => handleAnalyze('test')}
            disabled={isAnalyzing}
            className="px-3 py-2 rounded-xl bg-violet-500/20 hover:bg-violet-500/30 border border-violet-500/50 text-violet-200 text-xs font-mono font-semibold transition-all cursor-pointer"
          >
            GENERATE TESTS
          </button>

          <button
            onClick={handleRun}
            disabled={isExecuting}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-mono font-bold text-xs uppercase tracking-wider flex items-center space-x-2 transition-all cursor-pointer shadow-lg shadow-emerald-500/20"
          >
            {isExecuting ? (
              <>
                <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <circle cx="12" cy="12" r="4" />
                </svg>
                <span>EXECUTING...</span>
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                <span>RUN SANDBOX</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Editor & Console Split Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Editor Column */}
        <div className="glass-panel p-4 rounded-2xl border border-violet-500/20 flex flex-col space-y-3">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 border-b border-violet-500/10 pb-2">
            <span className="text-violet-300 font-bold">SOURCE CODE EDITOR</span>
            <span>Lines: {code.split('\n').length}</span>
          </div>

          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Write or paste your code here..."
            className="w-full h-96 p-4 rounded-xl bg-slate-950/90 border border-violet-500/30 font-mono text-xs text-violet-100 focus:border-violet-400 focus:outline-none resize-none leading-relaxed shadow-inner"
            spellCheck={false}
          />

          <div>
            <label className="text-[11px] font-mono text-slate-400 block mb-1">Standard Input (stdin optional):</label>
            <input
              type="text"
              value={stdin}
              onChange={(e) => setStdin(e.target.value)}
              placeholder="e.g. input lines for sys.stdin"
              className="w-full px-3 py-2 rounded-lg bg-slate-950/80 border border-slate-800 text-xs font-mono text-slate-200 focus:outline-none"
            />
          </div>
        </div>

        {/* Output Console Column */}
        <div className="glass-panel p-4 rounded-2xl border border-violet-500/20 flex flex-col space-y-3">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 border-b border-violet-500/10 pb-2">
            <span className="text-emerald-300 font-bold">SANDBOX CONSOLE / STDOUT</span>
            {execResult && (
              <div className="flex items-center space-x-2">
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    execResult.ok ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                  }`}
                >
                  EXIT {execResult.exitCode}
                </span>
                <span className="text-[10px] text-slate-500">{execResult.executionTimeMs}ms</span>
              </div>
            )}
          </div>

          <div className="w-full h-96 p-4 rounded-xl bg-slate-950/90 border border-slate-800 font-mono text-xs overflow-y-auto space-y-2 shadow-inner">
            {isExecuting ? (
              <div className="flex items-center space-x-2 text-cyan-400 animate-pulse">
                <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <circle cx="12" cy="12" r="4" />
                </svg>
                <span>Executing payload in isolated runtime...</span>
              </div>
            ) : execResult ? (
              <>
                {execResult.stdout && (
                  <pre className="text-emerald-300 whitespace-pre-wrap leading-relaxed">{execResult.stdout}</pre>
                )}
                {execResult.stderr && (
                  <pre className="text-rose-400 whitespace-pre-wrap leading-relaxed border-t border-rose-500/20 pt-2">
                    {execResult.stderr}
                  </pre>
                )}
                {!execResult.stdout && !execResult.stderr && (
                  <span className="text-slate-600">Process completed with no output.</span>
                )}
              </>
            ) : (
              <span className="text-slate-600">Click &quot;RUN SANDBOX&quot; to execute code.</span>
            )}
          </div>

          <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 pt-1">
            <span>Runtime: Subprocess Sandbox</span>
            <button
              onClick={() => setExecResult(null)}
              className="text-slate-400 hover:text-slate-200 cursor-pointer"
            >
              Clear Console
            </button>
          </div>
        </div>
      </div>

      {/* AST & AI Refactoring Results */}
      {analysisResult && (
        <div className="glass-panel p-6 rounded-2xl border border-violet-500/30 space-y-4">
          <div className="flex items-center justify-between border-b border-violet-500/20 pb-3">
            <div>
              <h3 className="text-sm font-bold font-mono text-violet-300 uppercase">
                AI Static Analysis & Optimization Insights
              </h3>
              <p className="text-xs text-slate-400">
                Complexity rating: <strong className="text-white">{analysisResult.complexityScore || 'O(n)'}</strong>
              </p>
            </div>
            {analysisResult.fixedOrImprovedCode && (
              <button
                onClick={applyFixedCode}
                className="px-4 py-1.5 rounded-xl bg-violet-500/20 hover:bg-violet-500/30 border border-violet-500/50 text-violet-200 text-xs font-mono font-bold transition-all cursor-pointer"
              >
                APPLY CODE TO EDITOR &rarr;
              </button>
            )}
          </div>

          <div className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-4 rounded-xl border border-violet-500/10 whitespace-pre-wrap font-sans">
            {analysisResult.analysis}
          </div>

          {analysisResult.fixedOrImprovedCode && (
            <div>
              <h4 className="text-xs font-bold font-mono text-cyan-300 uppercase mb-2">Optimized Code</h4>
              <CodeBlock code={analysisResult.fixedOrImprovedCode} language={language} />
            </div>
          )}

          {analysisResult.testCode && (
            <div>
              <h4 className="text-xs font-bold font-mono text-emerald-300 uppercase mb-2">Generated Test Suite</h4>
              <CodeBlock code={analysisResult.testCode} language={language} />
            </div>
          )}
        </div>
      )}
    </div>
  );
};
