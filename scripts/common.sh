#!/bin/bash
# Voxplore 构建脚本公共函数
# 由 build_macos.sh / build_linux.sh 等 source 调用

set -e

# ── 版本号（单一真相来源：pyproject.toml）───────────────────────
VERSION=$(grep '^version = ' pyproject.toml 2>/dev/null | sed 's/version = "//;s/"//' | tr -d '[:space:]')

if [ -z "$VERSION" ]; then
    echo "❌ 无法从 pyproject.toml 读取版本号"
    exit 1
fi

# ── 项目根目录 ─────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── 颜色输出 ───────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }
step()    { echo -e "${CYAN}[STEP]${NC}  $*"; }
