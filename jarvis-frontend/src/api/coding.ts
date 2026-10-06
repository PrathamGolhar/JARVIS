import { API_BASE_URL } from "./client";

export type CodeExecutionResult = {
  ok: boolean;
  stdout: string;
  stderr: string;
  exitCode: number;
  executionTimeMs: number;
  memoryMb?: number;
};

export type CodeAnalysisResult = {
  analysis: string;
  fixedOrImprovedCode: string;
  testCode: string;
  complexityScore: string;
};

export async function executeCode(code: string, language: string = "python", stdinInput: string = ""): Promise<CodeExecutionResult> {
  const res = await fetch(`${API_BASE_URL}/code/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, language, stdinInput }),
  });
  if (!res.ok) throw new Error("Sandbox execution failed");
  return res.json();
}

export async function analyzeCode(code: string, language: string = "python", task: string = "explain"): Promise<CodeAnalysisResult> {
  const res = await fetch(`${API_BASE_URL}/code/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, language, task }),
  });
  if (!res.ok) throw new Error("Code analysis failed");
  return res.json();
}
