# SceneFab v2.5.0 Makefile
# Rust + Tauri 2 + React 主线构建系统
#
# 使用方法:
#   make help          显示帮助
#   make test          运行测试(Rust + 前端)
#   make coverage      全量覆盖率测量
#   make lint          cargo clippy + cargo fmt --check + pnpm lint
#   make format        cargo fmt + pnpm format
#   make build         本机架构的 release 构建
#   make build-tauri  调用 pnpm tauri build(三平台产物由 CI 完成)
#   make clean         清理临时文件

.SUFFIXES:
.PHONY: help build build-tauri clean test test-cov rust-test rust-test-verbose lint format coverage docs

# ── 版本号（单一真相来源：apps/desktop/package.json）──────────────────
VERSION := $(shell node -p "require('./apps/desktop/package.json').version" 2>/dev/null)
ifeq ($(VERSION),)
  VERSION := 2.5.0
endif

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
	@echo "SceneFab v$(VERSION) Build System  ·  Rust + Tauri 2 + React"
	@echo ""
	@echo "使用方式: make <target>"
	@echo ""
	@echo "构建目标:"
	@echo "  build         本机 release 构建（cargo build --release + pnpm build）"
	@echo "  build-tauri   pnpm tauri build（生成桌面安装包，由 CI 完成三平台）"
	@echo ""
	@echo "开发目标:"
	@echo "  test            运行测试（Rust workspace + 前端 vitest）"
	@echo "  rust-test       仅 Rust 单元 + 集成测试"
	@echo "  rust-test-verbose  Rust 测试 + 控制台输出"
	@echo "  test-cov        同 coverage（兼容旧名）"
	@echo "  coverage        全量覆盖率测量（Rust tarpaulin + 前端 vitest）"
	@echo "  lint            cargo clippy + cargo fmt --check + pnpm lint"
	@echo "  format          cargo fmt --all + pnpm format"
	@echo "  docs            构建 VitePress 文档站"
	@echo "  clean           清理临时文件"
	@echo ""
	@echo "版本: $(VERSION)"

# ── 构建 ───────────────────────────────────────────────────────
build:
	$(step) Rust workspace release 构建...
	cargo build --workspace --release
	$(step) 前端 production 构建...
	(cd apps/desktop && pnpm build)

# 桌面安装包(本机架构)
# CI 在 tag 触发时跑三平台矩阵,本地此目标仅生成当前平台产物
build-tauri:
	$(step) Tauri 桌面安装包构建...
	(cd apps/desktop && pnpm tauri build)

# ── 测试 ───────────────────────────────────────────────────────
test:
	$(step) Rust 单元 + 集成测试...
	cargo test --workspace
	$(step) 前端 Vitest 单元测试...
	(cd apps/desktop && pnpm test)

test-cov: coverage

rust-test:
	cargo test --workspace

rust-test-verbose:
	cargo test --workspace -- --nocapture

# ── Lint / Format / Coverage ───────────────────────────────────
lint:
	$(step) cargo clippy --workspace --all-targets...
	cargo clippy --workspace --all-targets -- -D warnings
	$(step) cargo fmt --all -- --check...
	cargo fmt --all -- --check
	$(step) pnpm lint...
	(cd apps/desktop && pnpm lint)

format:
	$(step) cargo fmt --all...
	cargo fmt --all
	$(step) pnpm format...
	(cd apps/desktop && pnpm format)

coverage:
	./scripts/coverage.sh

# ── 文档 ────────────────────────────────────────────────────────────
docs:
	cd docs && npm run docs:build

# ── 清理 ────────────────────────────────────────────────────────────
clean:
	rm -rf target/coverage/
	rm -rf apps/desktop/coverage/
	rm -rf apps/desktop/dist/
	rm -rf apps/desktop/.tanstack/tmp/
	rm -rf docs/.vitepress/dist/
	rm -rf docs/.vitepress/cache/
	rm -rf docs/.vitepress/.temp/
	rm -rf node_modules/
	rm -rf apps/desktop/node_modules/
	rm -rf docs/node_modules/
