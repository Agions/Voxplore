# Voxplore (Voxplore) - CPU Version
# AI-Powered Video Creation Desktop App

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:0 \
    QT_X11_NO_MITSHM=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Qt/X11 dependencies for PySide6
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxkbcommon-x11-0 \
    libegl1 \
    libopengl0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    # Audio/Video processing
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender1 \
    # Additional utilities
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only dependency files first for better caching
COPY pyproject.toml requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    PySide6>=6.9.0 \
    Shiboken6>=6.9.0 \
    opencv-python>=4.8.1 \
    numpy>=1.26.0 \
    pillow>=10.1.0 \
    pydub>=0.25.0 \
    librosa>=0.10.0 \
    soundfile>=0.12.0 \
    faster-whisper>=1.0.0 \
    torch>=2.0.0 \
    edge-tts>=6.1.0 \
    scenedetect>=0.6.0 \
    deepl>=1.18.0 \
    requests>=2.31.0 \
    httpx>=0.25.0 \
    python-dotenv>=1.0.0 \
    pyyaml>=6.0.1 \
    psutil>=5.9.6 \
    cryptography>=41.0.0 \
    keyring>=24.0.0 \
    openai>=1.0.0 \
    google-generativeai>=0.8.0 \
    moviepy>=1.0.3 \
    packaging>=21.0

# Copy application code
COPY app ./app
COPY config ./config
COPY resources ./resources
COPY main.py ./

# Create necessary directories
RUN mkdir -p /app/logs /app/cache /app/output

# Set environment variables for app
ENV APP_HOME=/app \
    APP_CACHE=/app/cache \
    APP_OUTPUT=/app/output

# Expose ports (if running as server)
EXPOSE 7860 8080

# Entrypoint script
ENTRYPOINT ["/app/scripts/docker_entrypoint.sh"]
CMD ["python", "-m", "app.main"]
