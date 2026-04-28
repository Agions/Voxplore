#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 项目文件管理

支持 .narrafiilm 项目文件的保存、加载和管理。

项目文件格式：
- JSON 格式，易于阅读和调试
- 包含所有项目配置和元数据
- 支持版本兼容性和向后兼容

使用示例:
    from app.services.orchestration import ProjectManager, ProjectType

    manager = ProjectManager()

    # 保存项目
    manager.save(project, "my_video.narrafiilm")

    # 加载项目
    project = manager.load("my_video.narrafiilm")
"""

import json
import zipfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
import uuid

# 获取 logger
logger = logging.getLogger(__name__)

# ============ 常量 ============
HASH_CHUNK_SIZE = 1024 * 1024  # 文件哈希计算 chunk 大小: 1MB


class ProjectType(Enum):
    """项目类型"""
    COMMENTARY = "commentary"         # AI 解说
    MASHUP = "mashup"               # 视频混剪
    BEAT_SYNC = "beat_sync"         # Beat-sync 混剪
    MONOLOGUE = "monologue"          # 第一人称独白
    RAW = "raw"                      # 原始项目


class ProjectVersion(Enum):
    """项目版本"""
    V1 = "1.0"
    V2 = "2.0"  # 当前版本，支持更多元数据


@dataclass
class ProjectMetadata:
    """项目元数据"""
    id: str = ""                    # 项目唯一ID
    name: str = "未命名项目"         # 项目名称
    version: str = "2.0"            # 项目格式版本
    project_type: str = "raw"       # 项目类型
    created_at: str = ""            # 创建时间
    modified_at: str = ""           # 修改时间
    author: str = ""                # 作者
    description: str = ""           # 项目描述

    # 软件信息
    app_version: str = "2.0.0"      # Voxplore 版本
    platform: str = "windows"      # 平台

    # 输出设置
    output_width: int = 1920
    output_height: int = 1080
    output_fps: float = 30.0
    output_format: str = "mp4"


@dataclass
class ProjectSource:
    """项目素材"""
    path: str = ""                  # 素材路径
    type: str = "video"            # video/audio/image
    name: str = ""                  # 显示名称
    duration: float = 0.0           # 时长（秒）
    size: int = 0                   # 文件大小
    hash: str = ""                  # 文件哈希（用于验证）


@dataclass
class ProjectConfig:
    """项目配置"""
    # AI 配置
    llm_provider: str = "openai"    # LLM 提供商
    llm_model: str = "gpt-4o-mini" # LLM 模型
    voice_provider: str = "edge"    # 配音提供商
    voice_id: str = ""             # 声音ID

    # 视频配置
    style: str = "default"         # 风格
    target_duration: float = 0.0   # 目标时长
    target_platform: str = "bilibili"  # 目标平台

    # 字幕配置
    subtitle_style: str = "viral"   # 字幕风格
    subtitle_enabled: bool = True

    # 导出配置
    export_format: str = "mp4"
    export_quality: str = "high"
    export_jianying: bool = True   # 是否导出剪映草稿


@dataclass
class VoxploreProject:
    """
    Voxplore 项目

    完整的项目数据结构
    """
    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)
    sources: List[ProjectSource] = field(default_factory=list)
    config: ProjectConfig = field(default_factory=ProjectConfig)

    # 项目特定数据（JSON 格式存储）
    project_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # 生成唯一ID
        if not self.metadata.id:
            self.metadata.id = str(uuid.uuid4())

        # 设置时间戳
        now = datetime.now().isoformat()
        if not self.metadata.created_at:
            self.metadata.created_at = now
        self.metadata.modified_at = now


class ProjectManager:
    """
    项目管理器

    负责项目的创建、保存、加载和版本兼容
    """

    # 支持的文件扩展名
    PROJECT_EXTENSIONS = [".narrafiilm", ".vfproj"]

    def __init__(self):
        self.current_project: Optional[VoxploreProject] = None
        self._last_save_path: Optional[Path] = None

    def create_project(
        self,
        name: str = "未命名项目",
        project_type: ProjectType = ProjectType.RAW,
    ) -> VoxploreProject:
        """
        创建新项目

        Args:
            name: 项目名称
            project_type: 项目类型

        Returns:
            新项目对象
        """
        project = VoxploreProject(
            metadata=ProjectMetadata(
                name=name,
                project_type=project_type.value,
            )
        )
        self.current_project = project
        return project

    def save(
        self,
        project: VoxploreProject,
        output_path: str,
        include_sources: bool = True,
        compress: bool = True,
    ) -> str:
        """
        保存项目到文件

        Args:
            project: 项目对象
            output_path: 输出路径
            include_sources: 是否包含素材信息
            compress: 是否压缩

        Returns:
            保存的文件路径
        """
        output_path = Path(output_path)

        # 确保扩展名正确
        if output_path.suffix.lower() not in self.PROJECT_EXTENSIONS:
            output_path = output_path.with_suffix(".narrafiilm")

        # 更新修改时间
        project.metadata.modified_at = datetime.now().isoformat()

        # 转换为字典
        project_dict = self._project_to_dict(project)

        if compress:
            # 使用 zip 压缩
            return self._save_compressed(project_dict, output_path, include_sources)
        else:
            # 直接保存 JSON
            return self._save_json(project_dict, output_path)

    def load(self, project_path: str) -> VoxploreProject:
        """
        从文件加载项目

        Args:
            project_path: 项目文件路径

        Returns:
            项目对象
        """
        project_path = Path(project_path)

        if not project_path.exists():
            raise FileNotFoundError(f"项目文件不存在: {project_path}")

        # 根据扩展名选择加载方式
        if project_path.suffix.lower() == ".zip" or self._is_compressed(project_path):
            project_dict = self._load_compressed(project_path)
        else:
            project_dict = self._load_json(project_path)

        # 解析项目
        project = self._dict_to_project(project_dict)
        self.current_project = project
        self._last_save_path = project_path

        return project

    def _project_to_dict(self, project: VoxploreProject) -> Dict:
        """将项目转换为字典"""
        return {
            "metadata": asdict(project.metadata),
            "sources": [asdict(s) for s in project.sources],
            "config": asdict(project.config),
            "project_data": project.project_data,
        }

    def _dict_to_project(self, data: Dict) -> VoxploreProject:
        """将字典转换为项目"""
        metadata = ProjectMetadata(**data.get("metadata", {}))
        sources = [ProjectSource(**s) for s in data.get("sources", [])]
        config = ProjectConfig(**data.get("config", {}))

        project = VoxploreProject(
            metadata=metadata,
            sources=sources,
            config=config,
            project_data=data.get("project_data", {}),
        )

        return project

    def _save_json(self, data: Dict, output_path: Path) -> str:
        """保存为 JSON 文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._last_save_path = output_path
        return str(output_path)

    def _load_json(self, project_path: Path) -> Dict:
        """从 JSON 文件加载"""
        with open(project_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 版本兼容性处理
        data = self._migrate_if_needed(data)

        return data

    def _save_compressed(
        self,
        data: Dict,
        output_path: Path,
        include_sources: bool
    ) -> str:
        """保存为压缩的 zip 文件"""
        # 创建 zip
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 保存主项目文件
            project_json = json.dumps(data, ensure_ascii=False, indent=2)
            zf.writestr("project.json", project_json)

            # 保存项目缩略图（如果有）
            # zf.writestr("thumbnail.jpg", thumbnail_data)

        self._last_save_path = output_path
        return str(output_path)

    def _load_compressed(self, project_path: Path) -> Dict:
        """从压缩文件加载"""
        with zipfile.ZipFile(project_path, 'r') as zf:
            # 读取主项目文件
            with zf.open("project.json") as f:
                data = json.load(f)

        # 版本兼容性处理
        data = self._migrate_if_needed(data)

        return data

    def _is_compressed(self, path: Path) -> bool:
        """检查是否是压缩文件"""
        try:
            return zipfile.is_zipfile(path)
        except Exception:
            return False

    def _migrate_if_needed(self, data: Dict) -> Dict:
        """项目版本迁移"""
        version = data.get("metadata", {}).get("version", "1.0")

        if version == "1.0":
            # 从 1.0 迁移到 2.0
            data = self._migrate_v1_to_v2(data)

        return data

    def _migrate_v1_to_v2(self, data: Dict) -> Dict:
        """从 1.0 迁移到 2.0"""
        # 添加新的元数据字段
        metadata = data.get("metadata", {})
        metadata["version"] = "2.0"

        # 添加新的配置字段（使用默认值）
        config = data.get("config", {})
        new_fields = {
            "subtitle_style": "viral",
            "subtitle_enabled": True,
            "export_format": "mp4",
            "export_quality": "high",
            "export_jianying": True,
        }
        for key, value in new_fields.items():
            if key not in config:
                config[key] = value

        data["metadata"] = metadata
        data["config"] = config

        return data

    def add_source(
        self,
        project: VoxploreProject,
        path: str,
        source_type: str = "video",
    ) -> ProjectSource:
        """
        添加素材到项目

        Args:
            project: 项目
            path: 素材路径
            source_type: 素材类型

        Returns:
            添加的素材对象
        """
        source = ProjectSource(
            path=path,
            type=source_type,
            name=Path(path).name,
        )

        # 获取文件信息
        p = Path(path)
        if p.exists():
            source.size = p.stat().st_size
            source.hash = self._calculate_simple_hash(p)

        project.sources.append(source)
        return source

    def _calculate_simple_hash(self, path: Path) -> str:
        """计算文件的简单哈希（用于验证）"""
        import hashlib
        try:
            with open(path, 'rb') as f:
                # 只读取前 1MB 用于哈希计算
                chunk = f.read(HASH_CHUNK_SIZE)
                return hashlib.md5(chunk).hexdigest()
        except Exception:
            return ""

    def get_recent_projects(self, count: int = 10) -> List[Dict]:
        """
        获取最近的项目列表

        Args:
            count: 返回数量

        Returns:
            项目列表（基本信息）
        """
        # 这是一个占位实现，实际可以从配置文件中读取
        return []

    def export_to_template(
        self,
        project: VoxploreProject,
        output_path: str,
    ) -> str:
        """
        导出为模板

        模板不包含素材路径，只包含配置

        Args:
            project: 项目
            output_path: 输出路径

        Returns:
            模板文件路径
        """
        # 创建模板项目（复制配置，清除敏感信息）
        template = VoxploreProject(
            metadata=ProjectMetadata(
                name=f"{project.metadata.name} (模板)",
                project_type=project.metadata.project_type,
                description=f"从 {project.metadata.name} 导出的模板",
            ),
            config=project.config,
        )

        # 保存模板
        return self.save(template, output_path, include_sources=False)

    def import_from_template(
        self,
        template_path: str,
        new_name: str,
    ) -> VoxploreProject:
        """
        从模板创建项目

        Args:
            template_path: 模板路径
            new_name: 新项目名称

        Returns:
            新项目
        """
        # 加载模板
        template_data = self.load(template_path)

        # 创建新项目
        project = self.create_project(
            name=new_name,
            project_type=ProjectType(template_data.metadata.project_type),
        )

        # 复制配置
        project.config = template_data.config

        return project


def save_project(
    project: VoxploreProject,
    output_path: str,
) -> str:
    """
    便捷的项目保存函数

    Args:
        project: 项目对象
        output_path: 输出路径

    Returns:
        保存的文件路径
    """
    manager = ProjectManager()
    return manager.save(project, output_path)


def load_project(project_path: str) -> VoxploreProject:
    """
    便捷的项目加载函数

    Args:
        project_path: 项目文件路径

    Returns:
        项目对象
    """
    manager = ProjectManager()
    return manager.load(project_path)


# ========== 使用示例 ==========

def demo_project_management():
    """演示项目管理"""
    logger.info("=" * 50)
    logger.info("Voxplore 项目管理演示")
    logger.info("=" * 50)

    manager = ProjectManager()

    # 创建项目
    project = manager.create_project(
        name="我的第一个视频",
        project_type=ProjectType.COMMENTARY,
    )

    # 添加素材
    manager.add_source(project, "/path/to/video.mp4", "video")
    manager.add_source(project, "/path/to/bgm.mp3", "audio")

    # 配置项目
    project.config.llm_provider = "deepseek"
    project.config.llm_model = "deepseek-chat"
    project.config.voice_provider = "edge"
    project.config.target_duration = 120.0
    project.config.target_platform = "bilibili"

    # 保存项目
    save_path = manager.save(project, "./demo_project.narrafiilm")
    logger.info(f"项目已保存: {save_path}")

    # 加载项目
    loaded = manager.load(save_path)
    logger.info(f"项目已加载: {loaded.metadata.name}")
    logger.info(f"素材数量: {len(loaded.sources)}")
    logger.info(f"目标平台: {loaded.config.target_platform}")


if __name__ == '__main__':
    demo_project_management()
