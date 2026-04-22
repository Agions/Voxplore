#!/usr/bin/env python3
"""测试项目模板管理器"""

from datetime import datetime

from app.core.project_template_manager import (
    TemplateCategory,
    TemplateInfo,
)


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
