# JARVIS 2.0 Design System Specification

## 1. Design Philosophy

The JARVIS 2.0 design system embodies an **intelligent, technological, and cinematic command center**. It emphasizes high visual contrast, crystal-clear information hierarchy, subtle glow accents, authentic glassmorphism, and responsive micro-animations.

---

## 2. Color Palette & Tokens

### 2.1 Cyber Cyan (Primary Accent)
- **Cyan Glow**: `#00f0ff` / `rgba(0, 240, 255, 0.4)`
- **Cyan Border**: `rgba(0, 217, 255, 0.3)`
- **Cyan Surface**: `rgba(0, 217, 255, 0.08)`
- **Cyan Text**: `#64ffda` / `#a5f3fc`

### 2.2 Deep Void (Background & Surfaces)
- **Deep Void Background**: `#030712` (99% darkness)
- **Glass Panel Surface**: `rgba(10, 18, 32, 0.82)` with `backdrop-filter: blur(16px)`
- **Active Card Surface**: `rgba(15, 23, 42, 0.90)`
- **Subsystem Border**: `rgba(30, 41, 59, 0.7)`

### 2.3 Status Tiers & Badges
- **Online / Success**: `#10b981` (Emerald 500)
- **Active / Processing**: `#00d9ff` (Cyan 400)
- **Warning / Confirmation**: `#f59e0b` (Amber 500)
- **Error / Intervention**: `#f43f5e` (Rose 500)
- **Symbolic Math / AST**: `#a855f7` (Violet 500)

---

## 3. Typography Hierarchy

- **Monospace HUD Font**: `'JetBrains Mono', 'Fira Code', 'Roboto Mono', monospace` (used for system telemetry, code, status badges, and technical readouts).
- **Interface Body Font**: `'Inter', system-ui, -apple-system, sans-serif` (used for conversational text, summaries, and dialogs).
- **Brand & Headings**: Bold, letter-spaced uppercase labels (`letter-spacing: 0.12em`).

---

## 4. Glassmorphism & Elevation System

```css
/* Core Glass Panel Token */
.glass-panel {
  background: rgba(10, 18, 32, 0.82);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 217, 255, 0.25);
  border-radius: 1rem;
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.45);
}

/* Focused / Glowing HUD Surface */
.glass-panel:hover {
  border-color: rgba(0, 217, 255, 0.45);
  box-shadow: 0 0 25px rgba(0, 217, 255, 0.2);
}
```

---

## 5. Z-Index Layering

| Layer | Z-Index | Elements |
| :--- | :--- | :--- |
| **Background Video & Ambient HUD** | `0 - 5` | Video background canvas, particle grid, ambient rings |
| **Movable Panels & Workspaces** | `10 - 20` | Orb 3D, Chat card, Activity monitor, Diagnostics |
| **Top Navigation & Sidebar** | `30 - 40` | TopNavigationBar, NavigationSidebar |
| **Global Modals & Overlays** | `50` | CommandPalette, Settings, FileUpload, StudySuite |
| **Toast Notification System** | `60` | Floating HUD alerts |
