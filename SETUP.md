# JARVIS Local Setup & Installation Guide

Follow this step-by-step guide to configure and run JARVIS on Windows, Linux, or macOS.

---

## 1. Prerequisites

- **Python**: Version 3.11 or newer (CI currently runs Python 3.11)
- **Node.js**: Version 20 or newer with npm
- **Git**: For source version control
- Optional: Virtual environment (`venv`) or `uv`

---

## 2. Clone and Dependencies

```bash
git clone <repository_url> JARVIS
cd JARVIS
```

### 2.1 Backend Setup
```bash
cd backend

# (Optional) Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Install runtime and development/test requirements
pip install -r requirements-dev.txt
```

### 2.2 Frontend Setup
```bash
cd ../frontend
npm ci
```

---

## 3. Environment Variables Configuration

Copy `.env.example` to `.env` in `backend/`:

```bash
cd ../backend
cp .env.example .env
```

Set a strong API key and configure any cloud providers you intend to use:
```ini
JARVIS_API_KEY=replace_with_a_long_random_secret
JARVIS_AI_PROVIDER=auto
GOOGLE_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=
JARVIS_PERMISSION_MODE=assisted
```

*Note: Without cloud API keys, JARVIS can use `LocalProvider`, a rule-based fallback rather than a general-purpose offline language model. If `JARVIS_API_KEY` is unset, the backend generates an ephemeral key and logs it; configure a key before exposing the service.*

---

## 4. Running Locally

### Start Backend
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

### Start Frontend
In a second terminal:
```bash
cd frontend
npm run dev
```

Open `http://localhost:1420` in your browser. The backend API is at `http://127.0.0.1:8765`.

---

## 5. Verification

To verify full system integrity:
```bash
cd backend
python -m pytest -v
```
