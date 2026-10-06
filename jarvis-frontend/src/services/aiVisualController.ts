/**
 * AI Real-Time Visual Controller
 *
 * Central Single Source of Truth for all JARVIS visualizations.
 * Manages the Web Audio API graph, extracts multi-band acoustic DSP features,
 * and broadcasts an immutable, synchronized visual state to both foreground
 * and background visualizers on a single unified animation clock.
 */

export type AssistantState =
  | "idle"
  | "listening"
  | "transcribing"
  | "understanding"
  | "thinking"
  | "searching"
  | "executing"
  | "speaking"
  | "error";

export type AudioSourceType = "tts" | "mic" | "idle";

export type AIVisualState = {
  /** Current operational state */
  state: AssistantState;
  /** Active audio input source */
  source: AudioSourceType;
  /** Normalized smoothed amplitude [0.0, 1.0] (fast attack, smooth release) */
  amplitude: number;
  /** Raw instantaneous RMS amplitude */
  rawAmplitude: number;
  /** Low-frequency energy (60 - 350Hz) */
  bass: number;
  /** Mid-frequency energy (350 - 2000Hz) */
  mid: number;
  /** High-frequency energy (2000 - 8000Hz) */
  high: number;
  /** Normalized pitch / spectral centroid [0.0 = deep bass, 1.0 = high treble] */
  pitch: number;
  /** Estimated fundamental pitch in Hertz (approximate) */
  pitchHz: number;
  /** Transient syllable/word emphasis detector [0.0, 1.0] */
  emphasis: number;
  /** Voice Activity Detection (VAD) active flag */
  isSpeaking: boolean;
  /** High-frequency micro-oscillation factor */
  microPulse: number;
  /** Smooth resting factor: 1.0 = resting idle, 0.0 = fully active */
  calmRatio: number;
  /** 16-band normalized frequency spectrum for background HUD equalizer [0.0, 1.0] */
  frequencyBands: number[];
  /** Calculated target scale for 3D core & background waves */
  scale: number;
  /** Calculated luminous glow factor */
  glow: number;
  /** Calculated rotation velocity */
  rotationSpeed: number;
  /** Calculated acoustic wave displacement */
  waveDeformation: number;
  /** Timestamp of the frame (ms) */
  timestamp: number;
};

export type VisualStateSubscriber = (state: AIVisualState) => void;

class AIVisualController {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private ttsSourceMap = new WeakMap<HTMLAudioElement, MediaElementAudioSourceNode>();
  private micSourceNode: MediaStreamAudioSourceNode | null = null;
  private micStream: MediaStream | null = null;
  private currentAudioElement: HTMLAudioElement | null = null;

  private currentSource: AudioSourceType = "idle";
  private currentState: AssistantState = "idle";

  private freqData: Uint8Array<ArrayBuffer> | null = null;
  private timeData: Uint8Array<ArrayBuffer> | null = null;
  private floatTimeData: Float32Array<ArrayBuffer> | null = null;

  // Smoothing physics state
  private smoothedAmp = 0;
  private smoothedBass = 0;
  private smoothedMid = 0;
  private smoothedHigh = 0;
  private smoothedPitch = 0.25;
  private smoothedPitchHz = 160;
  private smoothedEmphasis = 0;
  private calmFactor = 1.0;
  private prevRawAmp = 0;
  private frequencyBands: number[] = new Array(16).fill(0);

  // Simulation mode (fallback if audio output cannot be tapped)
  private isSimulating = false;
  private simStartTime = 0;
  private simText = "";

  // Subscribers
  private subscribers = new Set<VisualStateSubscriber>();
  private animationFrameId: number | null = null;
  private isLoopRunning = false;

  constructor() {
    this.startLoop();
  }

  public getContext(): AudioContext {
    if (!this.audioContext) {
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.audioContext = new AudioCtx();
    }
    if (this.audioContext.state === "suspended") {
      void this.audioContext.resume();
    }
    return this.audioContext;
  }

  public getAnalyser(): AnalyserNode {
    const ctx = this.getContext();
    if (!this.analyser) {
      this.analyser = ctx.createAnalyser();
      this.analyser.fftSize = 512;
      this.analyser.smoothingTimeConstant = 0.72;
      this.analyser.minDecibels = -85;
      this.analyser.maxDecibels = -10;
      this.freqData = new Uint8Array(this.analyser.frequencyBinCount);
      this.timeData = new Uint8Array(this.analyser.fftSize);
      this.floatTimeData = new Float32Array(this.analyser.fftSize);
    }
    return this.analyser;
  }

  public setState(state: AssistantState): void {
    this.currentState = state;
    if (state === "idle" || state === "error") {
      if (this.currentSource !== "idle") {
        this.currentSource = "idle";
      }
    }
  }

  /**
   * Connect an HTMLAudioElement (TTS Speech Output) to the audio processing graph
   */
  public connectTTSAudio(audio: HTMLAudioElement): void {
    this.disconnectMic();
    const ctx = this.getContext();
    const analyser = this.getAnalyser();

    this.currentAudioElement = audio;
    this.currentSource = "tts";
    this.isSimulating = false;

    if (!this.ttsSourceMap.has(audio)) {
      try {
        const source = ctx.createMediaElementSource(audio);
        source.connect(analyser);
        analyser.connect(ctx.destination);
        this.ttsSourceMap.set(audio, source);
      } catch {
        // Already connected or cross-origin
      }
    }
  }

  /**
   * Connect a MediaStream (User Microphone) to the audio processing graph
   */
  public connectMicStream(stream: MediaStream): void {
    this.disconnectTTS();
    const ctx = this.getContext();
    const analyser = this.getAnalyser();

    this.disconnectMic();

    try {
      this.micStream = stream;
      this.micSourceNode = ctx.createMediaStreamSource(stream);
      // Connect to analyser ONLY (do NOT connect to ctx.destination to avoid acoustic feedback loop)
      this.micSourceNode.connect(analyser);
      this.currentSource = "mic";
      this.isSimulating = false;
    } catch {
      this.currentSource = "idle";
    }
  }

  public disconnectMic(): void {
    if (this.micSourceNode) {
      try {
        this.micSourceNode.disconnect();
      } catch {
        // Ignore disconnect errors
      }
      this.micSourceNode = null;
    }
    this.micStream = null;
    if (this.currentSource === "mic") {
      this.currentSource = "idle";
    }
  }

  public disconnectTTS(): void {
    this.currentAudioElement = null;
    if (this.currentSource === "tts") {
      this.currentSource = "idle";
    }
  }

  public disconnectAll(): void {
    this.disconnectMic();
    this.disconnectTTS();
    this.isSimulating = false;
    this.currentSource = "idle";
  }

  public startSpeechSimulation(text: string): void {
    this.disconnectAll();
    this.isSimulating = true;
    this.simStartTime = performance.now();
    this.simText = text;
    this.currentSource = "tts";
  }

  public stopSpeechSimulation(): void {
    this.isSimulating = false;
    if (this.currentSource === "tts") {
      this.currentSource = "idle";
    }
  }

  /**
   * Subscribe to real-time visual state updates on the unified frame clock
   */
  public subscribe(subscriber: VisualStateSubscriber): () => void {
    this.subscribers.add(subscriber);
    return () => {
      this.subscribers.delete(subscriber);
    };
  }

  private startLoop(): void {
    if (this.isLoopRunning) return;
    this.isLoopRunning = true;

    const tick = (time: number) => {
      const visualState = this.computeFrame(time);
      for (const subscriber of this.subscribers) {
        try {
          subscriber(visualState);
        } catch {
          // Prevent bad subscriber from breaking render loop
        }
      }
      this.animationFrameId = requestAnimationFrame(tick);
    };

    this.animationFrameId = requestAnimationFrame(tick);
  }

  /**
   * Primary DSP analysis and visual state calculation per frame
   */
  private computeFrame(now: number): AIVisualState {
    if (this.isSimulating) {
      return this.computeSimulationFrame(now);
    }

    if (!this.analyser || !this.freqData || !this.timeData || this.currentSource === "idle") {
      return this.computeRestFrame(now);
    }

    this.analyser.getByteFrequencyData(this.freqData);
    this.analyser.getByteTimeDomainData(this.timeData);

    // 1. Calculate RMS Amplitude
    let sumSquares = 0;
    for (let i = 0; i < this.timeData.length; i++) {
      const normalized = (this.timeData[i] - 128) / 128;
      sumSquares += normalized * normalized;
    }
    const rms = Math.sqrt(sumSquares / this.timeData.length);
    const rawAmp = Math.min(1.0, Math.max(0.0, (rms - 0.012) * 5.2));

    // 2. Frequency Band Analysis
    const binCount = this.freqData.length;
    let bassSum = 0;
    let bassCount = 0;
    let midSum = 0;
    let midCount = 0;
    let highSum = 0;
    let highCount = 0;

    let totalWeightedFreq = 0;
    let totalEnergy = 0;

    // Build 16-band equalizer for background HUD
    const bandSize = Math.floor(binCount / 16);
    const newBands = new Array(16).fill(0);

    for (let b = 0; b < 16; b++) {
      let bSum = 0;
      const start = b * bandSize;
      const end = start + bandSize;
      for (let i = start; i < end; i++) {
        bSum += this.freqData[i] / 255;
      }
      newBands[b] = bSum / bandSize;
    }

    for (let i = 0; i < binCount; i++) {
      const val = this.freqData[i] / 255;
      totalWeightedFreq += i * val;
      totalEnergy += val;

      if (i >= 1 && i <= 8) {
        bassSum += val;
        bassCount++;
      } else if (i >= 9 && i <= 36) {
        midSum += val;
        midCount++;
      } else if (i >= 37 && i <= 120) {
        highSum += val;
        highCount++;
      }
    }

    const bassVal = bassCount > 0 ? Math.min(1.0, (bassSum / bassCount) * 1.6) : 0;
    const midVal = midCount > 0 ? Math.min(1.0, (midSum / midCount) * 1.8) : 0;
    const highVal = highCount > 0 ? Math.min(1.0, (highSum / highCount) * 2.2) : 0;

    // Pitch estimation via spectral centroid
    const sampleRate = this.audioContext?.sampleRate || 44100;
    const nyquist = sampleRate / 2;
    const centroidBin = totalEnergy > 0.04 ? totalWeightedFreq / totalEnergy : 8;
    const estimatedHz = Math.round((centroidBin / binCount) * (nyquist / 2));
    const rawPitch = Math.min(1.0, Math.max(0.0, (centroidBin - 4) / 45));

    // 3. Transient emphasis detection
    const delta = Math.max(0, rawAmp - this.prevRawAmp);
    this.prevRawAmp = rawAmp;
    const isSpeaking = rawAmp > 0.035;

    // 4. Smooth with organic spring physics (Fast Attack, Smooth Release)
    const attackRate = rawAmp > this.smoothedAmp ? 0.45 : 0.12;
    this.smoothedAmp += (rawAmp - this.smoothedAmp) * attackRate;
    this.smoothedBass += (bassVal - this.smoothedBass) * (bassVal > this.smoothedBass ? 0.4 : 0.14);
    this.smoothedMid += (midVal - this.smoothedMid) * (midVal > this.smoothedMid ? 0.45 : 0.16);
    this.smoothedHigh += (highVal - this.smoothedHigh) * (highVal > this.smoothedHigh ? 0.55 : 0.2);
    this.smoothedPitch += (rawPitch - this.smoothedPitch) * 0.18;
    this.smoothedPitchHz += (estimatedHz - this.smoothedPitchHz) * 0.15;

    const rawEmphasis = delta > 0.12 ? Math.min(1.0, delta * 3.2) : 0;
    this.smoothedEmphasis = Math.max(rawEmphasis, this.smoothedEmphasis * 0.82);

    const targetCalm = isSpeaking ? 0.0 : 1.0;
    this.calmFactor += (targetCalm - this.calmFactor) * 0.06;

    // Smooth equalizer bands
    for (let b = 0; b < 16; b++) {
      this.frequencyBands[b] += (newBands[b] - this.frequencyBands[b]) * 0.35;
    }

    const microPulse =
      Math.sin(now * 0.02 * (1 + this.smoothedPitch * 2)) * this.smoothedHigh;

    // Calculated visual derivatives
    const scale = 1.0 + this.smoothedAmp * 0.38 + this.smoothedEmphasis * 0.16;
    const glow = 0.4 + this.smoothedAmp * 0.8 + this.smoothedBass * 0.35;
    const rotationSpeed = 0.4 + this.smoothedAmp * 1.5 + this.smoothedPitch * 0.8;
    const waveDeformation =
      this.smoothedMid * 4.2 + this.smoothedBass * 3.4 + this.smoothedHigh * 2.0;

    return {
      state: this.currentState,
      source: this.currentSource,
      amplitude: this.smoothedAmp,
      rawAmplitude: rawAmp,
      bass: this.smoothedBass,
      mid: this.smoothedMid,
      high: this.smoothedHigh,
      pitch: this.smoothedPitch,
      pitchHz: Math.round(this.smoothedPitchHz),
      emphasis: this.smoothedEmphasis,
      isSpeaking,
      microPulse,
      calmRatio: this.calmFactor,
      frequencyBands: [...this.frequencyBands],
      scale,
      glow,
      rotationSpeed,
      waveDeformation,
      timestamp: now,
    };
  }

  private computeSimulationFrame(now: number): AIVisualState {
    const elapsed = (now - this.simStartTime) / 1000;
    const syllables = Math.max(4, this.simText.split(/\s+/).length * 1.5);
    const totalDuration = syllables * 0.28;

    if (elapsed > totalDuration) {
      this.isSimulating = false;
      return this.computeRestFrame(now);
    }

    const speechCadence = Math.sin(elapsed * 9.5) * 0.5 + 0.5;
    const syllabicBurst = Math.sin(elapsed * 18.2) * 0.3 + 0.7;
    const pauseFactor = Math.sin(elapsed * 2.8) > 0.72 ? 0.1 : 1.0;

    const rawAmp = Math.max(0.0, speechCadence * syllabicBurst * pauseFactor * 0.78);
    const bassVal = rawAmp * 0.85;
    const midVal = rawAmp * 0.95;
    const highVal = (Math.sin(elapsed * 28.0) * 0.5 + 0.5) * rawAmp * 0.8;
    const rawPitch = 0.35 + Math.sin(elapsed * 4.2) * 0.25;

    this.smoothedAmp += (rawAmp - this.smoothedAmp) * 0.35;
    this.smoothedBass += (bassVal - this.smoothedBass) * 0.3;
    this.smoothedMid += (midVal - this.smoothedMid) * 0.35;
    this.smoothedHigh += (highVal - this.smoothedHigh) * 0.4;
    this.smoothedPitch += (rawPitch - this.smoothedPitch) * 0.2;
    this.smoothedPitchHz = 180 + Math.sin(elapsed * 4.2) * 40;

    const isSpeaking = this.smoothedAmp > 0.04;
    this.calmFactor += ((isSpeaking ? 0.0 : 1.0) - this.calmFactor) * 0.08;

    for (let b = 0; b < 16; b++) {
      const targetB = this.smoothedAmp * (0.4 + 0.6 * Math.sin(elapsed * 12 + b));
      this.frequencyBands[b] += (targetB - this.frequencyBands[b]) * 0.3;
    }

    const scale = 1.0 + this.smoothedAmp * 0.38;
    const glow = 0.4 + this.smoothedAmp * 0.8;
    const rotationSpeed = 0.4 + this.smoothedAmp * 1.5;
    const waveDeformation = this.smoothedMid * 4.0;

    return {
      state: this.currentState,
      source: "tts",
      amplitude: this.smoothedAmp,
      rawAmplitude: rawAmp,
      bass: this.smoothedBass,
      mid: this.smoothedMid,
      high: this.smoothedHigh,
      pitch: this.smoothedPitch,
      pitchHz: Math.round(this.smoothedPitchHz),
      emphasis: this.smoothedHigh > 0.5 ? 0.6 : 0.0,
      isSpeaking,
      microPulse: Math.sin(elapsed * 22) * this.smoothedHigh,
      calmRatio: this.calmFactor,
      frequencyBands: [...this.frequencyBands],
      scale,
      glow,
      rotationSpeed,
      waveDeformation,
      timestamp: now,
    };
  }

  private computeRestFrame(now: number): AIVisualState {
    this.smoothedAmp *= 0.88;
    this.smoothedBass *= 0.88;
    this.smoothedMid *= 0.88;
    this.smoothedHigh *= 0.85;
    this.smoothedEmphasis *= 0.8;
    this.calmFactor += (1.0 - this.calmFactor) * 0.05;

    for (let b = 0; b < 16; b++) {
      this.frequencyBands[b] *= 0.85;
    }

    // Gentle ambient breathing oscillation during idle / thinking
    const ambientPulse =
      this.currentState === "thinking" || this.currentState === "searching" || this.currentState === "executing"
        ? Math.sin(now * 0.005) * 0.08 + 0.12
        : Math.sin(now * 0.0018) * 0.03;

    const scale = 1.0 + ambientPulse + this.smoothedAmp * 0.38;
    const glow = 0.35 + ambientPulse * 0.5;
    const rotationSpeed =
      this.currentState === "thinking" || this.currentState === "searching"
        ? 0.85
        : 0.35;
    const waveDeformation =
      this.currentState === "thinking" ? 0.8 : 0.2;

    return {
      state: this.currentState,
      source: this.currentSource,
      amplitude: this.smoothedAmp,
      rawAmplitude: 0.0,
      bass: this.smoothedBass,
      mid: this.smoothedMid,
      high: this.smoothedHigh,
      pitch: this.smoothedPitch,
      pitchHz: Math.round(this.smoothedPitchHz),
      emphasis: 0.0,
      isSpeaking: false,
      microPulse: 0.0,
      calmRatio: this.calmFactor,
      frequencyBands: [...this.frequencyBands],
      scale,
      glow,
      rotationSpeed,
      waveDeformation,
      timestamp: now,
    };
  }
}

export const aiVisualController = new AIVisualController();
