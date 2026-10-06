# JARVIS Production Deployment & Operations Guide

This guide details deployment options for running JARVIS in production, ranging from bare-metal local environments to containerized Docker deployments and cloud Kubernetes setups.

---

## 1. System Requirements

### Hardware Requirements
- **Minimum**: 2 vCPU, 4GB RAM, 10GB free disk space.
- **Recommended**: 4+ vCPU, 8GB+ RAM, SSD storage.

### Software Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: 18.x or 20.x LTS
- **Docker & Docker Compose**: (Optional, for containerized deployment)

---

## 2. Bare-Metal / Local Server Deployment

### 2.1 Backend Deployment with Systemd / Supervisord
1. Prepare python virtual environment:
   ```bash
   cd AI/Backend/DR-doom-Day-2-Backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
2. Configure `.env` with production keys:
   ```bash
   cp .env.example .env
   # Edit .env with your Google Gemini / Groq API keys and environment=production
   ```
3. Run with Gunicorn + Uvicorn workers:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8765
   ```

### 2.2 Frontend Static Build & Hosting
1. Build optimized production bundle:
   ```bash
   cd jarvis-frontend
   npm ci
   npm run build
   ```
2. Serve static `dist/` bundle using Nginx, Caddy, or Cloudflare Pages.

---

## 3. Containerized Deployment (Docker Compose)

The repository provides a production multi-stage `Dockerfile` and `docker-compose.yml`.

### Launching with Docker Compose:
```bash
# 1. Provide your API keys
export GOOGLE_API_KEY="your-gemini-key"
export GROQ_API_KEY="your-groq-key"

# 2. Build and run
docker compose up -d --build
```

### Checking Container Health:
```bash
docker compose ps
docker compose logs -f jarvis-backend
```

---

## 4. Reverse Proxy Setup (Nginx Example)

```nginx
server {
    listen 80;
    server_name jarvis.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name jarvis.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/jarvis.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/jarvis.yourdomain.com/privkey.pem;

    # Frontend Static Distribution
    location / {
        root /var/www/jarvis/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8765/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Audio streaming & long document generation timeouts
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

---

## 5. Backup & Persistence
- **Database**: The SQLite database is located at `./data/jarvis.db` (or `/app/data/jarvis.db` in Docker). Backup regularly.
- **Generated Artifacts & Uploads**: Located under `./data/workspace` and `./data/generated_files`.
