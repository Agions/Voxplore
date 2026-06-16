#!/usr/bin/env python3
"""Project version manager tests."""

from datetime import datetime
from pathlib import Path

from scenefab.version_manager import ProjectVersionManager
from scenefab.version_models import ProjectVersion


class TestProjectVersion:
    """测试项目版本数据类"""

    def test_creation(self):
        """测试创建"""
        version = ProjectVersion(
            version_id="v1.0.0",
            timestamp=datetime.now(),
            description="初始版本",
            changes=["创建项目"],
            file_hash="abc123",
            size=1024,
        )

        assert version.version_id == "v1.0.0"
        assert version.description == "初始版本"
        assert version.size == 1024

    def test_to_dict(self):
        """测试转换为字典"""
        version = ProjectVersion(
            version_id="v1.0.0",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            description="测试",
            changes=[],
            file_hash="hash",
            size=100,
        )

        d = version.to_dict()

        assert d["version_id"] == "v1.0.0"
        assert d["description"] == "测试"

    def test_from_dict(self):
        """测试从字典恢复"""
        version = ProjectVersion.from_dict(
            {
                "version_id": "v1.0.1",
                "timestamp": "2024-01-01T12:00:00",
                "description": "恢复测试",
                "changes": ["更新脚本"],
                "file_hash": "hash",
                "size": 256,
                "tags": ["release"],
                "is_auto_backup": False,
                "is_major": True,
            }
        )

        assert version.version_id == "v1.0.1"
        assert version.timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert version.tags == ["release"]
        assert version.is_major is True


class TestProjectVersionManager:
    """测试项目版本管理器"""

    def test_initializes_version_dir_and_main_branch(self, tmp_path: Path):
        manager = ProjectVersionManager(str(tmp_path))

        assert (tmp_path / "versions").is_dir()
        assert manager.current_branch == "main"
        assert manager.get_current_branch() is not None
        assert manager.get_current_branch().name == "main"

    def test_create_version_copies_project_file(self, tmp_path: Path):
        project_file = tmp_path / "project.json"
        project_file.write_text('{"name": "demo"}', encoding="utf-8")
        manager = ProjectVersionManager(str(tmp_path))

        version_id = manager.create_version(
            description="初始版本",
            changes=["创建项目"],
            tags=["draft"],
            is_major=True,
        )

        assert version_id is not None
        version = manager.get_version(version_id)
        assert version is not None
        assert version.description == "初始版本"
        assert version.tags == ["draft"]
        assert version.is_major is True
        assert version.file_hash
        assert version_id in manager.branches["main"].versions
        assert (
            tmp_path / "versions" / version_id / "project.json"
        ).read_text(encoding="utf-8") == '{"name": "demo"}'
