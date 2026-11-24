import { describe, expect, it } from "vitest";
import { createMicrophoneConstraints } from "./audioConstraints";

describe("createMicrophoneConstraints", () => {
  it("uses the explicitly selected input device", () => {
    expect(createMicrophoneConstraints("mic-1").audio).toMatchObject({
      deviceId: { exact: "mic-1" },
      echoCancellation: { ideal: true },
    });
  });

  it("leaves device selection to the browser when no input is selected", () => {
    expect(createMicrophoneConstraints().audio).not.toHaveProperty("deviceId");
  });
});
