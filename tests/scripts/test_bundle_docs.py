#!/usr/bin/env python3
"""bundle-docs.py 单元测试（v2.5.0 安装包文档化）。

覆盖：
- 必需 markdown 文件存在性
- docs_bundle/markdown/ 完整性
- --check 模式返回正确 exit code
- docs_bundle/html/ 校验（缺失时警告而非错误）
- 幂等性：连续运行不会引入重复文件
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
DOCS_DIR = ROOT / "docs"
DOCS_GUIDE = DOCS_DIR / "guide"
BUNDLE_DIR = ROOT / "docs_bundle"

REQUIRED_MD: tuple[str, ...] = (
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


class TestRequiredDocs:
    """确保必需的使用文档在源仓库中存在。"""

    @pytest.mark.parametrize("filename", REQUIRED_MD)
    def test_required_markdown_exists(self, filename: str) -> None:
        path = DOCS_GUIDE / filename
        assert path.exists(), f"missing required doc: {path}"
        assert path.stat().st_size > 0, f"empty doc: {path}"


class TestBundleScriptExists:
    """bundle-docs.py 脚本本身存在且可执行。"""

    def test_script_file_exists(self) -> None:
        path = SCRIPTS_DIR / "bundle-docs.py"
        assert path.exists()
        assert path.stat().st_size > 0

    def test_script_is_executable(self) -> None:
        path = SCRIPTS_DIR / "bundle-docs.py"
        mode = path.stat().st_mode
        # 任意用户可执行位 (owner or group or other)
        assert mode & 0o111, f"script not executable: {path}"

    def test_script_help_works(self) -> None:
        """--help 立即返回 (烟雾测试：解析参数无误)。"""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "bundle-docs.py"), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "Bundle" in result.stdout or "bundle" in result.stdout


@pytest.mark.skipif(
    not (ROOT / "docs" / ".vitepress" / "dist").exists(),
    reason="VitePress dist not built (run `cd docs && npm run build`)",
)
class TestBundleEndToEnd:
    """端到端：跑 bundle-docs.py → 校验产物。"""

    def test_full_bundle_creates_required_dirs(self, tmp_path: Path) -> None:
        """跑完整 bundle 流程后,docs_bundle/ 存在并有正确子目录。"""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "bundle-docs.py")],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=30,
        )
        assert result.returncode == 0, f"bundle failed: {result.stderr}"
        assert (BUNDLE_DIR / "markdown").exists()
        assert (BUNDLE_DIR / "html").exists()

    def test_markdown_subdir_has_all_files(self) -> None:
        md_dir = BUNDLE_DIR / "markdown"
        if not md_dir.exists():
            pytest.skip("markdown bundle not generated")
        bundled = {p.name for p in md_dir.glob("*.md")}
        missing = set(REQUIRED_MD) - bundled
        assert not missing, f"missing bundled md: {missing}"

    def test_check_mode_returns_zero(self) -> None:
        """CI gate 模式：bundle 已生成时返回 0。"""
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "bundle-docs.py"),
                "--check",
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=10,
        )
        assert result.returncode == 0, f"check failed: {result.stdout}\n{result.stderr}"

    def test_idempotent(self) -> None:
        """连续跑两次 → 文件数稳定,无重复。"""
        first = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "bundle-docs.py")],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=30,
        )
        assert first.returncode == 0

        md_dir = BUNDLE_DIR / "markdown"
        if not md_dir.exists():
            pytest.skip("markdown bundle not generated")
        first_count = len(list(md_dir.glob("*.md")))

        second = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "bundle-docs.py")],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=30,
        )
        assert second.returncode == 0
        second_count = len(list(md_dir.glob("*.md")))
        assert first_count == second_count, "bundle not idempotent"


class TestBuildScriptsReferenceBundle:
    """三个构建脚本都引用了 bundle-docs.py。"""

    @pytest.mark.parametrize(
        "script",
        ["build_macos.sh", "build_linux.sh", "build_windows.ps1"],
    )
    def test_build_script_calls_bundle(self, script: str) -> None:
        path = SCRIPTS_DIR / script
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "bundle-docs" in content, (
            f"{script} should reference bundle-docs.py"
        )

    @pytest.mark.parametrize(
        "script",
        ["build_macos.sh", "build_linux.sh", "build_windows.ps1"],
    )
    def test_build_script_includes_docs_bundle(self, script: str) -> None:
        """确认 add-data 引用 docs_bundle (PyInstaller) 或 cp 到 AppDir (Nuitka)。"""
        path = SCRIPTS_DIR / script
        content = path.read_text(encoding="utf-8")
        assert "docs_bundle" in content, (
            f"{script} should include docs_bundle in install package"
        )


class TestManifestIncludesDocs:
    """MANIFEST.in 包含 docs 源文件。"""

    def test_manifest_includes_guide(self) -> None:
        path = ROOT / "MANIFEST.in"
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "docs/guide" in content
        assert "*.md" in content

    def test_manifest_includes_vitepress_dist(self) -> None:
        path = ROOT / "MANIFEST.in"
        content = path.read_text(encoding="utf-8")
        assert "docs/.vitepress/dist" in content


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
