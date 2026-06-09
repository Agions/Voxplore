#!/usr/bin/env python3

"""
SceneFab 项目管理器
提供完整的项目生命周期管理功能
"""

import functools
import json
import logging
import os
import shutil
import uuid
import zipfile
from dataclasses import asdict
from datetime import datetime
from typing import Any

from scenefab.signals_bridge import QObject, Signal

from .models.project_models import (
    ProjectMedia,
    ProjectMetadata,
    ProjectSettings,
    ProjectStatus,
    ProjectTimeline,
    ProjectType,
)
from .secure_key_manager import get_secure_key_manager
from .settings import ConfigManager


# ─── 错误处理装饰器 ────────────────────────────────────────────
def _handle_project_error(action_code: str, action_name: str):
    """
    统一处理 ProjectManager 各方法的异常：记录日志、发送信号、返回默认值。
    适用于所有返回 bool / Optional[str] 的项目操作方法。
    """

    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            try:
                return method(self, *args, **kwargs)
            except Exception as e:
                self.logger.error(f"Failed to {action_name}: {e}")
                self.error_occurred.emit(
                    f"{action_code}_ERROR", f"{action_name}失败: {str(e)}"
                )
                # 根据返回值类型返回 False 或 None
                hints = {"bool": False, "str": None}
                ret_type = method.__annotations__.get("return", "")
                return hints.get(
                    str(ret_type).split("'")[1] if "'" in str(ret_type) else ""
                )

        return wrapper

    return decorator


class Project:
    """项目类"""

    def __init__(self, project_id: str, project_path: str, metadata: ProjectMetadata):
        self.id = project_id
        self.path = project_path
        self.metadata = metadata
        self.settings = ProjectSettings()
        self.media_files: dict[str, ProjectMedia] = {}
        self.timeline = ProjectTimeline()
        self.is_modified = False
        self.is_loaded = False
        self._auto_save_timer = None

    def add_media_file(self, media_file: ProjectMedia) -> None:
        """添加媒体文件"""
        self.media_files[media_file.id] = media_file
        self.is_modified = True
        self.metadata.modified_at = datetime.now()

    def remove_media_file(self, media_id: str) -> bool:
        """移除媒体文件"""
        if media_id in self.media_files:
            del self.media_files[media_id]
            self.is_modified = True
            self.metadata.modified_at = datetime.now()
            return True
        return False

    def get_media_file(self, media_id: str) -> ProjectMedia | None:
        """获取媒体文件"""
        return self.media_files.get(media_id)

    def get_all_media_files(self) -> list[ProjectMedia]:
        """获取所有媒体文件"""
        return list(self.media_files.values())

    def update_settings(self, settings: dict[str, Any]) -> None:
        """更新项目设置"""
        for key, value in settings.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
            else:
                self.settings.custom_settings[key] = value
        self.is_modified = True
        self.metadata.modified_at = datetime.now()

    def save(self) -> bool:
        """保存项目"""
        try:
            project_data = {
                "metadata": self.metadata.to_dict(),
                "settings": asdict(self.settings),
                "media_files": {k: v.to_dict() for k, v in self.media_files.items()},
                "timeline": self.timeline.to_dict(),
                "version": "2.0.0",
            }
            project_file = os.path.join(self.path, "project.json")
            with open(project_file, "w", encoding="utf-8") as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            lock_file = os.path.join(self.path, ".lock")
            with open(lock_file, "w") as f:
                f.write(str(os.getpid()))
            self.is_modified = False
            return True
        except Exception as e:
            logging.error(f"Failed to save project {self.id}: {e}")
            return False

    def load(self) -> bool:
        """加载项目"""
        try:
            project_file = os.path.join(self.path, "project.json")
            if not os.path.exists(project_file):
                return False
            with open(project_file, encoding="utf-8") as f:
                project_data = json.load(f)
            self.metadata = ProjectMetadata.from_dict(project_data["metadata"])
            self.settings = ProjectSettings(**project_data.get("settings", {}))
            self.media_files.clear()
            for media_id, media_data in project_data.get("media_files", {}).items():
                self.media_files[media_id] = ProjectMedia.from_dict(media_data)
            self.timeline = ProjectTimeline.from_dict(project_data.get("timeline", {}))
            self.is_loaded = True
            self.is_modified = False
            return True
        except Exception as e:
            logging.error(f"Failed to load project {self.id}: {e}")
            return False

    def create_backup(self) -> str | None:
        """创建项目备份"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
            backup_path = os.path.join(self.path, "backups", backup_name)
            os.makedirs(backup_path, exist_ok=True)
            shutil.copy2(
                os.path.join(self.path, "project.json"),
                os.path.join(backup_path, "project.json"),
            )
            backup_info = {
                "timestamp": timestamp,
                "created_at": datetime.now().isoformat(),
                "project_version": self.metadata.version,
                "description": f"自动备份 - {timestamp}",
            }
            with open(os.path.join(backup_path, "backup_info.json"), "w") as f:
                json.dump(backup_info, f, indent=2)
            return backup_path
        except Exception as e:
            logging.error(f"Failed to create backup for project {self.id}: {e}")
            return None

    def cleanup_old_backups(self, keep_count: int = 10) -> None:
        """清理旧备份"""
        try:
            backup_dir = os.path.join(self.path, "backups")
            if not os.path.exists(backup_dir):
                return
            backups = []
            for backup_name in os.listdir(backup_dir):
                backup_path = os.path.join(backup_dir, backup_name)
                if os.path.isdir(backup_path):
                    backup_info_file = os.path.join(backup_path, "backup_info.json")
                    if os.path.exists(backup_info_file):
                        with open(backup_info_file) as f:
                            backup_info = json.load(f)
                            backups.append((backup_path, backup_info["timestamp"]))
            backups.sort(key=lambda x: x[1], reverse=True)
            for backup_path, _ in backups[keep_count:]:
                shutil.rmtree(backup_path)
        except Exception as e:
            logging.error(f"Failed to cleanup backups for project {self.id}: {e}")


class ProjectManager(QObject):
    """项目管理器"""

    project_created = Signal(str)
    project_opened = Signal(str)
    project_saved = Signal(str)
    project_closed = Signal(str)
    project_deleted = Signal(str)
    project_imported = Signal(str)
    project_exported = Signal(str)
    recent_projects_updated = Signal(list)
    error_occurred = Signal(str, str)

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.secure_key_manager = get_secure_key_manager()
        self.projects: dict[str, Project] = {}
        self.current_project: Project | None = None
        self.templates: dict[str, Project] = {}
        self.projects_dir = os.path.expanduser("~/SceneFab/Projects")
        self.templates_dir = os.path.expanduser("~/SceneFab/Templates")
        self.temp_dir = os.path.expanduser("~/SceneFab/Temp")
        self._ensure_directories()
        self.recent_projects: list[str] = self._load_recent_projects()
        self._load_templates()
        self._setup_auto_save()

    def _ensure_directories(self) -> None:
        for directory in [self.projects_dir, self.templates_dir, self.temp_dir]:
            os.makedirs(directory, exist_ok=True)

    def _load_recent_projects(self) -> list[str]:
        return self.config_manager.get("editor.recent_files", [])

    def _save_recent_projects(self) -> None:
        self.config_manager.set("editor.recent_files", self.recent_projects[:10])
        self.recent_projects_updated.emit(self.recent_projects[:10])

    def _add_to_recent_projects(self, project_path: str) -> None:
        if project_path in self.recent_projects:
            self.recent_projects.remove(project_path)
        self.recent_projects.insert(0, project_path)
        self._save_recent_projects()

    def _setup_auto_save(self) -> None:
        from PySide6.QtCore import QTimer

        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_timer.start(60000)

    def _auto_save(self) -> None:
        if self.current_project and self.current_project.is_modified:
            interval = self.current_project.settings.auto_save_interval
            if interval > 0:
                elapsed = (
                    datetime.now() - self.current_project.metadata.modified_at
                ).total_seconds()
                if elapsed >= interval:
                    self.save_project(self.current_project.id, auto_save=True)

    def _is_process_running(self, pid_str: str) -> bool:
        try:
            import psutil

            return psutil.pid_exists(int(pid_str))
        except (ImportError, ValueError):
            return False

    @_handle_project_error("CREATE", "创建项目")
    def create_project(
        self,
        name: str,
        project_type: ProjectType = ProjectType.VIDEO_EDITING,
        description: str = "",
        template_id: str | None = None,
    ) -> str | None:
        project_id = str(uuid.uuid4())
        project_path = os.path.join(self.projects_dir, f"{name}_{project_id[:8]}")
        os.makedirs(project_path, exist_ok=True)
        for subdir in ["media", "exports", "backups", "cache", "assets"]:
            os.makedirs(os.path.join(project_path, subdir), exist_ok=True)
        metadata = ProjectMetadata(
            name=name,
            description=description,
            project_type=project_type,
            author=os.getlogin(),
        )
        project = Project(project_id, project_path, metadata)
        if template_id and template_id in self.templates:
            template = self.templates[template_id]
            project.settings = template.settings
            project.timeline = template.timeline
        if project.save():
            self.projects[project_id] = project
            self.current_project = project
            self._add_to_recent_projects(project_path)
            self.project_created.emit(project_id)
            self.logger.info(f"Created project: {name} ({project_id})")
            return project_id
        shutil.rmtree(project_path)
        return None

    @_handle_project_error("OPEN", "打开项目")
    def open_project(self, project_path: str) -> str | None:
        project_file = os.path.join(project_path, "project.json")
        if not os.path.exists(project_file):
            self.error_occurred.emit("OPEN_ERROR", f"项目文件不存在: {project_path}")
            return None
        lock_file = os.path.join(project_path, ".lock")
        if os.path.exists(lock_file):
            with open(lock_file) as f:
                pid = f.read().strip()
            if self._is_process_running(pid):
                self.error_occurred.emit("OPEN_ERROR", "项目已被其他进程打开")
                return None
        with open(project_file, encoding="utf-8") as f:
            project_data = json.load(f)
        metadata = ProjectMetadata.from_dict(project_data["metadata"])
        project = Project(metadata.name, project_path, metadata)
        if project.load():
            self.projects[project.id] = project
            self.current_project = project
            self._add_to_recent_projects(project_path)
            with open(lock_file, "w") as f:
                f.write(str(os.getpid()))
            self.project_opened.emit(project.id)
            self.logger.info(f"Opened project: {metadata.name} ({project.id})")
            return project.id
        return None

    @_handle_project_error("SAVE", "保存项目")
    def save_project(self, project_id: str, auto_save: bool = False) -> bool:
        if project_id not in self.projects:
            return False
        project = self.projects[project_id]
        if project.settings.backup_enabled and not auto_save:
            backup_path = project.create_backup()
            if backup_path:
                project.cleanup_old_backups(project.settings.backup_count)
        if project.save():
            self.project_saved.emit(project_id)
            if not auto_save:
                self.logger.info(
                    f"Saved project: {project.metadata.name} ({project_id})"
                )
            return True
        return False

    @_handle_project_error("CLOSE", "关闭项目")
    def close_project(self, project_id: str) -> bool:
        if project_id not in self.projects:
            return False
        project = self.projects[project_id]
        if project.is_modified:
            self.save_project(project_id)
        lock_file = os.path.join(project.path, ".lock")
        if os.path.exists(lock_file):
            os.remove(lock_file)
        if self.current_project and self.current_project.id == project_id:
            self.current_project = None
        self.project_closed.emit(project_id)
        self.logger.info(f"Closed project: {project.metadata.name} ({project_id})")
        return True

    @_handle_project_error("DELETE", "删除项目")
    def delete_project(self, project_id: str) -> bool:
        if project_id not in self.projects:
            return False
        project = self.projects[project_id]
        self.close_project(project_id)
        if os.path.exists(project.path):
            shutil.rmtree(project.path)
        del self.projects[project_id]
        if project.path in self.recent_projects:
            self.recent_projects.remove(project.path)
            self._save_recent_projects()
        self.project_deleted.emit(project_id)
        self.logger.info(f"Deleted project: {project.metadata.name} ({project_id})")
        return True

    @_handle_project_error("EXPORT", "导出项目")
    def export_project(
        self, project_id: str, export_path: str, include_media: bool = True
    ) -> bool:
        if project_id not in self.projects:
            return False
        project = self.projects[project_id]
        with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            project_file = os.path.join(project.path, "project.json")
            if os.path.exists(project_file):
                zipf.write(project_file, "project.json")
            if include_media:
                media_dir = os.path.join(project.path, "media")
                if os.path.exists(media_dir):
                    for root, _dirs, files in os.walk(media_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, project.path)
                            zipf.write(file_path, arcname)
            export_info = {
                "exported_at": datetime.now().isoformat(),
                "project_version": project.metadata.version,
                "cineai_version": "2.0.0",
                "include_media": include_media,
            }
            zipf.writestr("export_info.json", json.dumps(export_info, indent=2))
        self.project_exported.emit(project_id)
        self.logger.info(f"Exported project: {project.metadata.name} to {export_path}")
        return True

    @_handle_project_error("IMPORT", "导入项目")
    def import_project(self, import_path: str) -> str | None:
        temp_dir = os.path.join(
            self.temp_dir, f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        os.makedirs(temp_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(import_path, "r") as zipf:
                zipf.extractall(temp_dir)
            project_file = os.path.join(temp_dir, "project.json")
            if not os.path.exists(project_file):
                self.error_occurred.emit("IMPORT_ERROR", "无效的项目文件")
                return None
            with open(project_file, encoding="utf-8") as f:
                project_data = json.load(f)
            metadata = ProjectMetadata.from_dict(project_data["metadata"])
            project_name = f"{metadata.name}_imported"
            project_path = os.path.join(
                self.projects_dir, f"{project_name}_{uuid.uuid4().hex[:8]}"
            )
            shutil.copytree(temp_dir, project_path)
            project_file = os.path.join(project_path, "project.json")
            with open(project_file, encoding="utf-8") as f:
                project_data = json.load(f)
            project_data["metadata"]["name"] = project_name
            project_data["metadata"]["modified_at"] = datetime.now().isoformat()
            with open(project_file, "w", encoding="utf-8") as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        project_id = self.open_project(project_path)
        if project_id:
            self.project_imported.emit(project_id)
            self.logger.info(f"Imported project: {project_name} from {import_path}")
        return project_id

    @_handle_project_error("CREATE", "创建模板")
    def create_template(self, project_id: str, template_name: str) -> bool:
        if project_id not in self.projects:
            return False
        project = self.projects[project_id]
        template_path = os.path.join(self.templates_dir, template_name)
        os.makedirs(template_path, exist_ok=True)
        shutil.copy2(
            os.path.join(project.path, "project.json"),
            os.path.join(template_path, "project.json"),
        )
        template_file = os.path.join(template_path, "project.json")
        with open(template_file, encoding="utf-8") as f:
            template_data = json.load(f)
        template_data["metadata"]["name"] = template_name
        template_data["metadata"]["status"] = "template"
        template_data["metadata"]["description"] = (
            f"模板创建自项目: {project.metadata.name}"
        )
        template_data["metadata"]["modified_at"] = datetime.now().isoformat()
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)
        self._load_templates()
        self.logger.info(f"Created template: {template_name} from project {project_id}")
        return True

    def get_project(self, project_id: str) -> Project | None:
        return self.projects.get(project_id)

    def get_current_project(self) -> Project | None:
        return self.current_project

    def get_all_projects(self) -> list[Project]:
        return list(self.projects.values())

    def get_recent_projects(self) -> list[str]:
        return self.recent_projects.copy()

    def get_templates(self) -> list[Project]:
        return list(self.templates.values())

    def scan_projects(self) -> list[Project]:
        discovered = []
        try:
            for project_dir in os.listdir(self.projects_dir):
                project_path = os.path.join(self.projects_dir, project_dir)
                if os.path.isdir(project_path):
                    project_file = os.path.join(project_path, "project.json")
                    if os.path.exists(project_file):
                        try:
                            with open(project_file, encoding="utf-8") as f:
                                project_data = json.load(f)
                            metadata = ProjectMetadata.from_dict(
                                project_data["metadata"]
                            )
                            discovered.append(
                                Project(metadata.name, project_path, metadata)
                            )
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to load project from {project_path}: {e}"
                            )
        except Exception as e:
            self.logger.error(f"Failed to scan projects: {e}")
        return discovered

    def _load_templates(self) -> None:
        try:
            if not os.path.exists(self.templates_dir):
                return
            for template_dir in os.listdir(self.templates_dir):
                template_path = os.path.join(self.templates_dir, template_dir)
                if os.path.isdir(template_path):
                    template_file = os.path.join(template_path, "project.json")
                    if os.path.exists(template_file):
                        try:
                            with open(template_file, encoding="utf-8") as f:
                                template_data = json.load(f)
                            metadata = ProjectMetadata.from_dict(
                                template_data["metadata"]
                            )
                            metadata.status = ProjectStatus.TEMPLATE
                            template = Project(metadata.name, template_path, metadata)
                            template.load()
                            self.templates[template_dir] = template
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to load template {template_dir}: {e}"
                            )
            self.logger.info(f"Loaded {len(self.templates)} templates")
        except Exception as e:
            self.logger.error(f"Failed to load templates: {e}")

    def cleanup(self) -> None:
        for project_id in list(self.projects.keys()):
            self.close_project(project_id)
        if hasattr(self, "auto_save_timer"):
            self.auto_save_timer.stop()
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temp dir: {e}")
