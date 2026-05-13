# ── Stage 1: build dependencies ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /install

COPY requirements.txt .

# Install only production deps into a separate prefix so we can copy them clean
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt


# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.11-slim

# opencv-python-headless needs these system libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install/deps /usr/local

# Copy application source
COPY app/ ./app/
COPY ui/  ./ui/

# Non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Cloud Run / Railway inject PORT env var; default to 8000 locally
ENV PORT=8000

EXPOSE $PORT

# Resource-conscious settings:
#   --workers 1        → single process (cloud gives you one vCPU on free tier)
#   --timeout-keep-alive 30 → drop idle connections quickly
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --timeout-keep-alive 30"]
