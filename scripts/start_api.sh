#!/bin/bash
# ==============================================================================
# SceneFab API 服务启动脚本
# 运行前进行依赖检查、环境变量验证与健康状态确认
# ==============================================================================

set -e

# 确保在项目根目录运行
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "=================================================="
echo "🚀 启动 SceneFab API 服务"
echo "=================================================="

# 1. 自动读取 .env 环境变量
if [ -f .env ]; then
    echo "📄 正在加载 .env 配置文件..."
    export $(grep -v '^#' .env | xargs)
fi

# 2. 依赖工具校验
echo "🔍 正在进行依赖检查..."
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "❌ 警告: 未找到 FFmpeg 可执行程序，部分视频处理功能可能无法正常工作。"
else
    echo "  ✅ FFmpeg 可用"
fi

if ! command -v ffprobe >/dev/null 2>&1; then
    echo "❌ 警告: 未找到 FFprobe 可执行程序。"
else
    echo "  ✅ FFprobe 可用"
fi

# 3. 参数配置
HOST="${API_HOST:-0.0.0.0}"
PORT="${API_PORT:-8000}"
WORKERS="${API_WORKERS:-1}"
LOG_LEVEL="${LOG_LEVEL:-info}"

export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

echo "=================================================="
echo "🌐 API 启动配置:"
echo "   Host:      $HOST"
echo "   Port:      $PORT"
echo "   Workers:   $WORKERS"
echo "   LogLevel:  $LOG_LEVEL"
echo "=================================================="

# 4. 启动 uvicorn 服务
exec uvicorn app.api.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "$LOG_LEVEL"
