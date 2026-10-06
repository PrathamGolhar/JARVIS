# JARVIS Local Setup & Installation Guide

Follow this step-by-step guide to configure and run JARVIS on Windows, Linux, or macOS.

---

## 1. Prerequisites

- **Python**: Version 3.11 or newer (Python 3.13 tested)
- **Node.js**: Version 18.0.0 or newer with npm
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

# Install requirements
pip install -r requirements.txt
```

### 2.2 Frontend Setup
```bash
cd ../../../jarvis-frontend
npm install
```

---

## 3. Environment Variables Configuration

Copy `.env.example` to `.env` in `backend/`:

```bash
cd ../backend
cp .env.example .env
```

Configure your preferred API keys:
```ini
JARVIS_AI_PROVIDER=auto
GOOGLE_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=
ELEVENLABS_API_KEY=
JARVIS_PERMISSION_MODE=assisted
```

*Note: Even without cloud API keys, JARVIS will operate using its offline Local Rule Engine.*

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
cd jarvis-frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 5. Verification

To verify full system integrity:
```bash
cd backend
python -m pytest -v
```
