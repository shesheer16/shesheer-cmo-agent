FROM python:3.11-slim

# System dependencies for faster-whisper and chromadb
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev deps in prod)
RUN uv sync --frozen --no-dev

# Copy source
COPY . .

# Ensure data directories exist
RUN mkdir -p data/chromadb data/logs data/audio_cache

# Default port
ENV PORT=8000

CMD ["python", "main.py", "--bot"]
