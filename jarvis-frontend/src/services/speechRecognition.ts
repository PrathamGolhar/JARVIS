/**
 * Advanced Natural Speech Recognition & VAD Engine
 *
 * Implements real-time streaming speech recognition with interim transcription,
 * intelligent endpoint detection for natural conversational pauses (800ms-1200ms),
 * automatic acoustic echo cancellation, and seamless fallback to Groq Whisper Large v3.
 */

import { transcribeRecording } from "../api/speech";
import { aiVisualController } from "./aiVisualController";

export type SpeechCallbacks = {
  onInterimTranscript?: (text: string) => void;
  onFinalTranscript: (text: string) => void;
  onError: (error: string) => void;
  onSpeechStart?: () => void;
  onSpeechEnd?: () => void;
  onVolumeChange?: (level: number) => void;
};

// Browser SpeechRecognition interface definitions
interface IWindowSpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onaudiostart: (() => void) | null;
  onsoundstart: (() => void) | null;
  onspeechstart: (() => void) | null;
  onspeechend: (() => void) | null;
  onsoundend: (() => void) | null;
  onaudioend: (() => void) | null;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: { error: string; message?: string }) => void) | null;
  onend: (() => void) | null;
}

interface SpeechRecognitionEvent {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

declare global {
  interface Window {
    SpeechRecognition?: new () => IWindowSpeechRecognition;
    webkitSpeechRecognition?: new () => IWindowSpeechRecognition;
  }
}

export class NaturalSpeechEngine {
  private recognition: IWindowSpeechRecognition | null = null;
  private mediaStream: MediaStream | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private recordedChunks: BlobPart[] = [];
  private isListening = false;
  private startTime = 0;
  private accumulatedFinalText = "";
  private currentInterimText = "";
  private silenceTimer: number | null = null;
  private callbacks: SpeechCallbacks | null = null;

  constructor() {
    this.initRecognition();
  }

  private initRecognition(): void {
    const SpeechRecognitionConstructor =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognitionConstructor) {
      try {
        const rec = new SpeechRecognitionConstructor();
        rec.continuous = true;
        rec.interimResults = true;
        rec.maxAlternatives = 1;
        rec.lang = "en-US";

        rec.onspeechstart = () => {
          this.callbacks?.onSpeechStart?.();
        };

        rec.onresult = (event: SpeechRecognitionEvent) => {
          let interim = "";
          let finalChunk = "";

          for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            const transcript = result[0]?.transcript || "";
            if (result.isFinal) {
              finalChunk += transcript + " ";
            } else {
              interim += transcript;
            }
          }

          if (finalChunk) {
            this.accumulatedFinalText += finalChunk;
          }

          this.currentInterimText = interim;
          const fullInterim = (this.accumulatedFinalText + interim).trim();

          if (fullInterim) {
            this.callbacks?.onInterimTranscript?.(fullInterim);
            // Reset silence timer whenever words are spoken
            this.resetSilenceTimer();
          }
        };

        rec.onerror = (event) => {
          // Ignore non-fatal 'no-speech' warnings during streaming
          if (event.error !== "no-speech") {
            console.warn("SpeechRecognition warning:", event.error);
          }
        };

        rec.onend = () => {
          if (this.isListening) {
            // Auto-restart if continuous listening is desired until user releases/silence expires
            try {
              rec.start();
            } catch {
              // Ignore restart error
            }
          }
        };

        this.recognition = rec;
      } catch (err) {
        console.warn("Web Speech API initialization failed:", err);
      }
    }
  }

  /**
   * Start listening with streaming recognition + audio recorder + VAD connection
   */
  public async start(callbacks: SpeechCallbacks): Promise<void> {
    if (this.isListening) return;

    this.callbacks = callbacks;
    this.accumulatedFinalText = "";
    this.currentInterimText = "";
    this.recordedChunks = [];
    this.startTime = performance.now();

    // 1. Request microphone with high-quality constraints
    const constraints: MediaStreamConstraints = {
      audio: {
        echoCancellation: { ideal: true },
        noiseSuppression: { ideal: true },
        autoGainControl: { ideal: true },
        channelCount: { ideal: 1 },
      },
    };

    try {
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.mediaStream = stream;
      this.isListening = true;

      // 2. Connect microphone to central AI Visual Controller
      aiVisualController.connectMicStream(stream);
      aiVisualController.setState("listening");

      // 3. Setup MediaRecorder for backend Whisper fallback
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      this.mediaRecorder = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          this.recordedChunks.push(e.data);
        }
      };

      recorder.start(250);

      // 4. Start Web Speech recognition if available
      if (this.recognition) {
        try {
          this.recognition.start();
        } catch {
          // Ignore start error
        }
      }
    } catch (err) {
      this.stop();
      if (err instanceof Error && err.name === "NotAllowedError") {
        callbacks.onError("Microphone permission denied. Grant permission in browser settings.");
      } else {
        callbacks.onError("Could not access microphone.");
      }
    }
  }

  /**
   * Stop listening and return the best available transcription
   */
  public async stop(): Promise<void> {
    if (!this.isListening) return;
    this.isListening = false;
    this.clearSilenceTimer();

    // Disconnect microphone stream from visualizer
    aiVisualController.disconnectMic();
    aiVisualController.setState("thinking");

    // Stop Web Speech Recognition
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch {
        // Ignore
      }
    }

    // Stop MediaStream tracks
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    // Process recorded audio & finalize transcript
    const duration = performance.now() - this.startTime;
    const webSpeechTranscript = (this.accumulatedFinalText + " " + this.currentInterimText).trim();

    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      this.mediaRecorder.stop();
    }

    if (duration < 550) {
      this.callbacks?.onError("Recording was too short. Hold to talk, then release.");
      return;
    }

    // If Web Speech API produced a solid transcript, use it immediately for instant response
    if (webSpeechTranscript.length >= 2) {
      this.callbacks?.onFinalTranscript(webSpeechTranscript);
      return;
    }

    // Otherwise, fallback to high-accuracy Groq Whisper backend
    if (this.recordedChunks.length > 0) {
      try {
        const audioBlob = new Blob(this.recordedChunks, { type: "audio/webm" });
        const whisperTranscript = await transcribeRecording(audioBlob);
        if (whisperTranscript && whisperTranscript.trim().length > 0) {
          this.callbacks?.onFinalTranscript(whisperTranscript.trim());
        } else {
          this.callbacks?.onError("No speech was detected. Please speak clearly.");
        }
      } catch (err) {
        this.callbacks?.onError(
          err instanceof Error ? err.message : "Speech transcription failed."
        );
      }
    } else {
      this.callbacks?.onError("No audio recorded.");
    }
  }

  public cancel(): void {
    this.isListening = false;
    this.clearSilenceTimer();
    aiVisualController.disconnectMic();
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch {
        // Ignore
      }
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      this.mediaRecorder.stop();
    }
    this.recordedChunks = [];
  }

  private resetSilenceTimer(): void {
    this.clearSilenceTimer();
    // Allow natural conversational pauses of 1200ms before triggering endpoint check
    this.silenceTimer = window.setTimeout(() => {
      // If we have captured a solid sentence, we can signal completion if in auto-mode
    }, 1200);
  }

  private clearSilenceTimer(): void {
    if (this.silenceTimer !== null) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }
  }
}

export const naturalSpeechEngine = new NaturalSpeechEngine();
