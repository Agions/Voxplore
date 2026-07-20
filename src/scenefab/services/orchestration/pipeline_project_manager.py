#!/usr/bin/env python3

"""
SceneFab 项目文件管理

支持 .scenefab 项目文件的保存、加载和管理（兼容旧 .narrafilm/.narrafiilm）。

项目文件格式：
- JSON 格式，易于阅读和调试
- 包含所有项目配置和元数据
- 支持版本兼容性和向后兼容

使用示例:
    from scenefab.services.orchestration import ProjectManager

    manager = ProjectManager()

    # 保存项目
    manager.save(project, "my_video.scenefab")

    # 加载项目
    project = manager.load("my_video.scenefab")
"""

import json
import logging
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from scenefab.models.project_file_metadata import (
    ProjectFileMetadata,
    _ProjectFileVersion,  # noqa: F401  # re-exported via services.orchestration.__init__
)
from scenefab.models.project_models import ProjectType
from scenefab.services.ai.model_catalog import DEFAULT_MODELS
from scenefab.services.export.export_utils import write_json_file

# 获取 logger
logger = logging.getLogger(__name__)

# ============ 常量 ============
HASH_CHUNK_SIZE = 1024 * 1024  # 文件哈希计算 chunk 大小: 1MB


@dataclass
class ProjectSource:
    """项目素材"""

    path: str = ""  # 素材路径
    type: str = "video"  # video/audio/image
    name: str = ""  # 显示名称
    duration: float = 0.0  # 时长（秒）
    size: int = 0  # 文件大小
    hash: str = ""  # 文件哈希（用于验证）


@dataclass
class ProjectConfig:
    """项目配置"""

    # AI 配置
    llm_provider: str = "deepseek"  # LLM 提供商
    llm_model: str = DEFAULT_MODELS["deepseek"]  # LLM 模型
    voice_provider: str = "edge"  # 配音提供商
    voice_id: str = ""  # 声音ID

    # 视频配置
    style: str = "default"  # 风格
    target_duration: float = 0.0  # 目标时长
    target_platform: str = "bilibili"  # 目标平台

    # 字幕配置
    subtitle_style: str = "viral"  # 字幕风格
    subtitle_enabled: bool = True

    # 导出配置
    export_format: str = "mp4"
    export_quality: str = "high"
    export_jianying: bool = True  # 是否导出剪映草稿


@dataclass
class SceneFabProject:
    """
    SceneFab 项目

    完整的项目数据结构
    """

    metadata: ProjectFileMetadata = field(default_factory=ProjectFileMetadata)
    sources: list[ProjectSource] = field(default_factory=list)
    config: ProjectConfig = field(default_factory=ProjectConfig)

    # 项目特定数据（JSON 格式存储）
    project_data: dict[str, Any] = field(default_factory=dict)

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

    # 项目文件扩展名（与产品名一致）。.narrafilm/.narrafiilm 为旧拼写，
    # 保留在加载列表中以兼容已有项目文件。
    PROJECT_EXTENSION = ".scenefab"
    PROJECT_EXTENSIONS = [".scenefab", ".narrafilm", ".narrafiilm", ".vfproj"]

    def __init__(self):
        self.current_project: SceneFabProject | None = None
        self._last_save_path: Path | None = None

    def create_project(
        self,
        name: str = "未命名项目",
        project_type: ProjectType = ProjectType.RAW,
    ) -> SceneFabProject:
        """
        创建新项目

        Args:
            name: 项目名称
            project_type: 项目类型

        Returns:
            新项目对象
        """
        project = SceneFabProject(
            metadata=ProjectFileMetadata(
                name=name,
                project_type=project_type.value,
            )
        )
        self.current_project = project
        return project

    def save(
        self,
        project: SceneFabProject,
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
        output_path = Path(output_path)  # type: ignore[assignment]

        # 确保扩展名正确
        if output_path.suffix.lower() not in self.PROJECT_EXTENSIONS:  # type: ignore[attr-defined]
            output_path = output_path.with_suffix(self.PROJECT_EXTENSION)  # type: ignore[attr-defined]

        # 更新修改时间
        project.metadata.modified_at = datetime.now().isoformat()

        # 转换为字典
        project_dict = self._project_to_dict(project)

        if compress:
            # 使用 zip 压缩
            return self._save_compressed(project_dict, output_path, include_sources)  # type: ignore[arg-type]
        else:
            # 直接保存 JSON
            return self._save_json(project_dict, output_path)  # type: ignore[arg-type]

    def load(self, project_path: str) -> SceneFabProject:
        """
        从文件加载项目

        Args:
            project_path: 项目文件路径

        Returns:
            项目对象
        """
        project_path = Path(project_path)  # type: ignore[assignment]

        if not project_path.exists():  # type: ignore[attr-defined]
            raise FileNotFoundError(f"项目文件不存在: {project_path}")

        # 根据扩展名选择加载方式
        if project_path.suffix.lower() == ".zip" or self._is_compressed(project_path):  # type: ignore[arg-type, attr-defined]
            project_dict = self._load_compressed(project_path)  # type: ignore[arg-type]
        else:
            project_dict = self._load_json(project_path)  # type: ignore[arg-type]

        # 解析项目
        project = self._dict_to_project(project_dict)
        self.current_project = project
        self._last_save_path = project_path  # type: ignore[assignment]

        return project

    def _project_to_dict(self, project: SceneFabProject) -> dict:
        """将项目转换为字典"""
        return {
            "metadata": asdict(project.metadata),
            "sources": [asdict(s) for s in project.sources],
            "config": asdict(project.config),
            "project_data": project.project_data,
        }

    def _dict_to_project(self, data: dict) -> SceneFabProject:
        """将字典转换为项目"""
        metadata = ProjectFileMetadata.from_dict(data.get("metadata", {}))
        sources = [ProjectSource(**s) for s in data.get("sources", [])]
        config = ProjectConfig(**data.get("config", {}))

        project = SceneFabProject(
            metadata=metadata,
            sources=sources,
            config=config,
            project_data=data.get("project_data", {}),
        )

        return project

    def _save_json(self, data: dict, output_path: Path) -> str:
        """保存为 JSON 文件"""
        write_json_file(output_path, data)

        self._last_save_path = output_path
        return str(output_path)

    def _load_json(self, project_path: Path) -> dict:
        """从 JSON 文件加载"""
        from scenefab.utils.json_io import read_json

        data = read_json(project_path)

        # 版本兼容性处理
        data = self._migrate_if_needed(data)

        return data

    def _save_compressed(
        self, data: dict, output_path: Path, include_sources: bool
    ) -> str:
        """保存为压缩的 zip 文件"""
        # 创建 zip
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 保存主项目文件
            project_json = json.dumps(data, ensure_ascii=False, indent=2)
            zf.writestr("project.json", project_json)

            # 保存项目缩略图（如果有）

        self._last_save_path = output_path
        return str(output_path)

    def _load_compressed(self, project_path: Path) -> dict:
        """从压缩文件加载"""
        with zipfile.ZipFile(project_path, "r") as zf:
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
        except Exception as e:
            logger.debug(f"Zipfile check failed: {e}")
            return False

    def _migrate_if_needed(self, data: dict) -> dict:
        """项目版本迁移"""
        version = data.get("metadata", {}).get("version", "1.0")

        if version == "1.0":
            # 从 1.0 迁移到 2.0
            data = self._migrate_v1_to_v2(data)

        return data

    def _migrate_v1_to_v2(self, data: dict) -> dict:
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
        project: SceneFabProject,
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
            with open(path, "rb") as f:
                # 只读取前 1MB 用于哈希计算
                chunk = f.read(HASH_CHUNK_SIZE)
                return hashlib.md5(chunk).hexdigest()
        except Exception as e:
            logger.debug(f"Hash computation failed: {e}")
            return ""

    def get_recent_projects(self, count: int = 10) -> list[dict]:
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
        project: SceneFabProject,
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
        template = SceneFabProject(
            metadata=ProjectFileMetadata(
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
    ) -> SceneFabProject:
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
            project_type=ProjectType(template_data.metadata.project_type),  # type: ignore[call-arg]
        )

        # 复制配置
        project.config = template_data.config

        return project


def save_project(
    project: SceneFabProject,
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


def load_project(project_path: str) -> SceneFabProject:
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

# （示例代码已移除，保持文件简洁）
