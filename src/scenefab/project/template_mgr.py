#!/usr/bin/env python3

"""
项目模板管理器
提供项目模板的创建、管理和应用功能
"""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from scenefab.signals_bridge import QObject, Signal
from scenefab.utils.project_io import (
    PROJECT_SUBDIRS,
    ensure_directories,
    export_to_zip,
    handle_error,
    import_from_zip,
)

from .manager import Project, ProjectType
from scenefab.settings.config import ConfigManager
from .template_models import TemplateCategory, TemplateInfo, TemplateMetadata
from ..utils.json_io import read_json, write_json
from ..utils.version import get_version_string

_handle_template_error = handle_error


class ProjectTemplateManager(QObject):
    """项目模板管理器"""

    # 信号定义
    template_created = Signal(str)  # 模板创建信号
    template_updated = Signal(str)  # 模板更新信号

    template_deleted = Signal(str)  # 模板删除信号
    template_imported = Signal(str)  # 模板导入信号
    template_exported = Signal(str)  # 模板导出信号
    categories_updated = Signal()  # 类别更新信号
    error_occurred = Signal(str, str)  # 错误发生信号

    def __init__(self, config_manager: ConfigManager):
        super().__init__()

        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)

        # 目录设置
        self.templates_dir = Path.home() / "SceneFab" / "Templates"
        self.builtin_templates_dir = Path(__file__).parent / "templates"
        self.temp_dir = Path.home() / "SceneFab" / "Temp"

        # 确保目录存在
        self._ensure_directories()

        # 模板存储
        self.templates: dict[str, TemplateInfo] = {}
        self.categories: dict[str, TemplateCategory] = {}

        # 初始化
        self._init_categories()
        self._load_templates()
        self._load_builtin_templates()

    def _ensure_directories(self) -> None:
        """确保所需目录存在"""
        ensure_directories(self.templates_dir, self.temp_dir)

    def _template_path(self, template_id: str, template_info: TemplateInfo) -> Path:
        """Return the storage directory for a template."""
        root = (
            self.builtin_templates_dir
            if template_info.is_builtin
            else self.templates_dir
        )
        return root / template_id

    def _write_template_info(
        self, template_dir: Path, template_info: TemplateInfo
    ) -> None:
        """Persist a template_info.json file."""
        write_json(template_dir / "template_info.json", template_info.to_dict())

    def _init_categories(self) -> None:
        """初始化模板类别"""
        default_categories = [
            TemplateCategory("video_editing", "视频编辑", "video", "#4CAF50"),
            TemplateCategory("ai_enhancement", "AI增强", "auto_awesome", "#9C27B0"),
            TemplateCategory("compilation", "视频集锦", "movie", "#FF5722"),
            TemplateCategory("commentary", "视频解说", "record_voice_over", "#2196F3"),
            TemplateCategory("social_media", "社交媒体", "share", "#00BCD4"),
            TemplateCategory("education", "教育培训", "school", "#FF9800"),
            TemplateCategory("business", "商务展示", "business", "#607D8B"),
            TemplateCategory("personal", "个人创作", "person", "#E91E63"),
        ]

        for category in default_categories:
            self.categories[category.name] = category

    def _load_templates(self) -> None:
        """加载用户模板"""
        try:
            if not self.templates_dir.exists():
                return

            # 加载模板索引
            index_file = self.templates_dir / "templates.json"
            if index_file.exists():
                templates_data = read_json(index_file)
                for template_id, template_data in templates_data.items():
                    template_info = TemplateInfo.from_dict(template_data)
                    self.templates[template_id] = template_info

            self.logger.info(f"Loaded {len(self.templates)} user templates")

        except Exception as e:
            self.logger.error(f"Failed to load templates: {e}")

    def _load_builtin_templates(self) -> None:
        """加载内置模板"""
        try:
            if not self.builtin_templates_dir.exists():
                return

            # 扫描内置模板目录
            for template_dir in self.builtin_templates_dir.iterdir():
                if template_dir.is_dir():
                    template_info_file = template_dir / "template_info.json"
                    if template_info_file.exists():
                        try:
                            template_data = read_json(template_info_file)
                            template_info = TemplateInfo.from_dict(template_data)
                            template_info.is_builtin = True

                            # 如果用户模板中不存在，则添加
                            if template_info.id not in self.templates:
                                self.templates[template_info.id] = template_info

                        except Exception as e:
                            self.logger.warning(
                                f"Failed to load builtin template {template_dir}: {e}"
                            )

            self.logger.info(
                f"Loaded {len([t for t in self.templates.values() if t.is_builtin])} builtin templates"
            )

        except Exception as e:
            self.logger.error(f"Failed to load builtin templates: {e}")

    def _save_templates(self) -> None:
        """保存模板信息"""
        try:
            index_file = self.templates_dir / "templates.json"
            templates_data = {
                tid: t.to_dict()
                for tid, t in self.templates.items()
                if not t.is_builtin
            }
            write_json(index_file, templates_data)

        except Exception as e:
            self.logger.error(f"Failed to save templates: {e}")

    def _calculate_directory_size(self, directory: Path) -> int:
        """计算目录大小"""
        try:
            total_size = 0
            for dirpath, _dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
            return total_size
        except Exception as e:
            self.logger.error(f"Failed to calculate directory size: {e}")
            return 0

    @_handle_template_error("TEMPLATE", "创建模板")
    def create_template(
        self,
        project: Project,
        template_name: str,
        category: str,
        description: str = "",
        tags: list[str] | None = None,
    ) -> str | None:
        """从项目创建模板"""
        template_id = f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        template_dir = self.templates_dir / template_id
        ensure_directories(template_dir)

        self._copy_project_to_template(project.path, template_dir)

        template_metadata = TemplateMetadata(
            name=template_name,
            description=description,
            author=project.metadata.author,
            version=get_version_string(),
            category=category,
            tags=tags or [],
        )
        metadata_file = template_dir / "template_metadata.json"
        write_json(metadata_file, template_metadata.__dict__)

        template_info = TemplateInfo(
            id=template_id,
            name=template_name,
            description=description,
            category=category,
            author=project.metadata.author,
            version=get_version_string(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_size=self._calculate_directory_size(template_dir),
            tags=tags or [],
            project_type=project.metadata.project_type,
        )

        thumbnail_path = getattr(project.metadata, "thumbnail_path", "")
        if thumbnail_path and os.path.exists(thumbnail_path):
            preview_dest = template_dir / "preview.png"
            shutil.copy2(thumbnail_path, preview_dest)
            template_info.preview_image = str(preview_dest)

        self.templates[template_id] = template_info
        self._save_templates()
        self.template_created.emit(template_id)
        self.logger.info(f"Created template: {template_name} ({template_id})")
        return template_id

    def _copy_project_to_template(self, project_path: str, template_dir: Path) -> None:
        """复制项目文件到模板目录"""
        try:
            # 复制项目配置文件
            project_file = os.path.join(project_path, "project.json")
            if os.path.exists(project_file):
                shutil.copy2(project_file, template_dir / "project_template.json")

            # 复制媒体文件（可选，可以只复制结构）
            media_source = Path(project_path) / "media"
            if media_source.exists():
                media_dest = template_dir / "media"
                shutil.copytree(media_source, media_dest, dirs_exist_ok=True)

            # 复制资产文件
            assets_source = Path(project_path) / "assets"
            if assets_source.exists():
                assets_dest = template_dir / "assets"
                shutil.copytree(assets_source, assets_dest, dirs_exist_ok=True)

        except Exception as e:
            self.logger.error(f"Failed to copy project to template: {e}")

    @_handle_template_error("TEMPLATE", "应用模板")
    def apply_template(
        self,
        template_id: str,
        project_name: str,
        project_path: str,
        variables: dict[str, Any] | None = None,
    ) -> bool:
        """应用模板创建项目"""
        if template_id not in self.templates:
            self.error_occurred.emit("TEMPLATE_ERROR", f"模板不存在: {template_id}")
            return False

        template_info = self.templates[template_id]
        template_path = self._template_path(template_id, template_info)

        if not template_path.exists():
            self.error_occurred.emit("TEMPLATE_ERROR", f"模板文件不存在: {template_id}")
            return False

        project_dir = Path(project_path)
        ensure_directories(project_dir)
        ensure_directories(*(project_dir / subdir for subdir in PROJECT_SUBDIRS))

        self._copy_template_to_project(template_path, project_dir, variables or {})

        if not template_info.is_builtin:
            template_info.download_count += 1
            self._save_templates()

        self.logger.info(f"Applied template {template_id} to project {project_name}")
        return True

    def _copy_template_to_project(
        self, template_path: Path, project_dir: Path, variables: dict[str, Any]
    ) -> None:
        """复制模板文件到项目目录"""
        try:
            # 处理模板项目文件
            template_project_file = template_path / "project_template.json"
            if template_project_file.exists():
                project_data = read_json(template_project_file)

                # 应用变量替换
                self._apply_variables_to_project(project_data, variables)

                # 更新项目元数据
                if "metadata" in project_data:
                    project_data["metadata"]["name"] = variables.get(
                        "project_name", "Untitled Project"
                    )
                    project_data["metadata"]["created_at"] = datetime.now().isoformat()
                    project_data["metadata"]["modified_at"] = datetime.now().isoformat()

                # 保存项目文件
                write_json(project_dir / "project.json", project_data)

            # 复制媒体文件
            media_source = template_path / "media"
            if media_source.exists():
                media_dest = project_dir / "media"
                shutil.copytree(media_source, media_dest, dirs_exist_ok=True)

            # 复制资产文件
            assets_source = template_path / "assets"
            if assets_source.exists():
                assets_dest = project_dir / "assets"
                shutil.copytree(assets_source, assets_dest, dirs_exist_ok=True)

            # 复制其他文件
            for file_path in template_path.rglob("*"):
                if file_path.is_file() and file_path.name not in [
                    "project_template.json",
                    "template_metadata.json",
                    "template_info.json",
                ]:
                    relative_path = file_path.relative_to(template_path)
                    dest_path = project_dir / relative_path
                    ensure_directories(dest_path.parent)
                    shutil.copy2(file_path, dest_path)

        except Exception as e:
            self.logger.error(f"Failed to copy template to project: {e}")

    def _apply_variables_to_project(
        self, project_data: dict[str, Any], variables: dict[str, Any]
    ) -> None:
        """应用变量到项目数据"""
        try:
            # 递归替换变量
            def replace_variables(obj):
                if isinstance(obj, dict):
                    return {k: replace_variables(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [replace_variables(item) for item in obj]
                elif isinstance(obj, str):
                    # 替换变量占位符
                    for var_name, var_value in variables.items():
                        obj = obj.replace(f"${{{var_name}}}", str(var_value))
                    return obj
                else:
                    return obj

            replaced_project_data = replace_variables(project_data)
            project_data.clear()
            project_data.update(replaced_project_data)

        except Exception as e:
            self.logger.error(f"Failed to apply variables to project: {e}")

    @_handle_template_error("UPDATE", "更新模板")
    def update_template(self, template_id: str, updates: dict[str, Any]) -> bool:
        """更新模板信息"""
        if template_id not in self.templates:
            return False

        template_info = self.templates[template_id]
        for key, value in updates.items():
            if hasattr(template_info, key):
                setattr(template_info, key, value)

        template_info.updated_at = datetime.now()

        if not template_info.is_builtin:
            template_dir = self.templates_dir / template_id
            if template_dir.exists():
                self._write_template_info(template_dir, template_info)

        self._save_templates()
        self.template_updated.emit(template_id)
        self.logger.info(f"Updated template: {template_id}")
        return True

    @_handle_template_error("DELETE", "删除模板")
    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        if template_id not in self.templates:
            return False

        template_info = self.templates[template_id]
        if template_info.is_builtin:
            self.error_occurred.emit("TEMPLATE_ERROR", "不能删除内置模板")
            return False

        template_dir = self.templates_dir / template_id
        if template_dir.exists():
            shutil.rmtree(template_dir)

        del self.templates[template_id]
        self._save_templates()
        self.template_deleted.emit(template_id)
        self.logger.info(f"Deleted template: {template_id}")
        return True

    def get_template(self, template_id: str) -> TemplateInfo | None:
        """获取模板信息"""
        return self.templates.get(template_id)

    def get_all_templates(self) -> list[TemplateInfo]:
        """获取所有模板"""
        return list(self.templates.values())

    def get_templates_by_category(self, category: str) -> list[TemplateInfo]:
        """按类别获取模板"""
        return [t for t in self.templates.values() if t.category == category]

    def get_templates_by_type(self, project_type: ProjectType) -> list[TemplateInfo]:
        """按类型获取模板"""
        return [t for t in self.templates.values() if t.project_type == project_type]

    def get_categories(self) -> list[TemplateCategory]:
        """获取所有类别"""
        return list(self.categories.values())

    def search_templates(
        self,
        query: str,
        category: str | None = None,
        project_type: ProjectType | None = None,
    ) -> list[TemplateInfo]:
        """搜索模板"""
        results = []

        for template in self.templates.values():
            # 检查类别过滤
            if category and template.category != category:
                continue

            # 检查类型过滤
            if project_type and template.project_type != project_type:
                continue

            # 检查搜索条件
            query_lower = query.lower()
            if (
                query_lower in template.name.lower()
                or query_lower in template.description.lower()
                or any(query_lower in tag.lower() for tag in template.tags)
            ):
                results.append(template)

        return results

    @_handle_template_error("EXPORT", "导出模板")
    def export_template(self, template_id: str, export_path: str) -> bool:
        """导出模板"""
        if template_id not in self.templates:
            return False

        template_info = self.templates[template_id]
        template_path = self._template_path(template_id, template_info)

        if not template_path.exists():
            return False

        export_to_zip(
            template_path,
            export_path,
            extra_info={"template_info": template_info.to_dict()},
        )
        self.template_exported.emit(template_id)
        self.logger.info(f"Exported template: {template_id} to {export_path}")
        return True

    @_handle_template_error("IMPORT", "导入模板")
    def import_template(self, import_path: str) -> str | None:
        """导入模板"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = self.temp_dir / f"template_import_{timestamp}"
        template_id = f"imported_{timestamp}"
        template_dir = self.templates_dir / template_id

        result = import_from_zip(
            import_path, temp_dir, template_dir, "export_info.json"
        )
        if result is None:
            self.error_occurred.emit("TEMPLATE_ERROR", "无效的模板文件")
            return None

        # 读取并更新模板信息
        export_info_file = result / "export_info.json"
        export_info = read_json(export_info_file)

        template_info = TemplateInfo.from_dict(export_info["template_info"])
        template_info.id = template_id
        template_info.is_builtin = False
        template_info.updated_at = datetime.now()

        self._write_template_info(result, template_info)

        self.templates[template_id] = template_info
        self._save_templates()
        self.template_imported.emit(template_id)
        self.logger.info(f"Imported template: {template_id}")
        return template_id

    @_handle_template_error("RATE", "评分模板")
    def rate_template(self, template_id: str, rating: float) -> bool:
        """评分模板"""
        if template_id not in self.templates:
            return False

        template_info = self.templates[template_id]
        template_info.rating = max(0.0, min(5.0, rating))
        template_info.updated_at = datetime.now()

        self._save_templates()
        self.logger.info(f"Rated template {template_id}: {rating}")
        return True

    def get_template_statistics(self) -> dict[str, Any]:
        """获取模板统计信息"""
        try:
            total_templates = len(self.templates)
            builtin_templates = len(
                [t for t in self.templates.values() if t.is_builtin]
            )
            user_templates = total_templates - builtin_templates

            # 按类别统计
            category_stats = {}
            for category in self.categories.values():
                count = len(
                    [t for t in self.templates.values() if t.category == category.name]
                )
                category_stats[category.name] = count

            # 按类型统计
            type_stats = {}
            for project_type in ProjectType:
                count = len(
                    [
                        t
                        for t in self.templates.values()
                        if t.project_type == project_type
                    ]
                )
                type_stats[project_type.value] = count

            # 下载统计
            total_downloads = sum(t.download_count for t in self.templates.values())

            # 评分统计
            rated_templates = [t for t in self.templates.values() if t.rating > 0]
            avg_rating = (
                sum(t.rating for t in rated_templates) / len(rated_templates)
                if rated_templates
                else 0.0
            )

            return {
                "total_templates": total_templates,
                "builtin_templates": builtin_templates,
                "user_templates": user_templates,
                "category_stats": category_stats,
                "type_stats": type_stats,
                "total_downloads": total_downloads,
                "average_rating": avg_rating,
                "rated_templates_count": len(rated_templates),
            }

        except Exception as e:
            self.logger.error(f"Failed to get template statistics: {e}")
            return {}

    def validate_template(self, template_id: str) -> dict[str, Any]:
        """验证模板完整性"""
        try:
            if template_id not in self.templates:
                return {"valid": False, "errors": ["模板不存在"]}

            template_info = self.templates[template_id]

            template_path = self._template_path(template_id, template_info)

            if not template_path.exists():
                return {"valid": False, "errors": ["模板目录不存在"]}

            errors = []
            warnings = []

            # 检查必需文件
            required_files = ["project_template.json"]
            for file_name in required_files:
                file_path = template_path / file_name
                if not file_path.exists():
                    errors.append(f"缺少必需文件: {file_name}")

            # 检查模板信息
            info_file = template_path / "template_info.json"
            if not info_file.exists():
                warnings.append("缺少模板信息文件")

            # 检查文件大小
            actual_size = self._calculate_directory_size(template_path)
            if actual_size != template_info.file_size:
                warnings.append(
                    f"文件大小不匹配: 预期 {template_info.file_size}, 实际 {actual_size}"
                )

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "actual_size": actual_size,
            }

        except Exception as e:
            self.logger.error(f"Failed to validate template {template_id}: {e}")
            return {"valid": False, "errors": [f"验证失败: {str(e)}"]}


# Backward compatibility alias
TemplateManager = ProjectTemplateManager
