import { describe, expect, it } from "vitest";
import { extractWakeWordCommand } from "./voicePreferences";

describe("extractWakeWordCommand", () => {
  it("extracts a command after the wake word", () => {
    expect(extractWakeWordCommand("  Jarvis, summarize this page  ")).toBe("summarize this page");
  });

  it("accepts a spoken greeting before the wake word", () => {
    expect(extractWakeWordCommand("Hey, JARVIS! Open my notes")).toBe("Open my notes");
  });

  it("does not mistake ordinary speech for a wake-word command", () => {
    expect(extractWakeWordCommand("Please open my notes")).toBeNull();
  });
});
