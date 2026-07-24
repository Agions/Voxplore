#!/bin/bash
# SceneFab 构建脚本公共函数
# 由 build_macos.sh / build_linux.sh 等 source 调用

set -e

# ── 版本号（单一真相来源：src/scenefab/utils/version.py & pyproject.toml）─
VERSION=$(python3 -c "import sys; sys.path.insert(0, 'src'); from scenefab.utils.version import get_version_string; print(get_version_string())" 2>/dev/null)
if [ -z "$VERSION" ]; then
    VERSION=$(grep -E '^version = ' pyproject.toml 2>/dev/null | sed 's/.*"\(.*\)".*/\1/')
fi

if [ -z "$VERSION" ]; then
    echo "❌ 无法从 python 或 pyproject.toml 读取版本号"
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
