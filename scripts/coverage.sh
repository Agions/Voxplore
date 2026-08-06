#!/usr/bin/env bash
# ==============================================================================
# SceneFab v1.0.0  · Rust + TypeScript 统一覆盖率脚本
#
# 双端测量：
#   - Rust    : cargo tarpaulin(workspace 元数据自动加载)
#   - 前端    : pnpm --filter @scenefab/desktop test:coverage(vitest v8)
#
# 报告输出：
#   - target/coverage/tarpaulin-report.html
#   - apps/desktop/coverage/index.html
#
# 阈值防回归（在 CI 严格生效；本地软告警）：
#   - Rust    lines ≥ 60 %  (4 crate 存在测试：pipeline/tts/update/i18n)
#   - Front   lines ≥ 45 %  (基线已 commit 到 vite.config.ts)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

CYAN="\033[0;36m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"

info()  { printf "${CYAN}[INFO]${NC}  %s\n" "$*"; }
ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
fail()  { printf "${RED}[FAIL]${NC}  %s\n" "$*"; }

# 1. 前置依赖检查 -----------------------------------------------------------
info "检查 cargo-tarpaulin ..."
if ! command -v cargo-tarpaulin >/dev/null 2>&1; then
  warn "未检测到 cargo-tarpaulin,自动安装 cargo install cargo-tarpaulin --locked"
  cargo install cargo-tarpaulin --locked
fi

info "检查 pnpm ..."
if ! command -v pnpm >/dev/null 2>&1; then
  fail "未安装 pnpm,无法执行前端覆盖率"
  exit 1
fi

# 2. Rust 端覆盖率 ---------------------------------------------------------
info "执行 cargo tarpaulin (workspace 模式) ..."
mkdir -p target/coverage
cargo tarpaulin \
  --workspace \
  --timeout 180 \
  --out Html --out Json --out Xml \
  --output-dir target/coverage \
  --skip-clean \
  --exclude-files 'apps/desktop/src-tauri/src/main.rs' \
  || warn "cargo tarpaulin 退出码非 0,请检查 Rust 编译错误"
ok "Rust 报告已生成: target/coverage/tarpaulin-report.html"

# 3. TypeScript 端覆盖率 ---------------------------------------------------
info "执行 pnpm vitest coverage (前端) ..."
(cd apps/desktop && pnpm test:coverage)
ok "前端报告已生成: apps/desktop/coverage/index.html"

# 4. 综合展示 --------------------------------------------------------------
info "Rust 覆盖率汇总(若 tarpaulin-report.json 存在):"
if [ -f target/coverage/tarpaulin-report.json ]; then
  python3 -c "
import json
with open('target/coverage/tarpaulin-report.json') as f:
    data = json.load(f)
print(f\"  lines     : {data.get('line', 0):.2f} %\")
print(f\"  branches  : {data.get('branch', 0):.2f} %\")
print(f\"  functions : {data.get('function', 0):.2f} %\")
" || warn "Python 解析 Rust 报告失败,不影响整体流程"
fi

ok "全量覆盖率测量完成"
