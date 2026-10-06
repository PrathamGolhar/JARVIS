# JARVIS 2.0 Frontend Architecture

## 1. Executive Summary

The **JARVIS 2.0 Next-Generation Frontend** is an ultra-modern, reactive, multi-workspace AI command center designed for seamless human-AI interaction. Built with **React 19, TypeScript, and Vite**, it integrates 3D voice-reactive holographic visualizations, audio digital signal processing (DSP), voice activity detection (VAD), live multi-subsystem telemetry, and a Directed Acyclic Graph (DAG) task execution pipeline.

---

## 2. Architectural Pillars

```text
                               +------------------------------------------+
                               |           JARVIS Web Shell               |
                               |  (React 19 + TypeScript + CSS Modules)   |
                               +------------------------------------------+
                                                    |
             +--------------------------------------+--------------------------------------+
             |                                      |                                      |
             v                                      v                                      v
+--------------------------+          +--------------------------+          +--------------------------+
|   Navigation & Routing   |          |  Interactive Workspaces  |          |   Audio & Visual Core    |
| - TopNavigationBar       |          | - DashboardWorkspace     |          | - HolographicGlobe (3D)  |
| - NavigationSidebar      |          | - ResearchWorkspace      |          | - AmbientHud             |
| - CommandPalette (Ctrl+K)|          | - CodeWorkspace          |          | - Audio DSP & VAD        |
| - QuickActionsBar        |          | - IntegrationsWorkspace  |          | - Voice Synthesis (Edge) |
+--------------------------+          | - StudyMode / Files / ...|          +--------------------------+
                                      +--------------------------+
                                                    |
                                                    v
                               +------------------------------------------+
                               |          FastAPI Backend (8765)          |
                               | ModelRouter / TaskGraph / EventBus / RAG |
                               +------------------------------------------+
```

### 2.1 Technology Stack
- **Framework**: React 19 (`react`, `react-dom`)
- **Language**: TypeScript 5.6+ with strict type checking
- **Bundler & Build Tool**: Vite 6.4+
- **Styling**: Vanilla CSS with custom glassmorphism design tokens (`src/config/designTokens.ts`, `src/styles/global.css`)
- **Speech & Audio**: Web Speech API, Web Audio API DSP AnalyserNode, Microsoft Edge TTS neural speech
- **Graphics**: Canvas 2D / WebGL 3D Holographic Particle Globe with voice audio-reactivity

---

## 3. Directory Layout & Module Structure

```
jarvis-frontend/
├── src/
│   ├── api/                     # Backend API client bindings
│   │   ├── automation.ts        # Scheduled crons & automation tasks
│   │   ├── capabilities.ts      # Subsystem capability declarations
│   │   ├── chat.ts              # Conversational DAG & tool execution stream
│   │   ├── client.ts            # Base HTTP client with auto-reconnection
│   │   ├── coding.ts            # Python sandbox & AST analyzer
│   │   ├── diagnostics.ts       # System hardware & service metrics
│   │   ├── files.ts             # File upload, parsing, and retrieval
│   │   ├── generation.ts        # Document & presentation generation
│   │   ├── memory.ts            # Long-term knowledge base inspection
│   │   ├── projects.ts          # Project workspaces & task tracker
│   │   ├── research.ts          # Deep web research & citations
│   │   ├── settings.ts          # Voice, wakeword, and preferences
│   │   ├── speech.ts            # Neural TTS speech synthesizer
│   │   ├── study.ts             # Study notes, MCQs, and flashcards
│   │   └── system.ts            # Core liveness and health probes
│   ├── assets/                  # Ambient background video & media
│   ├── components/              # Reusable futuristic UI components
│   │   ├── AmbientHud.tsx       # Subtle futuristic ambient grid overlay
│   │   ├── CodeBlock.tsx        # Syntax-highlighted code with run button
│   │   ├── CommandPaletteModal.tsx # Ctrl+K spotlight command search
│   │   ├── DashboardWorkspace.tsx  # At-a-glance system metrics & agent matrix
│   │   ├── ResearchWorkspace.tsx   # DuckDuckGo multi-source search & citations
│   │   ├── CodeWorkspace.tsx       # Sandbox runtime, AST refactoring & tests
│   │   ├── IntegrationsWorkspace.tsx # Subsystem health matrix & ping probes
│   │   ├── HolographicGlobe.tsx    # 3D audio-reactive particle sphere
│   │   ├── NavigationSidebar.tsx   # Collapsible 12-item workspace sidebar
│   │   ├── TopNavigationBar.tsx    # Live clock, telemetry, mode pills & hotkeys
│   │   ├── ToastNotificationSystem.tsx # Floating sci-fi HUD notifications
│   │   └── ...
│   ├── config/
│   │   └── designTokens.ts      # Colors, typography, glassmorphism, z-index
│   ├── services/
│   │   ├── aiVisualController.ts # Visual state manager & TTS audio synchronizer
│   │   ├── permissionManager.ts  # Diagnostic logs & capability tracking
│   │   └── speechManager.ts      # Voice Activity Detection (VAD) & speech recognition
│   ├── styles/
│   │   └── global.css           # Futuristic glassmorphism tokens, HUD classes
│   ├── App.tsx                  # Root application orchestrator
│   └── main.tsx                 # React DOM mount point
```

---

## 4. State Management & Data Flow

1. **Reactive UI State**:
   - Central view routing is driven by `currentView` in `App.tsx` (`'core' | 'dashboard' | 'research' | 'coding' | 'integrations' | ...`).
   - Modals and drawers (`StudyModePanel`, `GeneratedFilesDrawer`, `ProjectManagerModal`, `MemoryInspectorModal`, `AutomationModal`, `SettingsModal`, `DeveloperDiagnosticsOverlay`, `CommandPaletteModal`) open on-demand.
2. **Audio & Voice Flow**:
   - `speechManager` captures microphone input with continuous hands-free VAD or push-to-talk.
   - Spoken transcripts stream live to the UI via `interimTranscript` bubbles.
   - When speech concludes, `askJarvis()` is invoked.
   - `requestSpeech()` fetches neural speech bytes from `/api/speech/synthesize`, piping the audio element through `aiVisualController.connectTTSAudio()` to modulate the 3D Holographic Globe in real time.
3. **DAG Plan Execution**:
   - Assistant responses with multi-step workflows deliver `planSteps` objects rendered via `PlanExecutionIndicator`.
   - Tool events (`web_search`, `python_sandbox`, `math_eval`) display in the `ActivityMonitor`.
