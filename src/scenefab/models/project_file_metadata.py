#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目文件元数据（narrafiilm 文件格式）

.. note::
    本模块定义 .narrafiilm 项目文件持久化时的元数据格式，与
    ``scenefab.models.project_models.ProjectMetadata``（项目运行时元数据）
    是两个不同概念：

    - ``ProjectMetadata``：项目运行时元数据（用于项目管理器）
    - ``ProjectFileMetadata``：项目文件元数据（用于 .narrafiilm 文件格式）

历史：原位于 ``scenefab.services.orchestration.pipeline_project_manager``，
因与 ``models.project_models.ProjectMetadata`` 命名冲突，于 Phase 1 重构中
提取为独立模型类。
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict


class _NarrafiilmVersion(Enum):
    """narrafiilm 项目文件版本（内部使用）"""
    V1 = "1.0"
    V2 = "2.0"  # 当前版本，支持更多元数据


@dataclass
class ProjectFileMetadata:
    """narrafiilm 项目文件元数据

    用于 .narrafiilm 项目文件的持久化与交换。
    """
    id: str = ""                    # 项目唯一ID
    name: str = "未命名项目"         # 项目名称
    version: str = "2.0"            # 项目格式版本
    project_type: str = "raw"       # 项目类型
    created_at: str = ""            # 创建时间
    modified_at: str = ""           # 修改时间
    author: str = ""                # 作者
    description: str = ""           # 项目描述

    # 软件信息
    app_version: str = "2.0.0"      # SceneFab 版本
    platform: str = "windows"      # 平台

    # 输出设置
    output_width: int = 1920
    output_height: int = 1080
    output_fps: float = 30.0
    output_format: str = "mp4"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectFileMetadata":
        # 忽略未知字段，保持前向兼容
        valid_fields = set(cls.__dataclass_fields__.keys())
        return cls(**{k: v for k, v in data.items() if k in valid_fields})


__all__ = ["ProjectFileMetadata", "_NarrafiilmVersion"]
