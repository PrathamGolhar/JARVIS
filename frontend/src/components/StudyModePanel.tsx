import React, { useState } from "react";
import { fetchStudyNotes, DefinitionItem, FormulaItem, MCQItem, StudyNotesResponse } from "../api/study";
import { showToast } from "./ToastNotificationSystem";

type StudyModePanelProps = {
  onClose: () => void;
};

export function StudyModePanel({ onClose }: StudyModePanelProps) {
  const [topic, setTopic] = useState("");
  const [subject, setSubject] = useState("Physics & Engineering");
  const [loading, setLoading] = useState(false);
  const [notesData, setNotesData] = useState<StudyNotesResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"notes" | "quiz" | "formulas" | "flashcards">("notes");
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, number>>({});
  const [showHints, setShowHints] = useState<Record<number, boolean>>({});
  const [showExplanations, setShowExplanations] = useState<Record<number, boolean>>({});
  const [flashcardIndex, setFlashcardIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);

  const handleGenerate = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    try {
      showToast({
        title: "Study Agent Engaged",
        message: `Synthesizing curriculum and exam MCQs for "${topic}"...`,
        type: "cyber",
      });
      const res = await fetchStudyNotes(topic, subject, "pdf");
      setNotesData(res);
      setSelectedAnswers({});
      setShowHints({});
      setShowExplanations({});
      setFlashcardIndex(0);
      setIsFlipped(false);
      showToast({
        title: "Study Suite Ready",
        message: `Generated ${res.keyConcepts?.length ?? 0} key concepts & ${res.practiceQuestions?.length ?? 0} MCQs.`,
        type: "success",
      });
    } catch (err) {
      showToast({
        title: "Generation Error",
        message: err instanceof Error ? err.message : "Failed to generate study materials",
        type: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const calculateScore = () => {
    if (!notesData || !notesData.practiceQuestions?.length) return { correct: 0, total: 0 };
    let correct = 0;
    notesData.practiceQuestions.forEach((q) => {
      if (selectedAnswers[q.id] === q.correctOptionIndex) {
        correct++;
      }
    });
    return { correct, total: notesData.practiceQuestions.length };
  };

  const score = calculateScore();

  return (
    <div className="modal-overlay-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="study-title">
      <div className="modal-dialog-card flex flex-col font-sans" style={{ maxWidth: "58rem", height: "88vh" }} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header-row">
          <div className="modal-header-title">
            <div className="w-8 h-8 rounded-lg bg-teal-500/20 border border-teal-500/40 flex items-center justify-center text-teal-300">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
                <path d="M6 6h10" />
                <path d="M6 10h10" />
              </svg>
            </div>
            <div>
              <h2 id="study-title" className="text-base font-bold text-white tracking-wide font-mono">
                JARVIS STUDY & ACADEMIC SUITE
              </h2>
              <p className="text-xs text-slate-400">
                Autonomous in-depth note synthesis, formula derivations & interactive exam preparation
              </p>
            </div>
          </div>
          <button onClick={onClose} className="modal-close-btn font-mono" aria-label="Close Study Suite">
            ✕
          </button>
        </div>

        {/* Input / Control Bar */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-cyan-500/20 flex flex-wrap gap-3 items-center mb-4">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Enter topic, chapter or concept (e.g., Quantum Computing, Fourier Transforms)..."
            className="flex-1 min-w-[240px] px-3.5 py-2.5 rounded-lg bg-slate-900 border border-cyan-500/30 text-white text-xs font-mono focus:border-cyan-400 focus:outline-none placeholder-slate-500"
            disabled={loading}
          />
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Subject / Field"
            className="w-48 px-3.5 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs font-mono focus:border-cyan-400 focus:outline-none placeholder-slate-500"
            disabled={loading}
          />
          <button
            onClick={handleGenerate}
            disabled={loading || !topic.trim()}
            className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-400 hover:to-cyan-400 disabled:opacity-50 text-slate-950 font-mono font-bold text-xs uppercase tracking-wider transition-all cursor-pointer shadow-lg shadow-teal-500/20 flex items-center space-x-2"
          >
            {loading ? (
              <>
                <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <circle cx="12" cy="12" r="4" />
                </svg>
                <span>SYNTHESIZING...</span>
              </>
            ) : (
              <span>✨ GENERATE SUITE</span>
            )}
          </button>
        </div>

        {/* Navigation Tabs */}
        {notesData && (
          <div className="flex items-center justify-between border-b border-cyan-500/20 mb-4 pb-2">
            <div className="flex space-x-2">
              {[
                { id: "notes", label: "📖 DETAILED NOTES" },
                { id: "quiz", label: `🎯 EXAM QUIZ (${notesData.practiceQuestions?.length ?? 0})` },
                { id: "formulas", label: `⚡ FORMULAS (${notesData.formulas?.length ?? 0})` },
                { id: "flashcards", label: `🃏 FLASHCARDS (${notesData.flashcards?.length ?? 0})` },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-3 py-1.5 rounded-md font-mono text-xs font-semibold transition-all cursor-pointer ${
                    activeTab === tab.id
                      ? "bg-cyan-500/20 text-cyan-200 border border-cyan-500/50 shadow-sm shadow-cyan-500/20"
                      : "text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {notesData.generatedFileUrl && (
              <a
                href={notesData.generatedFileUrl}
                target="_blank"
                rel="noreferrer"
                download
                className="px-3 py-1 rounded bg-teal-500/20 hover:bg-teal-500/30 border border-teal-500/50 text-teal-300 text-xs font-mono font-semibold transition-colors flex items-center gap-1.5"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                <span>DOWNLOAD PDF</span>
              </a>
            )}
          </div>
        )}

        {/* Tab Content Stage */}
        <div className="flex-1 overflow-y-auto pr-2 space-y-4">
          {!notesData && !loading && (
            <div className="h-64 flex flex-col items-center justify-center text-center p-8 border border-dashed border-cyan-500/20 rounded-xl bg-slate-950/40">
              <div className="w-12 h-12 rounded-full bg-cyan-500/10 flex items-center justify-center text-cyan-400 mb-3">
                <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                </svg>
              </div>
              <h3 className="text-sm font-bold text-white font-mono mb-1">NO STUDY MATERIAL LOADED</h3>
              <p className="text-xs text-slate-400 max-w-md">
                Enter any academic topic or upload syllabus materials above. JARVIS Study Agent will formulate structured notes, derivations, practice questions, and flashcards.
              </p>
            </div>
          )}

          {notesData && activeTab === "notes" && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-900/60 border border-cyan-500/20">
                <h3 className="text-xs font-mono font-bold text-cyan-300 uppercase mb-2">Executive Summary</h3>
                <p className="text-sm text-slate-200 leading-relaxed">{notesData.summary}</p>
              </div>

              {notesData.keyConcepts && notesData.keyConcepts.length > 0 && (
                <div className="p-4 rounded-xl bg-slate-900/60 border border-cyan-500/20">
                  <h3 className="text-xs font-mono font-bold text-cyan-300 uppercase mb-3">Key Concepts & Principles</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                    {notesData.keyConcepts.map((item: string, idx: number) => (
                      <div key={idx} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-start space-x-2">
                        <span className="text-teal-400 font-mono font-bold text-xs">#{idx + 1}</span>
                        <span className="text-xs text-slate-300">{item}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {notesData.definitions && notesData.definitions.length > 0 && (
                <div className="p-4 rounded-xl bg-slate-900/60 border border-cyan-500/20">
                  <h3 className="text-xs font-mono font-bold text-cyan-300 uppercase mb-3">Core Definitions</h3>
                  <div className="space-y-2.5">
                    {notesData.definitions.map((def: DefinitionItem, idx: number) => (
                      <div key={idx} className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 space-y-1">
                        <span className="text-xs font-bold text-teal-300 font-mono">{def.term}</span>
                        <p className="text-xs text-slate-300 leading-relaxed">{def.definition}</p>
                        {def.example && <p className="text-[11px] text-slate-400 italic">Example: {def.example}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {notesData.detailedNotesMarkdown && (
                <div className="p-4 rounded-xl bg-slate-900/60 border border-cyan-500/20">
                  <h3 className="text-xs font-mono font-bold text-cyan-300 uppercase mb-3">Detailed Curriculum Notes</h3>
                  <div className="p-4 rounded-lg bg-slate-950/80 border border-slate-800 text-xs text-slate-300 leading-relaxed whitespace-pre-line font-mono">
                    {notesData.detailedNotesMarkdown}
                  </div>
                </div>
              )}
            </div>
          )}

          {notesData && activeTab === "quiz" && (
            <div className="space-y-4">
              {/* Score Header */}
              <div className="p-3.5 rounded-xl bg-slate-900/80 border border-cyan-500/30 flex items-center justify-between font-mono text-xs">
                <span className="text-slate-400">PRACTICE EXAM PROGRESS:</span>
                <span className="text-teal-300 font-bold">
                  Score: {score.correct} / {score.total} ({score.total > 0 ? Math.round((score.correct / score.total) * 100) : 0}%)
                </span>
              </div>

              <div className="space-y-4">
                {notesData.practiceQuestions.map((q: MCQItem, qIdx: number) => {
                  const userAns = selectedAnswers[q.id];
                  const isAnswered = userAns !== undefined;
                  const isCorrect = userAns === q.correctOptionIndex;

                  return (
                    <div
                      key={q.id}
                      className={`p-4 rounded-xl border transition-all ${
                        !isAnswered
                          ? "bg-slate-900/60 border-cyan-500/20"
                          : isCorrect
                          ? "bg-emerald-950/20 border-emerald-500/40"
                          : "bg-rose-950/20 border-rose-500/40"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2 mb-3">
                        <span className="text-xs font-bold font-mono text-cyan-300">
                          Q{qIdx + 1}. {q.question}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-800 text-slate-400 uppercase">
                          {q.difficulty || "Standard"}
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-3">
                        {q.options.map((opt: string, oIdx: number) => {
                          const isSelected = userAns === oIdx;
                          const isOptionCorrect = oIdx === q.correctOptionIndex;

                          let btnStyle = "bg-slate-950/60 border-slate-800 text-slate-300 hover:border-cyan-500/40";
                          if (isAnswered) {
                            if (isOptionCorrect) btnStyle = "bg-emerald-500/20 border-emerald-500/60 text-emerald-200 font-bold";
                            else if (isSelected) btnStyle = "bg-rose-500/20 border-rose-500/60 text-rose-200";
                            else btnStyle = "opacity-50 bg-slate-950/40 border-slate-800 text-slate-500";
                          }

                          return (
                            <button
                              key={oIdx}
                              onClick={() => {
                                if (!isAnswered) {
                                  setSelectedAnswers((prev) => ({ ...prev, [q.id]: oIdx }));
                                }
                              }}
                              disabled={isAnswered}
                              className={`p-2.5 rounded-lg border text-left text-xs font-mono transition-all cursor-pointer flex items-center gap-2 ${btnStyle}`}
                            >
                              <span className="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center text-[10px] font-bold">
                                {String.fromCharCode(65 + oIdx)}
                              </span>
                              <span>{opt}</span>
                            </button>
                          );
                        })}
                      </div>

                      {/* Hint & Explanation Toggles */}
                      <div className="flex items-center space-x-3 text-[11px] font-mono">
                        {q.hint && (
                          <button
                            onClick={() => setShowHints((prev) => ({ ...prev, [q.id]: !prev[q.id] }))}
                            className="text-amber-400 hover:text-amber-300 underline cursor-pointer"
                          >
                            {showHints[q.id] ? "Hide Hint" : "💡 View Hint"}
                          </button>
                        )}

                        {isAnswered && (
                          <button
                            onClick={() => setShowExplanations((prev) => ({ ...prev, [q.id]: !prev[q.id] }))}
                            className="text-teal-400 hover:text-teal-300 underline cursor-pointer"
                          >
                            {showExplanations[q.id] ? "Hide Explanation" : "📖 View Rationale"}
                          </button>
                        )}
                      </div>

                      {showHints[q.id] && q.hint && (
                        <div className="mt-2 p-2.5 rounded bg-amber-950/30 border border-amber-500/30 text-xs text-amber-200">
                          {q.hint}
                        </div>
                      )}

                      {showExplanations[q.id] && (q.explanation || q.solution) && (
                        <div className="mt-2 p-2.5 rounded bg-cyan-950/30 border border-cyan-500/30 text-xs text-cyan-200">
                          {q.explanation || q.solution}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {notesData && activeTab === "formulas" && (
            <div className="space-y-3">
              {notesData.formulas.map((f: FormulaItem, idx: number) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-900/60 border border-cyan-500/20 space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-teal-300 font-mono">{f.name}</h4>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
                      FORMULA
                    </span>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-sm text-cyan-400 text-center font-bold">
                    {f.formula}
                  </div>
                  {f.explanation && <p className="text-xs text-slate-400">{f.explanation}</p>}
                  {f.variables && Object.keys(f.variables).length > 0 && (
                    <div className="mt-2 pt-2 border-t border-slate-800/80 flex flex-wrap gap-2 text-[11px] font-mono text-slate-400">
                      {Object.entries(f.variables).map(([k, v]) => (
                        <span key={k} className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800">
                          <strong className="text-cyan-300">{k}:</strong> {v}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {notesData && activeTab === "flashcards" && notesData.flashcards?.length > 0 && (
            <div className="flex flex-col items-center justify-center py-6 space-y-4">
              <div className="text-xs font-mono text-slate-400">
                Card {flashcardIndex + 1} of {notesData.flashcards.length}
              </div>

              <div
                onClick={() => setIsFlipped((prev) => !prev)}
                className="w-full max-w-lg h-64 p-8 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-950 border border-cyan-500/40 shadow-xl shadow-cyan-950/40 flex flex-col items-center justify-center text-center cursor-pointer transition-transform hover:scale-[1.02]"
              >
                <span className="text-[10px] font-mono font-bold text-cyan-400 uppercase tracking-wider mb-2">
                  {isFlipped ? "ANSWER / DEFINITION" : "PROMPT / CONCEPT (CLICK TO FLIP)"}
                </span>
                <p className="text-base font-semibold text-white">
                  {isFlipped
                    ? notesData.flashcards[flashcardIndex].back
                    : notesData.flashcards[flashcardIndex].front}
                </p>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={() => {
                    setIsFlipped(false);
                    setFlashcardIndex((prev) => (prev > 0 ? prev - 1 : notesData.flashcards.length - 1));
                  }}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-mono text-xs transition-colors cursor-pointer"
                >
                  &larr; Previous
                </button>
                <button
                  onClick={() => setIsFlipped((prev) => !prev)}
                  className="px-4 py-2 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/50 text-cyan-200 font-mono text-xs font-bold transition-colors cursor-pointer"
                >
                  Flip Card (Space)
                </button>
                <button
                  onClick={() => {
                    setIsFlipped(false);
                    setFlashcardIndex((prev) => (prev < notesData.flashcards.length - 1 ? prev + 1 : 0));
                  }}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-mono text-xs transition-colors cursor-pointer"
                >
                  Next &rarr;
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
