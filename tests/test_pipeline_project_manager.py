#!/usr/bin/env python3
"""测试 orchestration.ProjectManager 的 .scenefab 扩展名与向后兼容。"""

import tempfile
from pathlib import Path

from scenefab.services.orchestration.pipeline_project_manager import ProjectManager


class TestProjectExtension:
    def test_default_extension_is_scenefab(self):
        assert ProjectManager.PROJECT_EXTENSION == ".scenefab"
        # 旧拼写保留在加载列表中（向后兼容）
        assert ".scenefab" in ProjectManager.PROJECT_EXTENSIONS
        assert ".narrafilm" in ProjectManager.PROJECT_EXTENSIONS
        assert ".narrafiilm" in ProjectManager.PROJECT_EXTENSIONS

    def test_save_without_suffix_uses_scenefab(self):
        m = ProjectManager()
        project = m.create_project(name="t")
        with tempfile.TemporaryDirectory() as d:
            out = m.save(project, str(Path(d) / "proj"))
            assert out.endswith(".scenefab")
            assert Path(out).exists()

    def test_legacy_extension_preserved_and_loadable(self):
        m = ProjectManager()
        project = m.create_project(name="t")
        with tempfile.TemporaryDirectory() as d:
            # 显式旧扩展名：在受支持列表内，不被强改后缀
            out = m.save(project, str(Path(d) / "old.narrafilm"))
            assert out.endswith(".narrafilm")
            # 旧文件仍可加载
            assert m.load(out) is not None
