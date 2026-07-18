# SEO + AEO Agent — single-container image (FastAPI backend serving the React build).
# Bundles headless Chromium (run_lighthouse), git (clone/commit), and Node (Lighthouse) —
# the capabilities that rule out pure serverless.

# --- Stage 1: build the React frontend ---
FROM node:20-bookworm-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: runtime ---
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    CHROME_PATH=/usr/bin/chromium \
    UV_LINK_MODE=copy

# System deps: git, Chromium + runtime libs, Node (for Lighthouse).
RUN apt-get update && apt-get install -y --no-install-recommends \
        git ca-certificates curl gnupg \
        chromium fonts-liberation libasound2 libnss3 libxss1 libgbm1 libxshmfence1 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g lighthouse@12 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# uv for fast, reproducible installs.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /srv
# Install dependencies first (cached across code changes).
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# App code + built frontend, then install the project itself.
COPY app/ ./app/
COPY api/ ./api/
COPY seo_data_mcp/ ./seo_data_mcp/
COPY eval/ ./eval/
COPY integrations/ ./integrations/
COPY --from=frontend /fe/dist ./frontend/dist
RUN uv sync --frozen --no-dev

ENV PATH="/srv/.venv/bin:$PATH"
# Cloud Run injects $PORT (default 8080). Shell form so it expands.
CMD uvicorn api.main:api --host 0.0.0.0 --port ${PORT:-8080}
