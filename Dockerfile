# Multi-stage Dockerfile for JARVIS Full-Stack Assistant

# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY jarvis-frontend/package*.json ./
RUN npm ci
COPY jarvis-frontend/ ./
RUN npm run build

# Stage 2: Python Backend & Runtime Environment
FROM python:3.11-slim AS runner

WORKDIR /app

# Install system utilities (curl, fonts for reportlab PDF generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    fontconfig \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY AI/Backend/DR-doom-Day-2-Backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY AI/Backend/DR-doom-Day-2-Backend/app ./app

# Copy built frontend assets
COPY --from=frontend-builder /app/frontend/dist ./static

# Prepare data storage directories
RUN mkdir -p /app/data/workspace /app/data/generated_files /app/data/uploads

ENV PORT=8765
ENV HOST=0.0.0.0
ENV ENVIRONMENT=production

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8765/api/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765"]
