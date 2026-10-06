# JARVIS 2.0 Motion & Animation Architecture

## 1. Animation Principles

1. **Intelligent & Alive**: Elements gently pulse and respond to user presence and AI cognition.
2. **Performance First**: All continuous animations utilize GPU-accelerated CSS properties (`transform`, `opacity`, `filter`) and Canvas `requestAnimationFrame()`.
3. **Reduced Motion Respect**: Honors `@media (prefers-reduced-motion: reduce)` by gracefully disabling particle turbulence and scaling effects.

---

## 2. Core Animation Registry

```css
/* Breathing Pulse for Status Indicators */
@keyframes pulse-glow {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 10px rgba(0, 217, 255, 0.4);
  }
  50% {
    transform: scale(1.08);
    box-shadow: 0 0 25px rgba(0, 217, 255, 0.8);
  }
}

/* Ambient Ring Rotation */
@keyframes rotate-ring {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Live Audio Streaming Waveform */
@keyframes stream-pulse {
  0% { opacity: 0.3; transform: scaleY(0.6); }
  50% { opacity: 1; transform: scaleY(1.4); }
  100% { opacity: 0.3; transform: scaleY(0.6); }
}
```

---

## 3. 3D Holographic Particle Globe Physics

The central hologram (`src/components/HolographicGlobe.tsx`) is rendered dynamically:
- **Idle State**: 1,200 particle nodes rotating on spherical orbits with gentle sinusoidal drift.
- **Listening State**: Frequency bands modulate node velocity and particle point size in real time.
- **Thinking State**: Swirling vortex accretion ring with accelerated angular velocity.
- **Speaking State**: Multi-harmonic amplitude spikes mapped to TTS audio output frequency bins.
