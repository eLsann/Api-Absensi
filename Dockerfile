# =========================================================
# Absensi API - Production Dockerfile
# Optimized for low-RAM servers (2GB constraint)
# =========================================================

# Stage 1: Build dependencies (terpisah untuk layer cache optimal)
FROM python:3.10-slim AS builder

WORKDIR /build

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements DAHULU — Docker layer cache akan skip pip install
# jika requirements.txt tidak berubah. KRITIS untuk PyTorch ~2GB layer!
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# =========================================================
# Stage 2: Production image (slim, tanpa build tools)
# =========================================================
FROM python:3.10-slim AS production

# Metadata
ARG BUILD_DATE
ARG GIT_SHA
LABEL org.opencontainers.image.created="$BUILD_DATE"
LABEL org.opencontainers.image.revision="$GIT_SHA"
LABEL org.opencontainers.image.title="Absensi API"
LABEL org.opencontainers.image.description="Face Recognition Attendance API"

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Disable PyTorch telemetry
    PYTORCH_NO_CUDA_MEMORY_CACHING=1 \
    # Paksa CPU inference (tidak ada GPU di VM 2GB)
    CUDA_VISIBLE_DEVICES=""

# Set working directory
WORKDIR /app

# Install runtime sistem deps untuk OpenCV + curl untuk healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    # OpenCV runtime deps
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    # curl untuk Docker HEALTHCHECK
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages dari builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy source code
COPY . .

# Expose port
EXPOSE 8001

# ─── Docker Health Check ────────────────────────────────────
# start_period: 60s karena PyTorch model load butuh ~30-60 detik
# interval: 30s — cek berkala
# timeout: 10s — batas waktu per cek
# retries: 3 — berapa kali gagal sebelum mark unhealthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# ─── Command ─────────────────────────────────────────────────
# PENTING UNTUK 2GB RAM:
# --workers 1   → PyTorch satu instance saja (~1.5GB RAM)
#                 Satu worker cukup untuk penggunaan kamera CCTV/Webcam
#                 (tidak banyak concurrent user)
# --backlog 64  → Antrian koneksi dibatasi (tidak buang RAM)
# Gunakan env var WORKERS untuk override (default 1)
CMD ["sh", "-c", "python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --workers ${WORKERS:-1} \
    --backlog 64 \
    --timeout-keep-alive 30 \
    --access-log"]
