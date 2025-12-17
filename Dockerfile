# Use Python 3.11 slim image for smaller size
FROM python:3.12-slim

WORKDIR /app

# Environment variables for Python and faster-whisper
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# faster-whisper performance optimizations
ENV OMP_NUM_THREADS=4
ENV MKL_NUM_THREADS=4
# Disable CUDA to force CPU execution
ENV CUDA_VISIBLE_DEVICES=""

# Install system dependencies
# - ffmpeg: Audio decoding for faster-whisper
# - gcc: Compile Python packages
# - tesseract: OCR for resume parsing
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        curl \
        ffmpeg \
        tesseract-ocr \
        tesseract-ocr-eng \
        && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create directories for models and media storage
RUN mkdir -p /app/models /app/media_storage \
    && chmod 755 /app/models /app/media_storage

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

 #Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]