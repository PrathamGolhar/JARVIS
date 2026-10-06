# JARVIS 2.0 Frontend Component Directory

## 1. Component Catalog

| Component | Category | Path | Description |
| :--- | :--- | :--- | :--- |
| **`TopNavigationBar`** | Navigation | `src/components/TopNavigationBar.tsx` | Real-time clock, system health indicator, mode pills, `Ctrl+K` trigger, focus toggle. |
| **`NavigationSidebar`** | Navigation | `src/components/NavigationSidebar.tsx` | 12-item collapsible sidebar for switching workspaces with live badge counts. |
| **`CommandPaletteModal`** | Overlay | `src/components/CommandPaletteModal.tsx` | Fast keyboard-first modal (`Ctrl+K`) for global commands, modes, and exports. |
| **`ToastNotificationSystem`**| HUD Feedback| `src/components/ToastNotificationSystem.tsx` | Floating glassmorphism notifications dispatched via global `showToast()`. |
| **`DashboardWorkspace`** | Workspace | `src/components/DashboardWorkspace.tsx` | High-level system telemetry, active projects, agent ecosystem matrix, quick actions. |
| **`ResearchWorkspace`** | Workspace | `src/components/ResearchWorkspace.tsx` | Live DuckDuckGo search, depth selectors, multi-source synthesis, grounded citations. |
| **`CodeWorkspace`** | Workspace | `src/components/CodeWorkspace.tsx` | Subprocess sandbox runtime, AST analyzer, auto-refactor and unit test synthesis. |
| **`IntegrationsWorkspace`** | Workspace | `src/components/IntegrationsWorkspace.tsx` | Real-time status probes, latency benchmarking, and subsystem ping tool. |
| **`OrbControl`** | Core Voice | `src/components/OrbControl.tsx` | Central interactive wrapper for the 3D Holographic Globe with audio reactivity. |
| **`HolographicGlobe`** | 3D Canvas | `src/components/HolographicGlobe.tsx` | Particle-based 3D sphere rendered in Canvas 2D with audio-responsive pulsation. |
| **`ActivityMonitor`** | HUD Panel | `src/components/ActivityMonitor.tsx` | Live display of active and recent tool executions with micro-animations. |
| **`SystemStatus`** | HUD Panel | `src/components/SystemStatus.tsx` | Hardware CPU/RAM usage meters, battery stats, and subsystem diagnostic health. |
| **`BriefingPanel`** | HUD Panel | `src/components/BriefingPanel.tsx` | At-a-glance local environment readout, active user context, and time zone. |
| **`MovablePanel`** | Layout | `src/components/MovablePanel.tsx` | Draggable HUD container with smooth touch/pointer interaction and bounds clamping. |
| **`CodeBlock`** | Output | `src/components/CodeBlock.tsx` | Syntax-highlighted code viewer with copy and interactive execution sandbox trigger. |
| **`PlanExecutionIndicator`** | Workflow | `src/components/PlanExecutionIndicator.tsx` | Visual DAG step progress tracker with status badges (`pending`, `in_progress`, `done`). |
| **`CitationsList`** | Research | `src/components/CitationsList.tsx` | Verified source badges with domain pills and external links. |
| **`ActionConfirmationModal`**| Security | `src/components/ActionConfirmationModal.tsx` | Human-in-the-loop approval modal for privileged file and shell actions. |
| **`FileUploadDrawer`** | Media | `src/components/FileUploadDrawer.tsx` | Drag-and-drop document upload with automatic text parsing and ingestion. |
| **`StudyModePanel`** | Education | `src/components/StudyModePanel.tsx` | Comprehensive study suite: formula sheets, flashcard decks, MCQ quizzes. |
| **`GeneratedFilesDrawer`** | Artifacts | `src/components/GeneratedFilesDrawer.tsx` | Download manager for generated PDF, DOCX, PPTX, XLSX, and CSV documents. |
| **`ProjectManagerModal`** | Projects | `src/components/ProjectManagerModal.tsx` | Multi-project manager with task lists, notes, and file associations. |
| **`MemoryInspectorModal`** | Knowledge | `src/components/MemoryInspectorModal.tsx` | Long-term memory vector viewer and manual memory entry manager. |
| **`AutomationModal`** | Schedule | `src/components/AutomationModal.tsx` | Cron automation scheduler and recurring task monitor. |
| **`SettingsModal`** | Config | `src/components/SettingsModal.tsx` | Neural TTS voice picker, wake-word sensitivity, and theme configuration. |
| **`DeveloperDiagnosticsOverlay`**| Debugging| `src/components/DeveloperDiagnosticsOverlay.tsx` | Real-time audio DSP visualizer, VAD state, and raw speech transcript logs. |
