import { API_BASE_URL } from "./client";

export type DefinitionItem = {
  term: string;
  definition: string;
  example?: string;
};

export type FormulaItem = {
  name: string;
  formula: string;
  explanation: string;
  variables: Record<string, string>;
};

export type MCQItem = {
  id: number;
  question: string;
  options: string[];
  correctOptionIndex: number;
  difficulty: "Easy" | "Medium" | "Hard" | "Exam Level";
  hint?: string;
  solution?: string;
  explanation?: string;
};

export type FlashcardItem = {
  front: string;
  back: string;
  topic?: string;
};

export type StudyNotesResponse = {
  title: string;
  subject: string;
  summary: string;
  keyConcepts: string[];
  definitions: DefinitionItem[];
  formulas: FormulaItem[];
  detailedNotesMarkdown: string;
  practiceQuestions: MCQItem[];
  flashcards: FlashcardItem[];
  generatedFileUrl?: string;
};

export async function fetchStudyNotes(topicOrText: string, subject: string = "General", formatOutput: string = "pdf"): Promise<StudyNotesResponse> {
  const res = await fetch(`${API_BASE_URL}/study/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      topicOrText,
      subject,
      formatOutput,
    }),
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: "Study notes generation failed" }));
    throw new Error(errorBody.detail || `Error ${res.status}`);
  }

  return res.json();
}

export async function fetchExamMcqs(topicOrText: string, count: number = 10, difficulty: string = "Medium"): Promise<MCQItem[]> {
  const res = await fetch(`${API_BASE_URL}/study/mcqs?topic_or_text=${encodeURIComponent(topicOrText)}&count=${count}&difficulty=${encodeURIComponent(difficulty)}`, {
    method: "POST",
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch exam questions: ${res.status}`);
  }

  return res.json();
}
