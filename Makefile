# SceneFab Makefile
# 多系统版本打包工具
#
# 使用方法:
#   make help          显示帮助
#   make build_win      Windows x64 (.zip)
#   make build_mac      macOS x64 (.dmg)
#   make build_mac_arm  macOS ARM64 (.dmg)
#   make build_linux    Linux x86_64 (.AppImage)
#   make test          运行测试
#   make clean         清理临时文件

.SUFFIXES:
.PHONY: help build build_win build_mac build_mac_arm build_linux clean test test-cov lint format docs

# ── 版本号（单一真相来源：src/scenefab/__init__.py）────────────────────
VERSION := $(shell python3 -c "import sys; sys.path.insert(0, 'src'); from scenefab import __version__; print(__version__)" 2>/dev/null)
ifeq ($(VERSION),)
  VERSION := 2.4.0
endif
PLATFORM := $(shell python3 -c "import sys; s='darwin' if sys.platform=='darwin' else 'win32' if sys.platform=='win32' else 'linux'; print(s)")

# ── 颜色输出 ───────────────────────────────────────────────────────
GREEN  := \033[0;32m
CYAN   := \033[0;36m
YELLOW := \033[1;33m
RED    := \033[0;31m
NC     := \033[0m

info    = @echo "$(GREEN)[INFO]$(NC)  $*"
step    = @echo "$(CYAN)[STEP]$(NC)  $*"
warn    = @echo "$(YELLOW)[WARN]$(NC)  $*"

# ── 默认目标：显示帮助 ─────────────────────────────────────────────
help:
	@echo "SceneFab Build System  v$(VERSION)"
	@echo ""
	@echo "使用方式: make <target>"
	@echo ""
	@echo "构建目标:"
	@echo "  build_win     构建 Windows x64 版本（.zip）"
	@echo "  build_mac     构建 macOS x64 版本（.dmg）"
	@echo "  build_mac_arm 构建 macOS ARM64 版本（.dmg）"
	@echo "  build_linux   构建 Linux x86_64 版本（.AppImage）"
	@echo ""
	@echo "开发目标:"
	@echo "  test          运行测试"
	@echo "  test-cov      运行测试并生成覆盖率报告"
	@echo "  lint          代码风格检查"
	@echo "  format        代码格式化"
	@echo "  clean         清理临时文件"
	@echo ""
	@echo "版本: $(VERSION)"

# ── 跨平台构建 ─────────────────────────────────────────────────────
build: build_$(PLATFORM)

build_win:
	$(step) Windows x64 构建（PyInstaller）...
	@if [ "$(shell uname)" = "Darwin" ]; then \
		echo "$(RED)[ERROR]$(NC) Windows 构建只能在 Windows/macOS/Linux 执行"; \
		exit 1; \
	fi
	@powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1 -Version $(VERSION)
	@echo "$(GREEN)✅ Windows 构建完成: dist/SceneFab-$(VERSION)-windows-x64.zip$(NC)"

build_mac:
	$(step) macOS x64 构建（PyInstaller）...
	@bash scripts/build_macos.sh x64
	@echo "$(GREEN)✅ macOS x64 构建完成: dist/SceneFab-$(VERSION)-macos-x64.dmg$(NC)"

build_mac_arm:
	$(step) macOS ARM64 构建（PyInstaller）...
	@bash scripts/build_macos.sh arm64
	@echo "$(GREEN)✅ macOS ARM64 构建完成: dist/SceneFab-$(VERSION)-macos-arm64.dmg$(NC)"

build_linux:
	$(step) Linux x86_64 构建（Nuitka + AppImage）...
	@bash scripts/build_linux.sh
	@echo "$(GREEN)✅ Linux 构建完成: SceneFab-$(VERSION)-linux-x86_64.AppImage$(NC)"

# ── 开发目标 ───────────────────────────────────────────────────────
# v2.5.0: Rust + Tauri + React 主线取代 Python v2.4
# (pytest/ruff/black/isort 已退役,保留为过渡参考)
test:
	@echo "$(YELLOW)→ pytest 已退役,使用 'make rust-test' 与 'pnpm test'$(NC)"
	cargo test --workspace
	(cd apps/desktop && pnpm test)

test-cov:
	@echo "$(YELLOW)→ pytest-cov 已退役,使用 'make coverage'（统一脚本）$(NC)"
	./scripts/coverage.sh

# Rust 单元 + 集成测试
rust-test:
	cargo test --workspace

# Rust + 集成测试,输出到控制台
rust-test-verbose:
	cargo test --workspace -- --nocapture

# 仅 clippy,不动 coverage
lint:
	cargo clippy --workspace --all-targets -- -D warnings
	cargo fmt --all -- --check
	(cd apps/desktop && pnpm lint)

# Rust 格式化（检查 + 应用）
format:
	cargo fmt --all
	(cd apps/desktop && pnpm format)

# 全量覆盖率测量：Rust tarpaulin + 前端 vitest
coverage:
	./scripts/coverage.sh

# 清理（扩展：增加 v2.5.0 产物）
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf build/ dist/ dist-nuitka/ *.egg-info/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage
	rm -rf apps/desktop/coverage/
	rm -rf apps/desktop/dist/
	rm -rf target/coverage/

docs:
	cd docs && npm run docs:build
