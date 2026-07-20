#!/usr/bin/env python3
"""测试项目模板管理器"""

import logging
import zipfile
from datetime import datetime
from pathlib import Path

from scenefab.models.project_models import ProjectMetadata, ProjectType
from scenefab.project_manager import Project
from scenefab.project_template_manager import (
    ProjectTemplateManager,
    TemplateCategory,
    TemplateInfo,
)
from scenefab.utils.json_io import read_json, write_json


def _template_info(template_id: str) -> TemplateInfo:
    now = datetime.now()
    return TemplateInfo(
        id=template_id,
        name="测试模板",
        description="模板描述",
        category="commentary",
        author="作者",
        version="1.0.0",
        created_at=now,
        updated_at=now,
        file_size=0,
        project_type=ProjectType.COMMENTARY,
    )


def _template_manager(tmp_path: Path) -> ProjectTemplateManager:
    manager = ProjectTemplateManager.__new__(ProjectTemplateManager)
    manager.config_manager = None
    manager.logger = logging.getLogger(__name__)
    manager.templates_dir = tmp_path / "templates"
    manager.builtin_templates_dir = tmp_path / "builtin_templates"
    manager.temp_dir = tmp_path / "temp"
    manager.templates_dir.mkdir(parents=True)
    manager.builtin_templates_dir.mkdir(parents=True)
    manager.temp_dir.mkdir(parents=True)
    manager.templates = {}
    manager.categories = {}
    return manager


def _project(tmp_path: Path) -> Project:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    write_json(
        project_dir / "project.json",
        {
            "metadata": {
                "name": "源项目",
                "description": "${hook}",
                "author": "作者",
                "project_type": ProjectType.COMMENTARY.value,
            },
            "timeline": {"tracks": []},
        },
    )
    (project_dir / "media").mkdir()
    (project_dir / "media" / "clip.txt").write_text("media", encoding="utf-8")
    metadata = ProjectMetadata(
        name="源项目",
        description="",
        author="作者",
        project_type=ProjectType.COMMENTARY,
    )
    return Project("project_1", str(project_dir), metadata)


class TestTemplateCategory:
    """测试模板类别"""

    def test_creation(self):
        """测试创建"""
        category = TemplateCategory(
            name="视频编辑",
            description="视频编辑模板",
            icon="video",
            color="#FF0000",
        )

        assert category.name == "视频编辑"
        assert category.icon == "video"
        assert category.color == "#FF0000"

    def test_default_values(self):
        """测试默认值"""
        category = TemplateCategory(
            name="测试",
            description="测试描述",
        )

        assert category.icon == "folder"
        assert category.color == "#2196F3"


class TestTemplateInfo:
    """测试模板信息"""

    def test_creation(self):
        """测试创建"""
        now = datetime.now()
        info = TemplateInfo(
            id="template_1",
            name="测试模板",
            description="这是一个测试模板",
            category="视频",
            author="作者",
            version="1.0.0",
            created_at=now,
            updated_at=now,
            file_size=1024,
        )

        assert info.id == "template_1"
        assert info.name == "测试模板"
        assert info.version == "1.0.0"

    def test_default_values(self):
        """测试默认值"""
        now = datetime.now()
        info = TemplateInfo(
            id="test",
            name="测试",
            description="描述",
            category="分类",
            author="作者",
            version="1.0",
            created_at=now,
            updated_at=now,
            file_size=100,
        )

        assert info.preview_image is None
        assert info.tags == []
        assert info.rating == 0.0
        assert info.download_count == 0

    def test_to_dict(self):
        """测试转换为字典"""
        now = datetime.now()
        info = TemplateInfo(
            id="test",
            name="测试",
            description="描述",
            category="分类",
            author="作者",
            version="1.0",
            created_at=now,
            updated_at=now,
            file_size=100,
        )

        d = info.to_dict()

        assert d["id"] == "test"
        assert d["name"] == "测试"


class TestProjectTemplateManagerIO:
    """测试模板管理器真实文件读写路径"""

    def test_template_path_resolves_builtin_and_user_roots(self, tmp_path: Path):
        manager = _template_manager(tmp_path)
        user_template = _template_info("user_template")
        builtin_template = _template_info("builtin_template")
        builtin_template.is_builtin = True

        assert (
            manager._template_path(user_template.id, user_template)
            == manager.templates_dir / user_template.id
        )
        assert (
            manager._template_path(builtin_template.id, builtin_template)
            == manager.builtin_templates_dir / builtin_template.id
        )

    def test_create_template_writes_index_and_metadata(self, tmp_path: Path):
        manager = _template_manager(tmp_path)
        project = _project(tmp_path)

        template_id = manager.create_template(
            project,
            "第一人称模板",
            "commentary",
            description="解说模板",
            tags=["短剧"],
        )

        assert template_id is not None
        template_dir = manager.templates_dir / template_id
        assert (template_dir / "project_template.json").exists()
        assert (template_dir / "template_metadata.json").exists()
        assert (template_dir / "media" / "clip.txt").exists()

        metadata = read_json(template_dir / "template_metadata.json")
        assert metadata["name"] == "第一人称模板"
        assert metadata["tags"] == ["短剧"]

        template_index = read_json(manager.templates_dir / "templates.json")
        assert template_id in template_index

    def test_apply_template_replaces_variables_and_creates_project(
        self, tmp_path: Path
    ):
        manager = _template_manager(tmp_path)
        template_id = "template_apply"
        template_dir = manager.templates_dir / template_id
        template_dir.mkdir()
        write_json(
            template_dir / "project_template.json",
            {
                "metadata": {
                    "name": "${project_name}",
                    "description": "${hook}",
                },
                "script": "${hook}",
            },
        )
        manager.templates[template_id] = _template_info(template_id)

        project_dir = tmp_path / "created_project"
        ok = manager.apply_template(
            template_id,
            "新项目",
            str(project_dir),
            {"project_name": "新项目", "hook": "三秒冲突"},
        )

        assert ok is True
        project_data = read_json(project_dir / "project.json")
        assert project_data["metadata"]["name"] == "新项目"
        assert project_data["metadata"]["description"] == "三秒冲突"
        assert project_data["script"] == "三秒冲突"
        assert (project_dir / "media").is_dir()
        assert manager.templates[template_id].download_count == 1

    def test_export_then_import_template_roundtrip(self, tmp_path: Path):
        manager = _template_manager(tmp_path)
        template_id = "template_export"
        template_dir = manager.templates_dir / template_id
        template_dir.mkdir()
        write_json(template_dir / "project_template.json", {"metadata": {}})
        manager.templates[template_id] = _template_info(template_id)

        export_path = tmp_path / "template.zip"
        assert manager.export_template(template_id, str(export_path)) is True

        imported_manager = _template_manager(tmp_path / "imported")
        imported_id = imported_manager.import_template(str(export_path))

        assert imported_id is not None
        assert imported_id in imported_manager.templates
        imported_template = imported_manager.templates[imported_id]
        assert imported_template.name == "测试模板"
        assert imported_template.is_builtin is False
        assert (
            imported_manager.templates_dir / imported_id / "project_template.json"
        ).exists()

    def test_import_template_rejects_archive_without_export_info(self, tmp_path: Path):
        manager = _template_manager(tmp_path)
        archive_path = tmp_path / "broken_template.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("project_template.json", "{}")

        assert manager.import_template(str(archive_path)) is None
        assert manager.templates == {}

    def test_delete_builtin_template_is_rejected(self, tmp_path: Path):
        manager = _template_manager(tmp_path)
        template_id = "builtin_template"
        template_info = _template_info(template_id)
        template_info.is_builtin = True
        manager.templates[template_id] = template_info

        assert manager.delete_template(template_id) is False
        assert template_id in manager.templates

    def test_validate_template_reports_missing_project_file(self, tmp_path: Path):
        manager = _template_manager(tmp_path)
        template_id = "template_missing_project"
        (manager.templates_dir / template_id).mkdir()
        manager.templates[template_id] = _template_info(template_id)

        result = manager.validate_template(template_id)

        assert result["valid"] is False
        assert "缺少必需文件: project_template.json" in result["errors"]

    def test_update_template_writes_metadata_and_index(self, tmp_path: Path):
        manager = _template_manager(tmp_path)
        template_id = "template_update"
        (manager.templates_dir / template_id).mkdir()
        manager.templates[template_id] = _template_info(template_id)

        ok = manager.update_template(
            template_id,
            {"name": "更新后的模板", "description": "更新描述"},
        )

        assert ok is True
        assert manager.templates[template_id].name == "更新后的模板"
        metadata = read_json(manager.templates_dir / template_id / "template_info.json")
        assert metadata["description"] == "更新描述"
        template_index = read_json(manager.templates_dir / "templates.json")
        assert template_index[template_id]["name"] == "更新后的模板"

    def test_rate_template_clamps_rating(self, tmp_path: Path):
        manager = _template_manager(tmp_path)
        template_id = "template_rate"
        manager.templates[template_id] = _template_info(template_id)

        assert manager.rate_template(template_id, 8.0) is True
        assert manager.templates[template_id].rating == 5.0

        assert manager.rate_template(template_id, -1.0) is True
        assert manager.templates[template_id].rating == 0.0

    def test_template_statistics_groups_templates(self, tmp_path: Path):
        manager = _template_manager(tmp_path)
        user_template = _template_info("user_template")
        user_template.rating = 4.0
        builtin_template = _template_info("builtin_template")
        builtin_template.is_builtin = True
        builtin_template.category = "education"
        manager.templates = {
            user_template.id: user_template,
            builtin_template.id: builtin_template,
        }
        manager._init_categories()

        stats = manager.get_template_statistics()

        assert stats["total_templates"] == 2
        assert stats["builtin_templates"] == 1
        assert stats["user_templates"] == 1
        assert stats["category_stats"]["commentary"] == 1
        assert stats["category_stats"]["education"] == 1
        assert stats["average_rating"] == 4.0

    def test_load_templates_reads_user_index(self, tmp_path: Path):
        manager = _template_manager(tmp_path)
        template_info = _template_info("indexed_template")
        write_json(
            manager.templates_dir / "templates.json",
            {template_info.id: template_info.to_dict()},
        )

        manager._load_templates()

        assert "indexed_template" in manager.templates
        assert manager.templates["indexed_template"].name == "测试模板"

    def test_load_builtin_templates_does_not_override_user_template(
        self, tmp_path: Path
    ):
        manager = _template_manager(tmp_path)
        template_id = "shared_template"
        user_template = _template_info(template_id)
        user_template.name = "用户模板"
        builtin_template = _template_info(template_id)
        builtin_template.name = "内置模板"
        manager.templates[template_id] = user_template

        builtin_dir = manager.builtin_templates_dir / template_id
        builtin_dir.mkdir()
        write_json(builtin_dir / "template_info.json", builtin_template.to_dict())

        manager._load_builtin_templates()

        assert manager.templates[template_id].name == "用户模板"
        assert manager.templates[template_id].is_builtin is False

    def test_search_templates_filters_by_category_and_type(self, tmp_path: Path):
        manager = _template_manager(tmp_path)
        commentary_template = _template_info("commentary_template")
        commentary_template.name = "第一人称解说"
        education_template = _template_info("education_template")
        education_template.name = "课程讲解"
        education_template.category = "education"
        education_template.project_type = ProjectType.MULTIMEDIA
        manager.templates = {
            commentary_template.id: commentary_template,
            education_template.id: education_template,
        }

        results = manager.search_templates(
            "讲解",
            category="education",
            project_type=ProjectType.MULTIMEDIA,
        )

        assert [item.id for item in results] == ["education_template"]

    def test_load_templates_ignores_corrupt_user_index(self, tmp_path: Path):
        manager = _template_manager(tmp_path)
        (manager.templates_dir / "templates.json").write_text(
            "{broken", encoding="utf-8"
        )

        manager._load_templates()

        assert manager.templates == {}

    def test_load_builtin_templates_ignores_corrupt_template_info(self, tmp_path: Path):
        manager = _template_manager(tmp_path)
        broken_dir = manager.builtin_templates_dir / "broken_builtin"
        broken_dir.mkdir()
        (broken_dir / "template_info.json").write_text("{broken", encoding="utf-8")

        manager._load_builtin_templates()

        assert manager.templates == {}
