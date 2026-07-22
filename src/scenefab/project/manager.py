#!/usr/bin/env python3

"""
SceneFab 项目管理器
提供完整的项目生命周期管理功能
"""

import getpass
import logging
import os
import shutil
import uuid
from dataclasses import asdict
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

from .models.project_models import (
    ProjectMedia,
    ProjectMetadata,
    ProjectSettings,
    ProjectTimeline,
    ProjectType,
)
from .settings import ConfigManager
from .utils.json_io import read_json, write_json

_handle_project_error = handle_error


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

    def add_media_file(self, media_file: ProjectMedia) -> None:
        """添加媒体文件"""
        self.media_files[media_file.id] = media_file
        self.is_modified = True
        self.metadata.modified_at = datetime.now().isoformat()

    def remove_media_file(self, media_id: str) -> bool:
        """移除媒体文件"""
        if media_id in self.media_files:
            del self.media_files[media_id]
            self.is_modified = True
            self.metadata.modified_at = datetime.now().isoformat()
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
        self.metadata.modified_at = datetime.now().isoformat()

    def save(self) -> bool:
        """保存项目"""
        try:
            project_data = {
                "id": self.id,
                "metadata": self.metadata.to_dict(),
                "settings": asdict(self.settings),
                "media_files": {k: v.to_dict() for k, v in self.media_files.items()},
                "timeline": self.timeline.to_dict(),
                "version": "2.0.0",
            }
            project_file = os.path.join(self.path, "project.json")
            write_json(project_file, project_data)
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
            project_data = read_json(project_file)
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
            ensure_directories(backup_path)
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
            write_json(os.path.join(backup_path, "backup_info.json"), backup_info)
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
                        backup_info = read_json(backup_info_file)
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
        self.logger = logging.getLogger(__name__)
        self.projects: dict[str, Project] = {}
        self.current_project: Project | None = None
        self.projects_dir = os.path.expanduser("~/SceneFab/Projects")
        self.templates_dir = os.path.expanduser("~/SceneFab/Templates")
        self.temp_dir = os.path.expanduser("~/SceneFab/Temp")
        self._ensure_directories()
        self.recent_projects: list[str] = self._load_recent_projects()
        self._setup_auto_save()

    def _ensure_directories(self) -> None:
        ensure_directories(self.projects_dir, self.templates_dir, self.temp_dir)

    def _load_recent_projects(self) -> list[str]:
        # NOTE: recent_projects 持久化改用本地文件 + 在 _save_recent_projects 中处理.
        # 历史版本曾尝试走 ConfigManager.get/set("editor.recent_files"),但 ConfigManager
        # 已重构为强类型 AppConfig 接口,不再提供 dict-like get/set.
        # 见 issue #82 + PR: 全局配置不应承担 UI 状态,改由 ProjectManager 自行持久化.
        cache_file = Path(self.projects_dir) / ".recent_projects.json"
        if not cache_file.exists():
            return []
        try:
            data = read_json(cache_file)
            return [str(p) for p in data if isinstance(p, str)]
        except (OSError, ValueError) as e:
            self.logger.warning(f"无法加载最近项目列表: {e}")
            return []

    def _save_recent_projects(self) -> None:
        cache_file = Path(self.projects_dir) / ".recent_projects.json"
        try:
            write_json(cache_file, self.recent_projects[:10])
        except OSError as e:
            self.logger.warning(f"无法保存最近项目列表: {e}")
        self.recent_projects_updated.emit(self.recent_projects[:10])

    def _add_to_recent_projects(self, project_path: str) -> None:
        if project_path in self.recent_projects:
            self.recent_projects.remove(project_path)
        self.recent_projects.insert(0, project_path)
        self._save_recent_projects()

    def _setup_auto_save(self) -> None:
        try:
            from PySide6.QtCore import QTimer
        except ImportError:
            self.logger.debug("PySide6 not available, auto-save disabled")
            return

        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_timer.start(60000)

    def _auto_save(self) -> None:
        if self.current_project and self.current_project.is_modified:
            interval = self.current_project.settings.auto_save_interval
            if interval > 0:
                modified_at_str = self.current_project.metadata.modified_at
                if not modified_at_str:
                    return
                modified_at = datetime.fromisoformat(modified_at_str)
                elapsed = (datetime.now() - modified_at).total_seconds()
                if elapsed >= interval:
                    self.save_project(self.current_project.id, auto_save=True)

    def _is_process_running(self, pid_str: str) -> bool:
        try:
            import psutil

            return psutil.pid_exists(int(pid_str))  # type: ignore[no-any-return, attr-defined]  # type: ignore[attr-defined]
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
        ensure_directories(project_path)
        ensure_directories(
            *(os.path.join(project_path, subdir) for subdir in PROJECT_SUBDIRS)
        )
        metadata = ProjectMetadata(
            name=name,
            description=description,
            project_type=project_type,
            author=getpass.getuser(),
        )
        project = Project(project_id, project_path, metadata)
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
        project_data = read_json(project_file)
        metadata = ProjectMetadata.from_dict(project_data["metadata"])
        project_id = project_data.get("id", metadata.name)
        project = Project(project_id, project_path, metadata)
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

        def _filter(path: Path) -> bool:
            if not include_media:
                return path.name == "project.json"
            return True

        export_to_zip(
            project.path,
            export_path,
            extra_info={
                "project_version": project.metadata.version,
                "include_media": include_media,
            },
            file_filter=_filter,
        )
        self.project_exported.emit(project_id)
        self.logger.info(f"Exported project: {project.metadata.name} to {export_path}")
        return True

    @_handle_project_error("IMPORT", "导入项目")
    def import_project(self, import_path: str) -> str | None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = Path(self.temp_dir) / f"import_{timestamp}"
        project_name = f"imported_{timestamp}"
        project_path = (
            Path(self.projects_dir) / f"{project_name}_{uuid.uuid4().hex[:8]}"
        )

        result = import_from_zip(import_path, temp_dir, project_path, "project.json")
        if result is None:
            self.error_occurred.emit("IMPORT_ERROR", "无效的项目文件")
            return None

        # 更新项目名称
        project_file = result / "project.json"
        project_data = read_json(project_file)
        project_data["metadata"]["name"] = project_name
        project_data["metadata"]["modified_at"] = datetime.now().isoformat()
        write_json(project_file, project_data)

        project_id = self.open_project(str(result))
        if project_id:
            self.project_imported.emit(project_id)
            self.logger.info(f"Imported project: {project_name} from {import_path}")
        return project_id  # type: ignore[no-any-return]

    def get_project(self, project_id: str) -> Project | None:
        return self.projects.get(project_id)

    def get_current_project(self) -> Project | None:
        return self.current_project

    def get_all_projects(self) -> list[Project]:
        return list(self.projects.values())

    def get_recent_projects(self) -> list[str]:
        return self.recent_projects.copy()

    def scan_projects(self) -> list[Project]:
        discovered = []
        try:
            for project_dir in os.listdir(self.projects_dir):
                project_path = os.path.join(self.projects_dir, project_dir)
                if os.path.isdir(project_path):
                    project_file = os.path.join(project_path, "project.json")
                    if os.path.exists(project_file):
                        try:
                            project_data = read_json(project_file)
                            metadata = ProjectMetadata.from_dict(
                                project_data["metadata"]
                            )
                            project_id = project_data.get("id", metadata.name)
                            discovered.append(
                                Project(project_id, project_path, metadata)
                            )
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to load project from {project_path}: {e}"
                            )
        except Exception as e:
            self.logger.error(f"Failed to scan projects: {e}")
        return discovered

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
