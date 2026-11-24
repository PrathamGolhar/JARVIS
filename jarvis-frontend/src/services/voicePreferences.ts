import { ResponseStyle } from "../api/chat";

const RESPONSE_STYLES: ResponseStyle[] = ["concise", "balanced", "detailed"];

export function extractWakeWordCommand(transcript: string): string | null {
  const match = transcript.trim().match(/^(?:hey[\s,]+)?jarvis\b[\s,.:;!?-]*(.*)$/i);
  return match ? match[1].trim() : null;
}

export function readResponseStyle(): ResponseStyle {
  try {
    const stored = window.localStorage.getItem("jarvis_response_style");
    return RESPONSE_STYLES.includes(stored as ResponseStyle) ? (stored as ResponseStyle) : "balanced";
  } catch {
    return "balanced";
  }
}

export function readBooleanPreference(key: string, fallback: boolean): boolean {
  try {
    const stored = window.localStorage.getItem(key);
    return stored === null ? fallback : stored === "true";
  } catch {
    return fallback;
  }
}

export function readStringPreference(key: string, fallback: string): string {
  try {
    return window.localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

export function savePreference(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    throw new Error("This preference could not be saved in browser storage.");
  }
}
