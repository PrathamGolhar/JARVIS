import { describe, expect, it, vi } from "vitest";
import { getResearchOutcome, performDeepResearch } from "./research";

describe("getResearchOutcome", () => {
  it("reports success only when research and synthesis both succeeded", () => {
    expect(
      getResearchOutcome({
        topic: "topic",
        summary: "summary",
        findingsMarkdown: "findings",
        citations: [{ title: "source", url: "https://example.com" }],
        keyTakeaways: ["finding"],
        status: "success",
        synthesisStatus: "success",
      }),
    ).toMatchObject({
      title: "Research Complete",
      toastType: "success",
    });
  });

  it("does not label partial or unverified results complete", () => {
    expect(
      getResearchOutcome({
        topic: "topic",
        summary: "partial",
        findingsMarkdown: "search snippets",
        citations: [],
        keyTakeaways: [],
        status: "partial_success",
        synthesisStatus: "failure",
      }),
    ).toMatchObject({
      title: "Research Incomplete",
      toastType: "warning",
    });

    expect(
      getResearchOutcome({
        topic: "topic",
        summary: "summary",
        findingsMarkdown: "findings",
        citations: [],
        keyTakeaways: ["finding"],
        status: "success",
        synthesisStatus: "success",
      }),
    ).toMatchObject({
      title: "Research Incomplete",
      toastType: "warning",
    });

    expect(
      getResearchOutcome({
        topic: "topic",
        summary: "unknown",
        findingsMarkdown: "unknown",
        citations: [],
        keyTakeaways: [],
      }),
    ).toMatchObject({
      title: "Research Incomplete",
      toastType: "warning",
    });
  });

  it("reports a failed research response as an error", () => {
    expect(
      getResearchOutcome({
        topic: "topic",
        summary: "unavailable",
        findingsMarkdown: "no sources",
        citations: [],
        keyTakeaways: [],
        status: "failure",
        synthesisStatus: "not_attempted",
      }),
    ).toMatchObject({
      title: "Research Failed",
      toastType: "error",
    });
  });

  it("maps UI research options to the backend request contract", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        topic: "topic",
        summary: "summary",
        findingsMarkdown: "findings",
        citations: [{ title: "source", url: "https://example.com" }],
        keyTakeaways: ["finding"],
        status: "success",
        synthesisStatus: "success",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    try {
      await performDeepResearch("topic", "fast", "pdf");
      const request = JSON.parse(fetchMock.mock.calls[0][1].body);
      expect(request).toEqual({
        query: "topic",
        depth: "quick",
        generate_document: "pdf",
      });
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
