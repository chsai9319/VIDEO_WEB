# ─── Stage 1: Base image ───────────────────────────────────────────────────────
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# ─── Stage 2: Dependencies ─────────────────────────────────────────────────────
FROM base AS deps

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Stage 3: Final image ──────────────────────────────────────────────────────
FROM base AS final

WORKDIR /app

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin/gunicorn /usr/local/bin/gunicorn

# Copy application source
COPY --chown=appuser:appgroup app.py .
COPY --chown=appuser:appgroup templates/ templates/
COPY --chown=appuser:appgroup static/ static/

# Create uploads directory and set permissions
RUN mkdir -p /app/uploads && \
    chown -R appuser:appgroup /app/uploads

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Environment defaults (override via docker run -e or docker-compose)
ENV PORT=5000 \
    UPLOAD_FOLDER=/app/uploads \
    MAX_CONTENT_MB=2048 \
    FLASK_DEBUG=false \
    WORKERS=2

# Run with Gunicorn in production
CMD gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers "${WORKERS}" \
    --worker-class sync \
    --timeout 300 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    app:app
