FROM python:3.11-slim

# Prevent interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Install system dependencies for audio, camera, and compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libportaudio2 \
    portaudio19-dev \
    libasound2-dev \
    alsa-utils \
    ffmpeg \
    sox \
    libsox-fmt-all \
    curl \
    git \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml from root build context
COPY pyproject.toml /app/pyproject.toml

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    hatchling \
    pydantic-settings \
    paho-mqtt \
    fastapi \
    uvicorn \
    pydantic \
    httpx \
    pyyaml \
    numpy \
    psutil \
    sounddevice \
    soundfile \
    faster-whisper \
    piper-tts \
    onnxruntime \
    opencv-python-headless

# Copy application source code
COPY brain/ /app/brain/
COPY schemas/ /app/schemas/

ENV PYTHONPATH=/app
WORKDIR /app

EXPOSE 8000

CMD ["uvicorn", "brain.main:app", "--host", "0.0.0.0", "--port", "8000"]
