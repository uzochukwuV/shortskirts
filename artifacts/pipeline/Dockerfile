FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install base requirements
RUN pip install --no-cache-dir -r requirements.txt

# Install OpenHands SDK separately (Python 3.11 compatible)
RUN pip install --no-cache-dir openhands-agent-sdk>=0.2.0 || pip install --no-cache-dir openhands-sdk>=0.2.0 || echo "SDK installation skipped"

# Copy application code
COPY src/ ./src/

# Set working directory to where main.py is located
WORKDIR /app/src

# Create empty .env if not exists
RUN touch /app/src/.env

# Environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/pipeline/providers/status')" || exit 1

# Run with uvicorn (single worker for ECS compatibility)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
