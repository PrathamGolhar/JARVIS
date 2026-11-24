import { useEffect, useRef } from "react";
import { aiVisualController, AIVisualState } from "../services/aiVisualController";

type VoiceWaveformProps = {
  className?: string;
};

export function VoiceWaveform({ className = "" }: VoiceWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const visualRef = useRef<AIVisualState | null>(null);

  useEffect(() => {
    const unsubscribe = aiVisualController.subscribe((state) => {
      visualRef.current = state;
    });

    const canvas = canvasRef.current;
    if (!canvas) return () => unsubscribe();
    const ctx = canvas.getContext("2d");
    if (!ctx) return () => unsubscribe();

    let animId = 0;

    const render = () => {
      animId = requestAnimationFrame(render);
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (width === 0 || height === 0) return;

      if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
        canvas.width = width * dpr;
        canvas.height = height * dpr;
      }

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);

      const state = visualRef.current;
      const bands = state?.frequencyBands ?? [];
      const amp = state?.amplitude ?? 0;
      const mode = state?.state ?? "idle";
      const cx = width / 2;
      const cy = height / 2;
      const inner = Math.min(width, height) * 0.34;
      const barCount = 64;
      const now = performance.now();

      let stroke = "rgba(0, 240, 255,";
      if (mode === "listening") stroke = "rgba(80, 170, 255,";
      else if (mode === "speaking") stroke = "rgba(0, 229, 192,";
      else if (mode === "error") stroke = "rgba(255, 56, 96,";
      else if (mode === "thinking" || mode === "searching" || mode === "executing") {
        stroke = "rgba(180, 220, 255,";
      }

      ctx.save();
      ctx.translate(cx, cy);

      for (let i = 0; i < barCount; i++) {
        const band = bands[i % Math.max(bands.length, 1)] || 0;
        const idleWave = Math.sin(now * 0.002 + i * 0.22) * 4;
        const energy = Math.max(0.08, band * 0.92 + amp * 0.35);
        const length = 10 + energy * 42 + (mode === "idle" ? idleWave : 0);
        const angle = (i / barCount) * Math.PI * 2 - Math.PI / 2;

        ctx.strokeStyle = `${stroke}${0.28 + energy * 0.55})`;
        ctx.lineWidth = 2;
        ctx.shadowColor = `${stroke}0.55)`;
        ctx.shadowBlur = energy > 0.25 ? 10 : 0;
        ctx.beginPath();
        ctx.moveTo(Math.cos(angle) * inner, Math.sin(angle) * inner);
        ctx.lineTo(Math.cos(angle) * (inner + length), Math.sin(angle) * (inner + length));
        ctx.stroke();
      }

      ctx.restore();
    };

    render();
    return () => {
      unsubscribe();
      cancelAnimationFrame(animId);
    };
  }, []);

  return <canvas ref={canvasRef} className={`voice-waveform ${className}`} aria-hidden="true" />;
}
