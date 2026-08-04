#!/usr/bin/env python3
"""bundle-docs.py — 将 VitePress 文档站点打包到安装包（v2.5.0 端到端优化 · 安装包文档化）。

职责
----
SceneFab 的 docs 站 (VitePress) 在 CI 中已经构建为静态站点
(docs/.vitepress/dist/)，但安装包 (.dmg/.exe/.AppImage) 默认只打包 Python
资源和二进制,用户离线时无法访问使用文档。

本脚本提供 3 个产物供安装包使用：
1. ``docs/.vitepress/dist`` — 完整 HTML 站点（已构建，离线可用）
2. ``docs/guide/*.md``     — Markdown 源文件（便于 Help 系统 / 帮助面板使用）
3. ``docs_bundle/``         — 上述 1+2 的整合（构建脚本统一从此处复制）

用法
----
    python3 scripts/bundle-docs.py                       # 完整打包到 docs_bundle/
    python3 scripts/bundle-docs.py --check               # 仅校验不写文件 (CI gate)
    python3 scripts/bundle-docs.py --dist-only           # 只生成 dist（不复制 markdown）
    python3 scripts/bundle-docs.py --md-only             # 只复制 markdown（不打包 dist）

设计原则
--------
- **不修改源文件**: VitePress dist 是构建产物,只读不写。
- **缺失时安全降级**: docs 未构建时 (VitePress dist 不存在),仍可生成 md-only 模式。
- **校验而非静默**: --check 模式下报告缺哪些文件,不直接退出。
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_SRC = ROOT / "docs"
DOCS_DIST = DOCS_SRC / ".vitepress" / "dist"
DOCS_GUIDE = DOCS_SRC / "guide"
BUNDLE_ROOT = ROOT / "docs_bundle"
BUNDLE_HTML = BUNDLE_ROOT / "html"
BUNDLE_MD = BUNDLE_ROOT / "markdown"

# 必备文件清单（用于完整性校验）
REQUIRED_MD_FILES: tuple[str, ...] = (
    "quick-start.md",
    "installation.md",
    "ai-configuration.md",
    "interface.md",
    "cli-reference.md",
    "python-api.md",
    "narration-spec.md",
    "ai-video-guide.md",
    "exporting.md",
    "troubleshooting.md",
)


def _safe_copytree(src: Path, dst: Path) -> int:
    """安全复制目录树，返回文件数。dst 已存在时先清空。"""
    if not src.exists():
        return 0
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return sum(1 for _ in dst.rglob("*") if _.is_file())


def _safe_copy_files(files: list[Path], dst: Path) -> int:
    """安全复制文件列表到目录 dst，返回成功数。"""
    dst.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in files:
        if not src.exists():
            continue
        shutil.copy(src, dst / src.name)
        copied += 1
    return copied


def bundle_html() -> int:
    """复制 docs/.vitepress/dist → docs_bundle/html/"""
    if not DOCS_DIST.exists():
        print(f"  [WARN] VitePress dist not found: {DOCS_DIST}")
        print("         run `cd docs && npm run build` first")
        return 0
    n = _safe_copytree(DOCS_DIST, BUNDLE_HTML)
    print(f"  [ok] bundled {n} files → {BUNDLE_HTML.relative_to(ROOT)}")
    return n


def bundle_markdown() -> int:
    """复制 docs/guide/*.md → docs_bundle/markdown/"""
    md_files = [DOCS_GUIDE / name for name in REQUIRED_MD_FILES]
    n = _safe_copy_files(md_files, BUNDLE_MD)
    if n < len(REQUIRED_MD_FILES):
        missing = [
            name
            for name in REQUIRED_MD_FILES
            if not (DOCS_GUIDE / name).exists()
        ]
        print(f"  [WARN] missing {len(missing)} markdown files: {missing}")
    print(
        f"  [ok] bundled {n}/{len(REQUIRED_MD_FILES)} markdown files → {BUNDLE_MD.relative_to(ROOT)}")
    return n


def verify_bundle() -> int:
    """校验 docs_bundle 内容（CI gate）。返回错误数。"""
    errors = 0

    # HTML 检查（允许缺失：用户可能未运行 vitepress build）
    if BUNDLE_HTML.exists():
        html_count = sum(1 for _ in BUNDLE_HTML.rglob("*.html"))
        if html_count < 5:
            print(
                f"  [FAIL] docs_bundle/html has only {html_count} html files")
            errors += 1
        else:
            print(f"  [ok] docs_bundle/html: {html_count} html files")
    else:
        print("  [WARN] docs_bundle/html missing (run `npm run build` in docs/)")

    # Markdown 检查（必须存在）
    if not BUNDLE_MD.exists():
        print("  [FAIL] docs_bundle/markdown missing")
        errors += 1
    else:
        md_count = len(list(BUNDLE_MD.glob("*.md")))
        if md_count < len(REQUIRED_MD_FILES):
            print(
                f"  [FAIL] docs_bundle/markdown has only {md_count}/"
                f"{len(REQUIRED_MD_FILES)} files"
            )
            errors += 1
        else:
            print(
                f"  [ok] docs_bundle/markdown: {md_count}/"
                f"{len(REQUIRED_MD_FILES)} files"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bundle SceneFab docs for packaging")
    parser.add_argument("--check", action="store_true",
                        help="verify only, no writes")
    parser.add_argument("--dist-only", action="store_true",
                        help="only bundle HTML dist")
    parser.add_argument("--md-only", action="store_true",
                        help="only bundle markdown")
    args = parser.parse_args()

    print("=== SceneFab Docs Bundler ===")
    print(f"ROOT: {ROOT}")
    print()

    if args.check:
        return verify_bundle()

    print("[1/2] Bundling VitePress dist (HTML site)...")
    bundle_html()
    print()

    if not args.dist_only:
        print("[2/2] Bundling markdown sources (guide/*.md)...")
        bundle_markdown()
        print()

    print("[verify] Checking bundle completeness...")
    errors = verify_bundle()
    if errors:
        print(f"\n[FAIL] {errors} errors found")
        return 1

    print(f"\n[OK] docs bundle ready at: {BUNDLE_ROOT.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
