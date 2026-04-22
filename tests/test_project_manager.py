#!/usr/bin/env python3
"""测试项目管理器"""

from app.core.project_manager import (
    ProjectStatus,
    ProjectType,
    ProjectMetadata,
)


class TestProjectStatus:
    """测试项目状态枚举"""

    def test_active(self):
        assert ProjectStatus.ACTIVE.value == "active"

    def test_archived(self):
        assert ProjectStatus.ARCHIVED.value == "archived"

    def test_template(self):
        assert ProjectStatus.TEMPLATE.value == "template"

    def test_corrupted(self):
        assert ProjectStatus.CORRUPTED.value == "corrupted"


class TestProjectType:
    """测试项目类型枚举"""

    def test_video_editing(self):
        assert ProjectType.VIDEO_EDITING.value == "video_editing"

    def test_ai_enhancement(self):
        assert ProjectType.AI_ENHANCEMENT.value == "ai_enhancement"

    def test_compilation(self):
        assert ProjectType.COMPILATION.value == "compilation"

    def test_commentary(self):
        assert ProjectType.COMMENTARY.value == "commentary"

    def test_multimedia(self):
        assert ProjectType.MULTIMEDIA.value == "multimedia"


class TestProjectMetadata:
    """测试项目元数据"""

    def test_creation(self):
        metadata = ProjectMetadata(
            name="测试项目",
            description="这是一个测试项目"
        )
        
        assert metadata.name == "测试项目"
        assert metadata.description == "这是一个测试项目"

    def test_default_values(self):
        metadata = ProjectMetadata(name="测试")
        
        assert metadata.created_at is not None
        assert metadata.modified_at is not None
        assert metadata.version == "1.0.0"
        assert metadata.tags == []
        assert metadata.status == ProjectStatus.ACTIVE

    def test_to_dict(self):
        metadata = ProjectMetadata(
            name="测试",
            description="描述",
            author="作者"
        )
        
        d = metadata.to_dict()
        
        assert d["name"] == "测试"
        assert d["description"] == "描述"
        assert d["author"] == "作者"
