#!/usr/bin/env python3

"""
项目模板数据模型

定义项目模板相关的枚举和数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .project_manager import ProjectType


@dataclass
class TemplateCategory:
    """模板类别"""
    name: str
    description: str
    icon: str = "folder"
    color: str = "#2196F3"


@dataclass
class TemplateInfo:
    """模板信息"""
    id: str
    name: str
    description: str
    category: str
    author: str
    version: str
    created_at: datetime
    updated_at: datetime
    file_size: int
    preview_image: str | None = None
    tags: list[str] = field(default_factory=list)
    rating: float = 0.0
    download_count: int = 0
    is_builtin: bool = False
    project_type: ProjectType = ProjectType.VIDEO_EDITING
    requirements: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'author': self.author,
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'file_size': self.file_size,
            'preview_image': self.preview_image,
            'tags': self.tags,
            'rating': self.rating,
            'download_count': self.download_count,
            'is_builtin': self.is_builtin,
            'project_type': self.project_type.value,
            'requirements': self.requirements
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TemplateInfo':
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            category=data['category'],
            author=data['author'],
            version=data['version'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            file_size=data['file_size'],
            preview_image=data.get('preview_image'),
            tags=data.get('tags', []),
            rating=data.get('rating', 0.0),
            download_count=data.get('download_count', 0),
            is_builtin=data.get('is_builtin', False),
            project_type=ProjectType(data.get('project_type', 'video_editing')),
            requirements=data.get('requirements', {})
        )


@dataclass
class TemplateMetadata:
    """模板元数据"""
    name: str
    description: str
    author: str
    version: str
    category: str
    tags: list[str] = field(default_factory=list)
    requirements: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)  # 模板变量


__all__ = [
    "TemplateCategory",
    "TemplateInfo",
    "TemplateMetadata",
]
