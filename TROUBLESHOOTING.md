# JARVIS 2.0 Troubleshooting & Diagnostic Guide

This guide provides step-by-step diagnostic procedures and solutions for common operational issues across the JARVIS system.

---

## 1. Quick Diagnostics Check

Run the built-in system diagnostics probe from terminal or browser:

### Via Browser:
- Navigate to `http://127.0.0.1:8765/health`
- View detailed AI subsystem status at `http://127.0.0.1:8765/health/ai`
- View storage metrics at `http://127.0.0.1:8765/health/storage`

### In Frontend HUD:
- Press `Ctrl + K` and select **"System Diagnostics & Real-Time Probes"** (or press the diagnostics button in the activity monitor).

---

## 2. Common Issues & Solutions

### 2.1 Backend Port 8765 Already in Use
**Symptom**: `ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8765)`
**Solution**:
1. Check what process is occupying port 8765:
   ```powershell
   Get-NetTCPConnection -LocalPort 8765 | Select-Object OwningProcess
   ```
2. Terminate the stale uvicorn instance:
   ```powershell
   Stop-Process -Id <PID> -Force
   ```
3. Restart via `.\start-dev.ps1`.

---

### 2.2 AI Provider Fallback / API Key Missing
**Symptom**: Responses indicate local fallback or "API key is not configured".
**Solution**:
1. Verify that your `.env` file exists at `backend/.env` (or root `.env`).
2. Ensure `GOOGLE_API_KEY`, `GROQ_API_KEY`, or `OPENAI_API_KEY` contains a valid key without trailing quotes.
3. Restart the backend process.

---

### 2.3 Neural Voice Synthesis Unavailable
**Symptom**: Frontend shows "Edge voice synthesis unavailable".
**Solution**:
- Ensure the backend has an active internet connection to stream neural voices from Edge-TTS.
- If offline, text chat and all document/agent generation remain 100% operational.

---

### 2.4 Document Generation Font or Package Errors
**Symptom**: `ImportError: No module named 'reportlab'` or `docx`
**Solution**:
- Ensure all Python dependencies are installed in your active virtual environment:
  ```bash
  pip install -r requirements.txt
  ```

---

## 3. Structured Logging
Backend logs are output with timestamps and subsystem tags:
```text
2026-09-24 04:00:15 [INFO] jarvis.main: JARVIS PRODUCTION AI ASSISTANT CORE ONLINE
2026-09-24 04:00:16 [INFO] jarvis.model_router: JARVIS Model Router: category=deep_reasoning -> provider=gemini
2026-09-24 04:00:17 [INFO] jarvis.task_graph: TaskGraph: Starting task 'Generate Presentation' (step_2)
```
