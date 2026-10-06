import { Citation } from "./chat";
import { API_BASE_URL } from "./client";

export type ResearchResult = {
  topic: string;
  summary: string;
  findingsMarkdown: string;
  citations: Citation[];
  keyTakeaways: string[];
  generatedFileUrl?: string;
};

export async function performDeepResearch(query: string, depth: string = "deep", generateDocument: string = "none"): Promise<ResearchResult> {
  const res = await fetch(`${API_BASE_URL}/research/deep`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, depth, generateDocument }),
  });
  if (!res.ok) throw new Error("Deep research failed");
  return res.json();
}
