# JARVIS 2.0 Tool Registry & Execution Specification

This document details all registered tools, their JSON input schemas, execution handlers, and security risk classifications.

---

## 1. Tool Classification & Risk Tiers

Tools in JARVIS are assigned one of four strict risk levels:
- **`LEVEL 0: READ-ONLY`**: Passive execution. Auto-approved in all safety tiers.
- **`LEVEL 1: LOCAL SAFE WRITE`**: Non-destructive operations inside `./data/workspace`. Auto-approved in `ASSISTED` and `FULL CONTROL`.
- **`LEVEL 2: EXTERNAL ACTION`**: Outbound network requests, live search, web page fetching. Auto-approved in `ASSISTED` and `FULL CONTROL`.
- **`LEVEL 3: HIGH IMPACT / SYSTEM BRIDGE`**: Launching OS applications, running sandboxed code, destructive operations. Triggers **Interactive Confirmation Modal** in `ASSISTED` mode.

---

## 2. Core Tool Registry

### 2.1 `web_search` (Level 2)
Performs multi-query search across live web sources via DuckDuckGo.
```json
{
  "name": "web_search",
  "description": "Execute live internet web search for current real-time data.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "Search query keywords" },
      "max_results": { "type": "integer", "default": 5 }
    },
    "required": ["query"]
  }
}
```

### 2.2 `math_engine` (Level 0)
Evaluates algebraic formulas, calculus derivatives, matrix determinants, and descriptive statistics.
```json
{
  "name": "math_engine",
  "description": "Calculate exact step-by-step calculus, matrix determinants, and statistics.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "Math expression, derivative, matrix, or array" }
    },
    "required": ["query"]
  }
}
```

### 2.3 `execute_python_code` (Level 3 - High Impact)
Executes user/agent-generated Python code inside an isolated subprocess sandbox with strict CPU timeout and output caps.
```json
{
  "name": "execute_python_code",
  "description": "Execute Python code in an isolated execution sandbox.",
  "parameters": {
    "type": "object",
    "properties": {
      "code": { "type": "string", "description": "Python code snippet" },
      "timeout": { "type": "integer", "default": 15 }
    },
    "required": ["code"]
  }
}
```

### 2.4 `generate_pdf_report` (Level 1)
Generates publication-quality PDF documents with headers, tables, math formatting, and page numbers via ReportLab.

### 2.5 `generate_presentation_deck` (Level 1)
Generates modern 16:9 widescreen PowerPoint presentations with custom color themes and speaker notes via python-pptx.

### 2.6 `open_application` (Level 3 - High Impact)
Launches authorized Windows / host applications (Notepad, Calculator, VS Code, Browser) with explicit user confirmation.
