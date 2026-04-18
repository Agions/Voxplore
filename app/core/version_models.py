#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目版本管理数据模型

定义版本控制相关的数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ProjectVersion:
    """项目版本信息"""
    version_id: str
    timestamp: datetime
    description: str
    changes: List[str]
    file_hash: str
    size: int
    tags: List[str] = field(default_factory=list)
    is_auto_backup: bool = False
    is_major: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'version_id': self.version_id,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'changes': self.changes,
            'file_hash': self.file_hash,
            'size': self.size,
            'tags': self.tags,
            'is_auto_backup': self.is_auto_backup,
            'is_major': self.is_major
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectVersion':
        return cls(
            version_id=data['version_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            description=data['description'],
            changes=data['changes'],
            file_hash=data['file_hash'],
            size=data['size'],
            tags=data.get('tags', []),
            is_auto_backup=data.get('is_auto_backup', False),
            is_major=data.get('is_major', False)
        )


@dataclass
class ProjectBranch:
    """项目分支信息"""
    name: str
    created_at: datetime
    description: str
    parent_branch: Optional[str] = None
    is_active: bool = True
    versions: List[str] = field(default_factory=list)  # version_id列表

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'description': self.description,
            'parent_branch': self.parent_branch,
            'is_active': self.is_active,
            'versions': self.versions
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectBranch':
        return cls(
            name=data['name'],
            created_at=datetime.fromisoformat(data['created_at']),
            description=data['description'],
            parent_branch=data.get('parent_branch'),
            is_active=data.get('is_active', True),
            versions=data.get('versions', [])
        )


__all__ = [
    "ProjectVersion",
    "ProjectBranch",
]
