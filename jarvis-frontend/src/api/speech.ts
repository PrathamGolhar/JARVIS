export type Voice = { id: string; label: string };

export type SpeechHealthStatus = {
  status: "ready" | "degraded" | "error";
  sttProvider: string;
  sttAvailable: boolean;
  ttsAvailable: boolean;
  supportedFormats: string[];
};

import { API_BASE_URL, DEMO_MODE } from "./client";

export async function checkSpeechHealth(): Promise<SpeechHealthStatus> {
  try {
    const response = await fetch(`${API_BASE_URL}/speech/health`, { method: "GET" });
    if (!response.ok) {
      return {
        status: "degraded",
        sttProvider: "browser-fallback",
        sttAvailable: false,
        ttsAvailable: true,
        supportedFormats: [],
      };
    }
    return (await response.json()) as SpeechHealthStatus;
  } catch {
    return {
      status: "degraded",
      sttProvider: "browser-fallback",
      sttAvailable: false,
      ttsAvailable: false,
      supportedFormats: [],
    };
  }
}

export async function fetchVoices(): Promise<Voice[]> {
  if (DEMO_MODE) {
    return [
      { id: "demo-guy", label: "Guy — Neural Voice" },
      { id: "demo-jenny", label: "Jenny — Neural Voice" },
    ];
  }
  const response = await fetch(`${API_BASE_URL}/voices`);
  if (!response.ok) throw new Error("Voice catalog is temporarily offline.");
  const body = (await response.json()) as { voices: Voice[] };
  return body.voices;
}

export async function requestSpeech(text: string, voiceId: string): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/tts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voiceId }),
    });
  } catch (err) {
    throw new Error(
      err instanceof Error && err.name === "AbortError"
        ? "Speech synthesis was cancelled."
        : "Speech synthesis connection error."
    );
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail ?? `TTS generation failed (HTTP ${response.status}).`);
  }
  return response.blob();
}

export async function transcribeRecording(audio: Blob): Promise<string> {
  const form = new FormData();
  const fileExt = audio.type.includes("ogg") ? "recording.ogg" : "recording.webm";
  form.append("audio", audio, fileExt);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 20000);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/transcribe`, {
      method: "POST",
      body: form,
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("STT_TIMEOUT: Transcription request timed out after 20 seconds.");
    }
    throw new Error("STT_NETWORK_ERROR: Unable to connect to backend transcription endpoint.");
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    if (response.status === 401) {
      throw new Error("STT_AUTH_ERROR: Groq API key is invalid or unauthorized.");
    }
    if (response.status === 429) {
      throw new Error("STT_RATE_LIMITED: Speech service rate limit exceeded. Retrying shortly.");
    }
    if (response.status === 415) {
      throw new Error(`STT_AUDIO_FORMAT_ERROR: ${body.detail ?? "Unsupported audio format."}`);
    }
    throw new Error(body.detail ?? `STT_SERVER_ERROR: Transcription failed (HTTP ${response.status}).`);
  }

  const data = (await response.json()) as { transcript: string };
  return data.transcript ?? "";
}
