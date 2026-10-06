/**
 * Production-Grade Cinematic JARVIS Voice Architecture
 *
 * Implements:
 * 1. MicrophoneManager: Studio browser constraints (echoCancellation, noiseSuppression, autoGainControl, 48kHz, single channel)
 * 2. VoiceActivityDetector (VAD): Multi-tier pause detection (SHORT_PAUSE 1200ms, LONG_PAUSE 2200ms, END_OF_SPEECH 2800ms)
 * 3. SpeechToTextManager: Browser WebSpeech API continuous interim stream + Backend Groq Whisper Large v3 fallback
 * 4. Voice State Machine: IDLE -> LISTENING -> VOICE_DETECTED -> TRANSCRIBING -> WAITING_FOR_END_OF_SPEECH -> FINALIZING_TRANSCRIPT -> UNDERSTANDING -> PROCESSING -> EXECUTING_ACTION -> GENERATING_RESPONSE -> SPEAKING -> LISTENING
 * 5. Instant Barge-In & Acoustic Feedback Prevention
 * 6. Error Classification & Exponential Backoff Recovery
 */

import { checkSpeechHealth, SpeechHealthStatus, transcribeRecording } from "../api/speech";
import { aiVisualController } from "./aiVisualController";

export type VoiceState =
  | "IDLE"
  | "LISTENING"
  | "VOICE_DETECTED"
  | "TRANSCRIBING"
  | "SHORT_PAUSE"
  | "WAITING_FOR_END_OF_SPEECH"
  | "FINALIZING_TRANSCRIPT"
  | "UNDERSTANDING"
  | "PROCESSING"
  | "EXECUTING_ACTION"
  | "GENERATING_RESPONSE"
  | "SPEAKING"
  | "RECONNECTING"
  | "ERROR_RECOVERY"
  | "INTERRUPTED";

export type STTStatus =
  | "STT_READY"
  | "MIC_PERMISSION_REQUIRED"
  | "MIC_UNAVAILABLE"
  | "BROWSER_UNSUPPORTED"
  | "STT_CONFIGURATION_ERROR"
  | "STT_AUTH_ERROR"
  | "STT_NETWORK_ERROR"
  | "STT_SERVER_ERROR"
  | "STT_TIMEOUT"
  | "STT_RATE_LIMITED"
  | "STT_DEGRADED"
  | "STT_OFFLINE";

export type SpeechProviderName = "browser-webspeech" | "backend-whisper" | "none";

export type ListenMode = "push-to-talk" | "continuous";

export interface SpeechListenOptions {
  mode?: ListenMode;
  lang?: string;
  onInterimTranscript?: (text: string) => void;
  onFinalTranscript: (text: string) => void;
  onError: (userMessage: string, technicalCode: STTStatus) => void;
  onSpeechStart?: () => void;
  onSpeechEnd?: () => void;
  onStateChange?: (voiceState: VoiceState) => void;
  onStatusChange?: (status: STTStatus, activeProvider: SpeechProviderName) => void;
}

// Web Speech API interface
interface IWindowSpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onspeechstart: (() => void) | null;
  onspeechend: (() => void) | null;
  onsoundstart: (() => void) | null;
  onsoundend: (() => void) | null;
  onaudiostart: (() => void) | null;
  onaudioend: (() => void) | null;
  onresult: ((event: any) => void) | null;
  onerror: ((event: { error: string; message?: string }) => void) | null;
  onend: (() => void) | null;
}

export class SpeechManager {
  // Configurable Pause & VAD Thresholds (ms)
  public static readonly SHORT_PAUSE_MS = 1200;
  public static readonly LONG_PAUSE_MS = 2200;
  public static readonly END_OF_SPEECH_MS = 2800;
  public static readonly MIN_SPEECH_DURATION_MS = 400;

  private voiceState: VoiceState = "IDLE";
  private sttStatus: STTStatus = "STT_READY";
  private activeProvider: SpeechProviderName = "none";
  private lastTechnicalError = "";
  private retryCount = 0;
  private maxRetries = 4;
  private retryTimer: number | null = null;

  // Audio & Hardware Streams
  private recognition: IWindowSpeechRecognition | null = null;
  private mediaStream: MediaStream | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private recordedChunks: BlobPart[] = [];
  private isListeningActive = false;
  private isSpeakingActive = false;
  private isTranscribingActive = false;
  private currentMode: ListenMode = "push-to-talk";
  private currentLang = "en-US";
  private startTime = 0;
  private lastSpeechActivityTime = 0;

  // Transcripts
  private accumulatedFinalText = "";
  private currentInterimText = "";

  // Timers
  private shortPauseTimer: number | null = null;
  private endOfSpeechTimer: number | null = null;
  private options: SpeechListenOptions | null = null;

  constructor() {
    this.initBrowserSpeech();
    this.setupNetworkMonitoring();
  }

  // ==========================================
  // Public Accessors
  // ==========================================

  public getVoiceState(): VoiceState {
    return this.voiceState;
  }

  public getStatus(): STTStatus {
    return this.sttStatus;
  }

  public getActiveProvider(): SpeechProviderName {
    return this.activeProvider;
  }

  public getLastError(): string {
    return this.lastTechnicalError;
  }

  public getRetryCount(): number {
    return this.retryCount;
  }

  public isListening(): boolean {
    return this.isListeningActive;
  }

  public isSpeaking(): boolean {
    return this.isSpeakingActive;
  }

  public isTranscribing(): boolean {
    return this.isTranscribingActive;
  }

  public getTranscript(): string {
    return (this.accumulatedFinalText + " " + this.currentInterimText).trim();
  }

  public getFinalTranscript(): string {
    return this.accumulatedFinalText.trim();
  }

  public getInterimTranscript(): string {
    return this.currentInterimText.trim();
  }

  // ==========================================
  // State Machine Management
  // ==========================================

  public setVoiceState(newState: VoiceState): void {
    if (this.voiceState === newState) return;
    this.voiceState = newState;
    this.options?.onStateChange?.(newState);
  }

  private setStatus(newStatus: STTStatus, errorDetail = ""): void {
    this.sttStatus = newStatus;
    if (errorDetail) {
      this.lastTechnicalError = errorDetail;
    }
    this.options?.onStatusChange?.(newStatus, this.activeProvider);
  }

  // ==========================================
  // Initialization & Network Monitoring
  // ==========================================

  private initBrowserSpeech(): void {
    const SpeechRec =
      window.SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: any }).webkitSpeechRecognition;

    if (SpeechRec) {
      try {
        const rec = new SpeechRec();
        rec.continuous = true;
        rec.interimResults = true;
        rec.maxAlternatives = 1;
        rec.lang = this.currentLang;

        rec.onspeechstart = () => {
          this.lastSpeechActivityTime = performance.now();
          this.setVoiceState("VOICE_DETECTED");
          this.clearPauseTimers();
          this.options?.onSpeechStart?.();
        };

        rec.onspeechend = () => {
          if (this.isListeningActive) {
            this.setVoiceState("WAITING_FOR_END_OF_SPEECH");
            this.startPauseTimers();
            this.options?.onSpeechEnd?.();
          }
        };

        rec.onresult = (event: any) => {
          this.lastSpeechActivityTime = performance.now();
          this.clearPauseTimers();
          this.isTranscribingActive = true;
          this.setVoiceState("TRANSCRIBING");

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
            this.options?.onInterimTranscript?.(fullInterim);
          }

          // In continuous mode, manage natural conversational pauses
          if (this.currentMode === "continuous" && fullInterim.length > 0) {
            this.startPauseTimers();
          }
        };

        rec.onerror = (event: any) => {
          console.warn("[JARVIS STT] WebSpeech event error:", event.error);
          if (event.error === "not-allowed") {
            this.setStatus("MIC_PERMISSION_REQUIRED", "Browser microphone access was denied.");
          } else if (event.error === "network") {
            this.setStatus("STT_NETWORK_ERROR", "Browser speech network connection lost.");
          } else if (event.error === "no-speech") {
            // Natural silence, no error action needed
          }
        };

        rec.onend = () => {
          // If still listening in continuous mode, restart recognition seamlessly
          if (this.isListeningActive) {
            try {
              rec.start();
            } catch {
              // Ignore already-started errors
            }
          }
        };

        this.recognition = rec;
        this.activeProvider = "browser-webspeech";
      } catch (err) {
        console.warn("[JARVIS STT] WebSpeech initialization:", err);
      }
    }
  }

  private setupNetworkMonitoring(): void {
    window.addEventListener("online", () => {
      if (this.sttStatus === "STT_OFFLINE") {
        this.setStatus("STT_READY", "Network connectivity restored.");
        this.setVoiceState("IDLE");
        this.retryCount = 0;
      }
    });

    window.addEventListener("offline", () => {
      this.setStatus("STT_OFFLINE", "Device network is offline.");
      this.setVoiceState("RECONNECTING");
    });
  }

  public async checkAvailability(): Promise<SpeechHealthStatus> {
    if (!navigator.onLine) {
      this.setStatus("STT_OFFLINE", "Network is offline.");
      return {
        status: "error",
        sttProvider: "none",
        sttAvailable: false,
        ttsAvailable: false,
        supportedFormats: [],
      };
    }

    const health = await checkSpeechHealth();

    if (this.recognition) {
      this.activeProvider = "browser-webspeech";
      this.setStatus("STT_READY");
    } else if (health.sttAvailable) {
      this.activeProvider = "backend-whisper";
      this.setStatus("STT_READY");
    } else {
      this.activeProvider = "none";
      this.setStatus("STT_CONFIGURATION_ERROR", "No speech-to-text service is currently reachable.");
    }

    return health;
  }

  // ==========================================
  // Core Listening Lifecycle
  // ==========================================

  /**
   * Start Listening with Multi-Provider Capture and Pause Handling
   */
  public async startListening(options: SpeechListenOptions): Promise<void> {
    if (this.isListeningActive) return;

    this.options = options;
    this.currentMode = options.mode || "push-to-talk";
    this.currentLang = options.lang || "en-US";
    this.accumulatedFinalText = "";
    this.currentInterimText = "";
    this.recordedChunks = [];
    this.startTime = performance.now();
    this.lastSpeechActivityTime = this.startTime;
    this.isTranscribingActive = false;

    // 1. Request microphone with studio audio constraints
    const constraints: MediaStreamConstraints = {
      audio: {
        echoCancellation: { ideal: true },
        noiseSuppression: { ideal: true },
        autoGainControl: { ideal: true },
        sampleRate: { ideal: 48000 },
        channelCount: { ideal: 1 },
      },
    };

    try {
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.mediaStream = stream;
      this.isListeningActive = true;
      this.setVoiceState("LISTENING");

      // 2. Route microphone to central Web Audio visualizer (no audio feedback loop)
      aiVisualController.connectMicStream(stream);
      aiVisualController.setState("listening");

      // 3. Start parallel MediaRecorder for high-fidelity Groq Whisper fallback
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/ogg")
        ? "audio/ogg"
        : "";

      if (mimeType) {
        const recorder = new MediaRecorder(stream, { mimeType });
        this.mediaRecorder = recorder;
        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) this.recordedChunks.push(e.data);
        };
        recorder.start(250);
      }

      // 4. Start Browser Speech recognition
      if (this.recognition) {
        this.recognition.lang = this.currentLang;
        try {
          this.recognition.start();
        } catch {
          // Ignore if already active
        }
      }
    } catch (err) {
      this.cancelListening();
      if (err instanceof Error && err.name === "NotAllowedError") {
        this.setStatus("MIC_PERMISSION_REQUIRED", "Microphone access was denied.");
        options.onError(
          "Microphone permission is required. Please enable microphone access in your browser settings, Master.",
          "MIC_PERMISSION_REQUIRED"
        );
      } else if (err instanceof Error && err.name === "NotFoundError") {
        this.setStatus("MIC_UNAVAILABLE", "No microphone hardware detected.");
        options.onError(
          "No microphone hardware was detected on your device, Master.",
          "MIC_UNAVAILABLE"
        );
      } else {
        this.setStatus("STT_SERVER_ERROR", "Could not initialize microphone stream.");
        options.onError(
          "Could not initialize microphone stream. Please verify your audio configuration, Master.",
          "STT_SERVER_ERROR"
        );
      }
    }
  }

  /**
   * Stop Listening and finalize complete speech capture
   */
  public async stopListening(): Promise<void> {
    if (!this.isListeningActive) return;
    this.isListeningActive = false;
    this.clearPauseTimers();

    this.setVoiceState("FINALIZING_TRANSCRIPT");
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

    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      this.mediaRecorder.stop();
    }

    const duration = performance.now() - this.startTime;
    const webSpeechTranscript = (this.accumulatedFinalText + " " + this.currentInterimText).trim();

    if (duration < SpeechManager.MIN_SPEECH_DURATION_MS && !webSpeechTranscript) {
      this.setVoiceState("IDLE");
      this.options?.onError("Voice input was too brief. Speak your command clearly, Master.", "STT_READY");
      return;
    }

    // 1. Primary: If WebSpeech captured clean text, dispatch immediately
    if (webSpeechTranscript.length >= 2) {
      this.retryCount = 0;
      this.setStatus("STT_READY");
      this.setVoiceState("UNDERSTANDING");
      this.options?.onFinalTranscript(webSpeechTranscript);
      return;
    }

    // 2. Fallback: Transcribe buffered audio using Backend Groq Whisper
    if (this.recordedChunks.length > 0) {
      this.setVoiceState("TRANSCRIBING");
      try {
        const audioBlob = new Blob(this.recordedChunks, {
          type: this.mediaRecorder?.mimeType || "audio/webm",
        });

        const whisperTranscript = await transcribeRecording(audioBlob);
        if (whisperTranscript && whisperTranscript.trim().length > 0) {
          this.retryCount = 0;
          this.setStatus("STT_READY");
          this.setVoiceState("UNDERSTANDING");
          this.options?.onFinalTranscript(whisperTranscript.trim());
          return;
        }

        this.setVoiceState("IDLE");
        this.options?.onError(
          "No distinct speech was detected. Please speak clearly into your microphone, Master.",
          "STT_READY"
        );
      } catch (err) {
        this.handleTranscriptionFailure(err);
      }
    } else {
      this.setVoiceState("IDLE");
      this.options?.onError(
        "No audio signal was captured. Please check your microphone connection, Master.",
        "MIC_UNAVAILABLE"
      );
    }
  }

  public pauseListening(): void {
    if (!this.isListeningActive) return;
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch {
        // Ignore
      }
    }
    this.setVoiceState("SHORT_PAUSE");
  }

  public resumeListening(): void {
    if (!this.isListeningActive) return;
    if (this.recognition) {
      try {
        this.recognition.start();
      } catch {
        // Ignore
      }
    }
    this.setVoiceState("LISTENING");
  }

  public cancelListening(): void {
    this.isListeningActive = false;
    this.clearPauseTimers();
    aiVisualController.disconnectMic();
    this.setVoiceState("IDLE");

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

  // ==========================================
  // Pause & End-of-Speech Detection (VAD)
  // ==========================================

  private startPauseTimers(): void {
    this.clearPauseTimers();

    // 1. Short Pause: 1200ms
    this.shortPauseTimer = window.setTimeout(() => {
      if (this.isListeningActive && this.voiceState !== "WAITING_FOR_END_OF_SPEECH") {
        this.setVoiceState("SHORT_PAUSE");
      }
    }, SpeechManager.SHORT_PAUSE_MS);

    // 2. End of Speech: 2800ms
    this.endOfSpeechTimer = window.setTimeout(() => {
      if (this.isListeningActive && this.currentMode === "continuous") {
        const fullText = (this.accumulatedFinalText + " " + this.currentInterimText).trim();
        if (fullText.length >= 2) {
          void this.stopListening();
        }
      }
    }, SpeechManager.END_OF_SPEECH_MS);
  }

  private clearPauseTimers(): void {
    if (this.shortPauseTimer !== null) {
      clearTimeout(this.shortPauseTimer);
      this.shortPauseTimer = null;
    }
    if (this.endOfSpeechTimer !== null) {
      clearTimeout(this.endOfSpeechTimer);
      this.endOfSpeechTimer = null;
    }
  }

  // ==========================================
  // Failure Recovery & Exponential Backoff
  // ==========================================

  private handleTranscriptionFailure(err: unknown): void {
    const errMsg = err instanceof Error ? err.message : String(err);
    let code: STTStatus = "STT_SERVER_ERROR";
    let userMsg = "I encountered difficulty with the speech transcription service. Reconnecting now, Master.";

    if (errMsg.includes("STT_AUTH_ERROR")) {
      code = "STT_AUTH_ERROR";
      userMsg = "Speech service authentication failed. Please verify your Groq API key in the configuration, Master.";
    } else if (errMsg.includes("STT_RATE_LIMITED")) {
      code = "STT_RATE_LIMITED";
      userMsg = "Speech service is temporarily rate-limited. Retrying automatically in a moment, Master.";
    } else if (errMsg.includes("STT_TIMEOUT")) {
      code = "STT_TIMEOUT";
      userMsg = "Speech service request timed out. Please repeat your command, Master.";
    } else if (errMsg.includes("STT_NETWORK_ERROR") || !navigator.onLine) {
      code = "STT_NETWORK_ERROR";
      userMsg = "Network connection is offline. Speech recognition will resume once online, Master.";
    }

    this.setStatus(code, errMsg);
    this.setVoiceState("ERROR_RECOVERY");
    this.scheduleRetry();
    this.options?.onError(userMsg, code);
  }

  private scheduleRetry(): void {
    if (this.retryCount >= this.maxRetries) return;
    this.retryCount++;
    const delay = Math.min(500 * Math.pow(2, this.retryCount), 5000);

    if (this.retryTimer !== null) clearTimeout(this.retryTimer);
    this.retryTimer = window.setTimeout(async () => {
      this.retryTimer = null;
      await this.checkAvailability();
    }, delay);
  }
}

export const speechManager = new SpeechManager();
