/**
 * JARVIS 2.0 — Centralized Futuristic Design Tokens.
 * Defines color palettes, glassmorphism styling, typography, elevation levels, and animation metrics.
 */

export const DESIGN_TOKENS = {
  colors: {
    background: {
      primary: '#030712',      // Deepest Obsidian Navy
      secondary: '#0a0f1d',    // Translucent Panel Charcoal
      tertiary: '#0f172a',     // Highlight Surface
      glass: 'rgba(10, 15, 29, 0.75)',
      glassHover: 'rgba(15, 23, 42, 0.85)',
    },
    accent: {
      cyan: '#00e5ff',         // Primary Arc-Reactor Blue
      cyanGlow: 'rgba(0, 229, 255, 0.35)',
      purple: '#a855f7',       // Secondary Deep AI Violet
      purpleGlow: 'rgba(168, 85, 247, 0.35)',
      blue: '#3b82f6',
      emerald: '#10b981',      // Success & Verified Output
      amber: '#f59e0b',        // Warning & Attention
      crimson: '#ef4444',      // Error & Critical Security
    },
    text: {
      primary: '#f8fafc',
      secondary: '#94a3b8',
      muted: '#64748b',
      accent: '#38bdf8',
      accentCyan: '#00e5ff',
    },
    border: {
      subtle: 'rgba(0, 229, 255, 0.15)',
      active: 'rgba(0, 229, 255, 0.45)',
      glow: 'rgba(0, 229, 255, 0.65)',
    },
  },
  typography: {
    fontFamily: {
      sans: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      mono: "'JetBrains Mono', 'Fira Code', monospace",
      hud: "'Orbitron', 'Rajdhani', sans-serif",
    },
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem',
      '3xl': '1.875rem',
    },
  },
  blur: {
    subtle: 'blur(8px)',
    medium: 'blur(16px)',
    heavy: 'blur(24px)',
  },
  shadows: {
    hudGlow: '0 0 20px rgba(0, 229, 255, 0.25)',
    hudGlowStrong: '0 0 35px rgba(0, 229, 255, 0.45)',
    purpleGlow: '0 0 20px rgba(168, 85, 247, 0.25)',
    panel: '0 10px 30px -10px rgba(0, 0, 0, 0.8)',
  },
  zIndex: {
    background: 0,
    content: 10,
    sidebar: 20,
    topbar: 30,
    drawer: 40,
    modal: 50,
    toast: 60,
    commandPalette: 70,
  },
  transitions: {
    fast: 'all 0.15s cubic-bezier(0.4, 0, 0.2, 1)',
    normal: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
    smooth: 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
  },
} as const;
