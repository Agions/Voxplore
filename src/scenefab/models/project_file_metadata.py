#!/usr/bin/env python3

"""
项目文件元数据（.scenefab 项目文件格式）

.. note::
    本模块定义 .scenefab 项目文件持久化时的元数据格式，与
    ``scenefab.models.project_models.ProjectMetadata``（项目运行时元数据）
    是两个不同概念：

    - ``ProjectMetadata``：项目运行时元数据（用于项目管理器）
    - ``ProjectFileMetadata``：项目文件元数据（用于 .scenefab 文件格式）

历史：原位于 ``scenefab.services.orchestration.pipeline_project_manager``，
因与 ``models.project_models.ProjectMetadata`` 命名冲突，于 Phase 1 重构中
提取为独立模型类。
"""

from dataclasses import dataclass
from enum import Enum

from .serialization import SerializableDataclass


class _ProjectFileVersion(Enum):
    """.scenefab 项目文件版本（内部使用）"""

    V1 = "1.0"
    V2 = "2.0"  # 当前版本，支持更多元数据


@dataclass
class ProjectFileMetadata(SerializableDataclass):
    """.scenefab 项目文件元数据

    用于 .scenefab 项目文件的持久化与交换。
    """

    id: str = ""  # 项目唯一ID
    name: str = "未命名项目"  # 项目名称
    version: str = "2.0"  # 项目格式版本
    project_type: str = "raw"  # 项目类型
    created_at: str = ""  # 创建时间
    modified_at: str = ""  # 修改时间
    author: str = ""  # 作者
    description: str = ""  # 项目描述

    # 软件信息
    app_version: str = "2.0.0"  # SceneFab 版本
    platform: str = "windows"  # 平台

    # 输出设置
    output_width: int = 1920
    output_height: int = 1080
    output_fps: float = 30.0
    output_format: str = "mp4"


__all__ = ["ProjectFileMetadata", "_ProjectFileVersion"]
