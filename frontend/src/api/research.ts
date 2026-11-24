import { Citation } from "./chat";
import { API_BASE_URL } from "./client";

export type ResearchResult = {
  topic: string;
  summary: string;
  findingsMarkdown: string;
  citations: Citation[];
  keyTakeaways: string[];
  generatedFileUrl?: string;
  status?: "success" | "partial_success" | "failure" | "unverified";
  synthesisStatus?: "success" | "failure" | "not_attempted";
  sourceStatus?: "none" | "search_results" | "page_content_retrieved";
  documentStatus?: "not_requested" | "generated" | "not_generated" | "unsupported";
  diagnostic?: string | null;
};

export function getResearchOutcome(result: ResearchResult): {
  title: string;
  message: string;
  toastType: "success" | "warning" | "error";
} {
  if (
    result.status === "success"
    && result.synthesisStatus === "success"
    && result.citations?.length
  ) {
    return {
      title: "Research Complete",
      message: `AI synthesis completed with ${result.citations?.length ?? 0} search-result citations. Sources are not independently fact-checked.`,
      toastType: "success",
    };
  }
  if (result.status === "failure") {
    return {
      title: "Research Failed",
      message: result.diagnostic || "No research synthesis or source-backed result was produced.",
      toastType: "error",
    };
  }
  return {
    title: "Research Incomplete",
    message: result.diagnostic || "The result is partial or its completion status could not be verified.",
    toastType: "warning",
  };
}

export async function performDeepResearch(
  query: string,
  depth: "fast" | "deep" | "academic" = "deep",
  generateDocument: "none" | "pdf" = "none",
): Promise<ResearchResult> {
  const backendDepth = depth === "fast" ? "quick" : depth === "academic" ? "comprehensive" : "deep";
  const res = await fetch(`${API_BASE_URL}/research/deep`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, depth: backendDepth, generate_document: generateDocument }),
  });
  if (!res.ok) throw new Error("Deep research failed");
  return res.json();
}
