import { useEffect, useRef, useState } from "react";
import { aiVisualController, AIVisualState } from "../services/aiVisualController";

export function AmbientHud() {
  const [visualState, setVisualState] = useState<AIVisualState | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const unsubscribe = aiVisualController.subscribe((state) => {
      setVisualState(state);
    });
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const particles = Array.from({ length: 70 }, () => ({
      x: Math.random(),
      y: Math.random(),
      z: 0.3 + Math.random() * 0.7,
      vx: (Math.random() - 0.5) * 0.00018,
      vy: (Math.random() - 0.5) * 0.00018,
    }));

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

      const state = visualState;
      const amp = state?.amplitude ?? 0;
      const now = performance.now();
      const mode = state?.state ?? "idle";

      let hue = "0, 240, 255";
      if (mode === "listening") hue = "90, 170, 255";
      else if (mode === "speaking") hue = "0, 229, 192";
      else if (mode === "error") hue = "255, 56, 96";
      else if (mode === "thinking" || mode === "searching" || mode === "executing") hue = "200, 225, 255";

      const cx = width / 2;
      const cy = height / 2;

      for (let r = 0; r < 4; r++) {
        const radius = 90 + r * 48 + amp * 18;
        ctx.beginPath();
        ctx.strokeStyle = `rgba(${hue}, ${0.05 + amp * 0.08})`;
        ctx.lineWidth = 1;
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.stroke();
      }

      const sweep = (now * 0.00035) % (Math.PI * 2);
      ctx.beginPath();
      ctx.strokeStyle = `rgba(${hue}, 0.18)`;
      ctx.lineWidth = 1.5;
      ctx.arc(cx, cy, 186 + amp * 20, sweep, sweep + 0.7);
      ctx.stroke();

      ctx.strokeStyle = `rgba(${hue}, 0.06)`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cx - 220, cy);
      ctx.lineTo(cx + 220, cy);
      ctx.moveTo(cx, cy - 220);
      ctx.lineTo(cx, cy + 220);
      ctx.stroke();

      for (const particle of particles) {
        particle.x += particle.vx;
        particle.y += particle.vy;
        if (particle.x < 0 || particle.x > 1) particle.vx *= -1;
        if (particle.y < 0 || particle.y > 1) particle.vy *= -1;

        const px = particle.x * width;
        const py = particle.y * height;
        const size = particle.z * (1.2 + amp * 1.6);
        ctx.fillStyle = `rgba(${hue}, ${0.12 + particle.z * 0.25})`;
        ctx.beginPath();
        ctx.arc(px, py, size, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [visualState]);

  const sourceLabel =
    visualState?.source === "tts" ? "NEURAL STREAM" : visualState?.source === "mic" ? "LIVE MIC" : "STANDBY";
  const stateLabel = visualState?.state?.toUpperCase() ?? "ONLINE";

  return (
    <div className={`ambient-hud ${visualState?.isSpeaking ? "is-active" : ""}`} aria-hidden="true">
      <canvas ref={canvasRef} className="ambient-hud-canvas" />
      <div className="hud-caption-bar">
        <span className="hud-source-badge">{sourceLabel}</span>
        <span className="hud-metric">
          DSP <strong>{stateLabel}</strong>
        </span>
      </div>
    </div>
  );
}
