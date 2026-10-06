# JARVIS 2.0 Frontend State Management

## 1. Overview

JARVIS 2.0 uses a high-performance, modular state management architecture designed to handle concurrent background telemetry, real-time voice streaming, and responsive multi-workspace navigation without unnecessary re-renders.

---

## 2. State Partitioning

### 2.1 Core Orchestrator State (`App.tsx`)
- **`currentView`**: Active workspace view (`core`, `dashboard`, `research`, `coding`, `integrations`, `projects`, etc.).
- **`messages`**: Chronological conversation history, citations, generated files, plan step executions, and interactive code blocks.
- **`status`**: Current AI status (`idle`, `listening`, `thinking`, `searching`, `executing`, `speaking`, `error`).
- **`activeMode`**: Operational mode (`general`, `study`, `research`, `coding`).
- **`activeProjectId`**: Active project context passed to LLM system prompts.

### 2.2 Audio & Speech Controller (`services/speechManager.ts`)
- **`VoiceState`**: State machine (`IDLE`, `LISTENING`, `PROCESSING`, `SPEAKING`, `ERROR_RECOVERY`).
- **`interimTranscript`**: High-frequency streaming text chunks displayed live during user utterance.
- **`finalTranscript`**: Finalized speech transcript dispatched to `sendChatMessage()`.

### 2.3 Visual Audio Reactive Controller (`services/aiVisualController.ts`)
- Connects directly to Web Audio API `AudioContext` and `AnalyserNode`.
- Computes frequency spectrum bands at 60 FPS to drive 3D particle amplitude in `HolographicGlobe.tsx`.

### 2.4 Event Bus & Notifications (`components/ToastNotificationSystem.tsx`)
- Lightweight, zero-dependency Pub/Sub listener registry for instant toast alerts across asynchronous subtasks.

---

## 3. Communication with Backend

```text
Frontend React 19              FastAPI Backend (Port 8765)
       |                                     |
       |--- POST /api/chat ----------------->| (DAG Decomposition & ModelRouter)
       |<-- { reply, planSteps, citations }--|
       |                                     |
       |--- POST /api/speech/synthesize ---->| (Edge TTS Neural Synthesizer)
       |<-- audio/mpeg stream ---------------|
       |                                     |
       |--- GET /health & /diagnostics ----->| (Hardware & Subsystem Probes)
       |<-- { items, systemMetrics } --------|
```
