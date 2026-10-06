# JARVIS 2.0 Developer & Plugin SDK Guide

This guide details local development workflows, adding custom agents and tools, and writing plugins using the JARVIS 2.0 Plugin SDK.

---

## 1. Project Directory Layout

```text
JARVIS/
├── backend/   # FastAPI Backend Core
│   ├── app/
│   │   ├── api/                       # REST endpoint routers
│   │   ├── services/
│   │   │   ├── agents/                # Orchestrator, TaskGraph, Study, Doc agents
│   │   │   ├── ai/                    # Multi-provider abstraction & ModelRouter
│   │   │   ├── coding/                # Code sandbox & AST analyzers
│   │   │   ├── document_generation/   # ReportLab, python-docx, python-pptx, openpyxl
│   │   │   ├── events/                # Asynchronous EventBus
│   │   │   ├── file_processing/       # PDF/Office parsers, OCR, MultiDoc reasoner
│   │   │   ├── memory/                # SQLite persistent store & RAG
│   │   │   ├── plugins/               # Plugin SDK & Registry
│   │   │   ├── research/              # DuckDuckGo search & scraping
│   │   │   ├── study_mode/            # Notes generator & MCQ exam prep
│   │   │   └── tools/                 # Tool registry, MathEngine, Calculator
│   │   └── settings.py                # Environment configuration
│   └── tests/                         # Pytest test suites
│
├── jarvis-frontend/                   # React 19 + TypeScript + Vite HUD
│   ├── src/
│   │   ├── api/                       # Typed backend fetch clients
│   │   ├── components/                # HUD panels, CommandPalette, Modals, 3D Globe
│   │   ├── services/                  # SpeechManager, AIVisualController
│   │   └── App.tsx                    # Main mission command interface
│
├── start-dev.ps1                      # Windows one-click startup launcher
└── start-dev.sh                       # Linux / macOS startup launcher
```

---

## 2. Creating a Custom Plugin

JARVIS 2.0 features an extensible plugin SDK (`app.services.plugins`).

### Example: Writing a Custom Weather Plugin
```python
from app.services.plugins.base import JARVISPlugin, PluginToolDefinition, PermissionScope

class MyCustomPlugin(JARVISPlugin):
    name = "custom_weather_plugin"
    version = "1.0.0"
    description = "Provides real-time local weather forecasts."

    def get_tools(self) -> list[PluginToolDefinition]:
        return [
            PluginToolDefinition(
                name="get_weather_forecast",
                description="Fetch 7-day weather forecast for a specified city.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City name"}
                    },
                    "required": ["city"],
                },
                handler=self._fetch_weather,
                required_permissions=[PermissionScope.EXTERNAL_NETWORK],
                is_high_impact=False,
            )
        ]

    def _fetch_weather(self, city: str) -> dict:
        return {"city": city, "temperature": "22°C", "condition": "Sunny"}

# Register plugin
from app.services.plugins.base import plugin_registry
plugin_registry.register_plugin(MyCustomPlugin())
```

---

## 3. Keyboard Shortcuts in JARVIS HUD
- `Ctrl + K` (or `Cmd + K` on macOS): Opens the **JARVIS Command Palette** for rapid search across all capabilities.
- `Escape`: Closes open modals and drawers.
- `Enter`: Sends chat command or selects active command palette item.
