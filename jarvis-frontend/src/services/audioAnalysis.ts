export type VoiceMetrics = {
  /** Overall vocal volume/energy (0.0 to 1.0) with fast attack and smooth decay */
  amplitude: number;
  /** Raw instantaneous RMS */
  rawAmplitude: number;
  /** Low-frequency voice resonance (fundamental pitch/vowels: 60-350Hz) */
  bass: number;
  /** Mid-frequency formants (vowel clarity: 350-2000Hz) */
  mid: number;
  /** High-frequency harmonics/sibilants (consonants/air: 2000-8000Hz) */
  high: number;
  /** Normalized spectral centroid (0.0 = deep bass, 1.0 = high pitch) */
  pitch: number;
  /** Transient emphasis detector for stressed syllables/words (0.0 to 1.0) */
  emphasis: number;
  /** Rapid micro-oscillation factor driven by voice harmonics */
  microPulse: number;
  /** Indicates if audio is actively producing voice */
  isSpeaking: boolean;
  /** Smooth resting factor: 1.0 when quiet/resting, 0.0 when actively vocalizing */
  calmRatio: number;
};

class SpeechAudioEngine {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private sourceMap = new WeakMap<HTMLAudioElement, MediaElementAudioSourceNode>();
  private freqData: Uint8Array<ArrayBuffer> | null = null;
  private timeData: Uint8Array<ArrayBuffer> | null = null;

  private smoothedAmp = 0;
  private smoothedBass = 0;
  private smoothedMid = 0;
  private smoothedHigh = 0;
  private smoothedPitch = 0.2;
  private smoothedEmphasis = 0;
  private calmFactor = 1;
  private prevRawAmp = 0;

  private isSimulating = false;
  private simStartTime = 0;
  private simText = "";

  public getContext(): AudioContext {
    if (!this.audioContext) {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
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
    }
    return this.analyser;
  }

  /**
   * Connect an HTMLAudioElement directly into the Web Audio processing graph
   */
  public connectAudioElement(audio: HTMLAudioElement): void {
    const ctx = this.getContext();
    const analyser = this.getAnalyser();

    if (!this.sourceMap.has(audio)) {
      try {
        const source = ctx.createMediaElementSource(audio);
        source.connect(analyser);
        analyser.connect(ctx.destination);
        this.sourceMap.set(audio, source);
      } catch {
        // Media element already connected or cross-origin
      }
    }
    this.isSimulating = false;
  }

  /**
   * Start simulation mode when using SpeechSynthesis or fallback audio
   */
  public startSpeechSimulation(text: string): void {
    this.isSimulating = true;
    this.simStartTime = performance.now();
    this.simText = text;
  }

  public stopSpeechSimulation(): void {
    this.isSimulating = false;
  }

  /**
   * Extract real-time voice metrics every animation frame
   */
  public sample(): VoiceMetrics {
    if (this.isSimulating) {
      return this.sampleSimulation();
    }

    if (!this.analyser || !this.freqData || !this.timeData) {
      return this.decayToRest();
    }

    this.analyser.getByteFrequencyData(this.freqData);
    this.analyser.getByteTimeDomainData(this.timeData);

    // 1. Calculate RMS Amplitude from Time Domain
    let sumSquares = 0;
    for (let i = 0; i < this.timeData.length; i++) {
      const normalized = (this.timeData[i] - 128) / 128;
      sumSquares += normalized * normalized;
    }
    const rms = Math.sqrt(sumSquares / this.timeData.length);
    const rawAmp = Math.min(1, Math.max(0, (rms - 0.012) * 5.2));

    // 2. Frequency Band Analysis (Bass: 60-350Hz, Mid: 350-2000Hz, High: 2000-8000Hz)
    const binCount = this.freqData.length;
    let bassSum = 0;
    let bassCount = 0;
    let midSum = 0;
    let midCount = 0;
    let highSum = 0;
    let highCount = 0;

    let totalWeightedFreq = 0;
    let totalEnergy = 0;

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

    const bassVal = bassCount > 0 ? Math.min(1, (bassSum / bassCount) * 1.6) : 0;
    const midVal = midCount > 0 ? Math.min(1, (midSum / midCount) * 1.8) : 0;
    const highVal = highCount > 0 ? Math.min(1, (highSum / highCount) * 2.2) : 0;

    // Pitch estimation via spectral centroid
    const centroid = totalEnergy > 0.05 ? totalWeightedFreq / totalEnergy : 8;
    const rawPitch = Math.min(1, Math.max(0, (centroid - 4) / 45));

    // 3. Transient emphasis detection
    const delta = Math.max(0, rawAmp - this.prevRawAmp);
    this.prevRawAmp = rawAmp;
    const isSpeaking = rawAmp > 0.035;

    // 4. Smooth with organic spring physics
    const attackRate = rawAmp > this.smoothedAmp ? 0.45 : 0.12;
    this.smoothedAmp += (rawAmp - this.smoothedAmp) * attackRate;
    this.smoothedBass += (bassVal - this.smoothedBass) * (bassVal > this.smoothedBass ? 0.4 : 0.14);
    this.smoothedMid += (midVal - this.smoothedMid) * (midVal > this.smoothedMid ? 0.45 : 0.16);
    this.smoothedHigh += (highVal - this.smoothedHigh) * (highVal > this.smoothedHigh ? 0.55 : 0.2);
    this.smoothedPitch += (rawPitch - this.smoothedPitch) * 0.18;

    const rawEmphasis = delta > 0.12 ? Math.min(1, delta * 3.2) : 0;
    this.smoothedEmphasis = Math.max(rawEmphasis, this.smoothedEmphasis * 0.82);

    const targetCalm = isSpeaking ? 0 : 1;
    this.calmFactor += (targetCalm - this.calmFactor) * 0.06;

    const microPulse = Math.sin(performance.now() * 0.02 * (1 + this.smoothedPitch * 2)) * this.smoothedHigh;

    return {
      amplitude: this.smoothedAmp,
      rawAmplitude: rawAmp,
      bass: this.smoothedBass,
      mid: this.smoothedMid,
      high: this.smoothedHigh,
      pitch: this.smoothedPitch,
      emphasis: this.smoothedEmphasis,
      microPulse,
      isSpeaking,
      calmRatio: this.calmFactor,
    };
  }

  /**
   * High-fidelity synthetic speech cadence generator when speech synthesis is used
   */
  private sampleSimulation(): VoiceMetrics {
    const elapsed = (performance.now() - this.simStartTime) / 1000;
    const syllables = Math.max(4, this.simText.split(/\s+/).length * 1.5);
    const totalDuration = syllables * 0.28;

    if (elapsed > totalDuration) {
      this.isSimulating = false;
      return this.decayToRest();
    }

    const speechCadence = Math.sin(elapsed * 9.5) * 0.5 + 0.5;
    const syllabicBurst = Math.sin(elapsed * 18.2) * 0.3 + 0.7;
    const pauseFactor = Math.sin(elapsed * 2.8) > 0.72 ? 0.1 : 1.0;

    const rawAmp = Math.max(0, speechCadence * syllabicBurst * pauseFactor * 0.78);
    const bassVal = rawAmp * 0.85;
    const midVal = rawAmp * 0.95;
    const highVal = (Math.sin(elapsed * 28.0) * 0.5 + 0.5) * rawAmp * 0.8;
    const rawPitch = 0.35 + Math.sin(elapsed * 4.2) * 0.25;

    this.smoothedAmp += (rawAmp - this.smoothedAmp) * 0.35;
    this.smoothedBass += (bassVal - this.smoothedBass) * 0.3;
    this.smoothedMid += (midVal - this.smoothedMid) * 0.35;
    this.smoothedHigh += (highVal - this.smoothedHigh) * 0.4;
    this.smoothedPitch += (rawPitch - this.smoothedPitch) * 0.2;

    const isSpeaking = this.smoothedAmp > 0.04;
    this.calmFactor += ((isSpeaking ? 0 : 1) - this.calmFactor) * 0.08;

    return {
      amplitude: this.smoothedAmp,
      rawAmplitude: rawAmp,
      bass: this.smoothedBass,
      mid: this.smoothedMid,
      high: this.smoothedHigh,
      pitch: this.smoothedPitch,
      emphasis: this.smoothedHigh > 0.5 ? 0.6 : 0,
      microPulse: Math.sin(elapsed * 22) * this.smoothedHigh,
      isSpeaking,
      calmRatio: this.calmFactor,
    };
  }

  private decayToRest(): VoiceMetrics {
    this.smoothedAmp *= 0.88;
    this.smoothedBass *= 0.88;
    this.smoothedMid *= 0.88;
    this.smoothedHigh *= 0.85;
    this.smoothedEmphasis *= 0.8;
    this.calmFactor += (1 - this.calmFactor) * 0.05;

    return {
      amplitude: Math.max(0, this.smoothedAmp),
      rawAmplitude: 0,
      bass: Math.max(0, this.smoothedBass),
      mid: Math.max(0, this.smoothedMid),
      high: Math.max(0, this.smoothedHigh),
      pitch: this.smoothedPitch,
      emphasis: Math.max(0, this.smoothedEmphasis),
      microPulse: 0,
      isSpeaking: false,
      calmRatio: this.calmFactor,
    };
  }
}

export const speechAudioEngine = new SpeechAudioEngine();
