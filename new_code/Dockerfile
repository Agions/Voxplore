# Voxplore Dockerfile - 优化版本
# 支持 GPU 加速和离线安装

FROM nvidia/cuda:12.1-runtime-ubuntu22.04 AS base

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libnotify4 \
    libnss3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 设置 Python 符号链接
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

WORKDIR /app

# 预安装 CPU 版本的 PyTorch（减少镜像体积）
RUN pip install --no-cache-dir \
    torch==2.2.0 \
    --index-url https://download.pytorch.org/whl/cpu

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（分阶段缓存优化）
RUN pip install --no-cache-dir --break-system-packages \
    -r requirements.txt || true

# 如果 GPU 可用，安装 GPU 版本（构建时指定）
# RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu121

# 复制应用代码
COPY . .

# 创建缓存目录
RUN mkdir -p ~/.cache/voxplore && \
    mkdir -p ~/.cache/voxplore/extractor && \
    mkdir -p ~/.cache/voxplore/checkpoints

# 设置环境变量（运行时配置）
ENV QT_QPA_PLATFORM=offscreen
ENV DISPLAY=
ENV HF_HOME=/workspace/.cache/huggingface
ENV TRANSFORMERS_CACHE=/workspace/.cache/transformers

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# 默认启动命令（无 GUI 模式）
CMD ["python", "-m", "app.main", "--cli"]

# ==================== 构建说明 ====================
# 
# 构建命令：
#   # CPU 版本
#   docker build -t voxplore:1.0.1 -f Dockerfile .
#
#   # GPU 版本（需要 nvidia-container-toolkit）
#   docker build -t voxplore:1.0.1-gpu --build-arg ENABLE_GPU=1 -f Dockerfile.gpu .
#
# 运行命令：
#   # CLI 模式
#   docker run --rm -it voxplore:1.0.1 python -m app.main --cli
#
#   # 挂载本地目录
#   docker run --rm -it -v /path/to/videos:/workspace/videos \
#       -v /path/to/output:/workspace/output \
#       -e DEEPSEEK_API_KEY=sk-xxx \
#       voxplore:1.0.1
#
# GPU 运行：
#   docker run --rm --gpus all -it \
#       -v /path/to/videos:/workspace/videos \
#       voxplore:1.0.1-gpu
#
# ==================== 多架构构建 ====================
# docker buildx create --name voxplore-builder
# docker buildx use voxplore-builder
# docker buildx build --platform linux/amd64,linux/arm64 \
#     -t voxplore:1.0.1 --push .
