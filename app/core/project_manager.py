#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 项目管理器
提供完整的项目生命周期管理功能
"""

import os
import json
import shutil
import uuid
import zipfile
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

from PySide6.QtCore import QObject, Signal

from .config_manager import ConfigManager
from .secure_key_manager import get_secure_key_manager
from .models.project_models import (
    ProjectStatus, ProjectType,
    ProjectMetadata, ProjectSettings,
    ProjectMedia, ProjectTimeline,
)



class Project:
    """项目类"""

    def __init__(self, project_id: str, project_path: str, metadata: ProjectMetadata):
        self.id = project_id
        self.path = project_path
        self.metadata = metadata
        self.settings = ProjectSettings()
        self.media_files: Dict[str, ProjectMedia] = {}
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

    def get_media_file(self, media_id: str) -> Optional[ProjectMedia]:
        """获取媒体文件"""
        return self.media_files.get(media_id)

    def get_all_media_files(self) -> List[ProjectMedia]:
        """获取所有媒体文件"""
        return list(self.media_files.values())

    def update_settings(self, settings: Dict[str, Any]) -> None:
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
                'metadata': self.metadata.to_dict(),
                'settings': asdict(self.settings),
                'media_files': {k: v.to_dict() for k, v in self.media_files.items()},
                'timeline': self.timeline.to_dict(),
                'version': '2.0.0'
            }

            # 保存主项目文件
            project_file = os.path.join(self.path, 'project.json')
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)

            # 保存项目锁文件
            lock_file = os.path.join(self.path, '.lock')
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))

            self.is_modified = False
            return True

        except Exception as e:
            logging.error(f"Failed to save project {self.id}: {e}")
            return False

    def load(self) -> bool:
        """加载项目"""
        try:
            project_file = os.path.join(self.path, 'project.json')
            if not os.path.exists(project_file):
                return False

            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # 加载元数据
            self.metadata = ProjectMetadata.from_dict(project_data['metadata'])

            # 加载设置
            settings_data = project_data.get('settings', {})
            self.settings = ProjectSettings(**settings_data)

            # 加载媒体文件
            self.media_files.clear()
            for media_id, media_data in project_data.get('media_files', {}).items():
                self.media_files[media_id] = ProjectMedia.from_dict(media_data)

            # 加载时间线
            timeline_data = project_data.get('timeline', {})
            self.timeline = ProjectTimeline.from_dict(timeline_data)

            self.is_loaded = True
            self.is_modified = False
            return True

        except Exception as e:
            logging.error(f"Failed to load project {self.id}: {e}")
            return False

    def create_backup(self) -> Optional[str]:
        """创建项目备份"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
            backup_path = os.path.join(self.path, 'backups', backup_name)

            os.makedirs(backup_path, exist_ok=True)

            # 复制项目文件
            shutil.copy2(os.path.join(self.path, 'project.json'),
                        os.path.join(backup_path, 'project.json'))

            # 创建备份信息文件
            backup_info = {
                'timestamp': timestamp,
                'created_at': datetime.now().isoformat(),
                'project_version': self.metadata.version,
                'description': f"自动备份 - {timestamp}"
            }

            with open(os.path.join(backup_path, 'backup_info.json'), 'w') as f:
                json.dump(backup_info, f, indent=2)

            return backup_path

        except Exception as e:
            logging.error(f"Failed to create backup for project {self.id}: {e}")
            return None

    def cleanup_old_backups(self, keep_count: int = 10) -> None:
        """清理旧备份"""
        try:
            backup_dir = os.path.join(self.path, 'backups')
            if not os.path.exists(backup_dir):
                return

            backups = []
            for backup_name in os.listdir(backup_dir):
                backup_path = os.path.join(backup_dir, backup_name)
                if os.path.isdir(backup_path):
                    backup_info_file = os.path.join(backup_path, 'backup_info.json')
                    if os.path.exists(backup_info_file):
                        with open(backup_info_file, 'r') as f:
                            backup_info = json.load(f)
                            backups.append((backup_path, backup_info['timestamp']))

            # 按时间戳排序，保留最新的keep_count个备份
            backups.sort(key=lambda x: x[1], reverse=True)
            for backup_path, _ in backups[keep_count:]:
                shutil.rmtree(backup_path)

        except Exception as e:
            logging.error(f"Failed to cleanup backups for project {self.id}: {e}")


class ProjectManager(QObject):
    """项目管理器"""

    # 信号定义
    project_created = Signal(str)           # 项目创建信号
    project_opened = Signal(str)            # 项目打开信号
    project_saved = Signal(str)             # 项目保存信号
    project_closed = Signal(str)            # 项目关闭信号
    project_deleted = Signal(str)           # 项目删除信号
    project_imported = Signal(str)          # 项目导入信号
    project_exported = Signal(str)          # 项目导出信号
    recent_projects_updated = Signal(list)  # 最近项目更新信号
    error_occurred = Signal(str, str)       # 错误发生信号

    def __init__(self, config_manager: ConfigManager):
        super().__init__()

        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.secure_key_manager = get_secure_key_manager()

        # 项目存储
        self.projects: Dict[str, Project] = {}
        self.current_project: Optional[Project] = None
        self.templates: Dict[str, Project] = {}

        # 项目目录
        self.projects_dir = os.path.expanduser("~/Voxplore/Projects")
        self.templates_dir = os.path.expanduser("~/Voxplore/Templates")
        self.temp_dir = os.path.expanduser("~/Voxplore/Temp")

        # 确保目录存在
        self._ensure_directories()

        # 加载最近项目
        self.recent_projects: List[str] = self._load_recent_projects()

        # 加载项目模板
        self._load_templates()

        # 设置自动保存
        self._setup_auto_save()

    def _ensure_directories(self) -> None:
        """确保所需目录存在"""
        for directory in [self.projects_dir, self.templates_dir, self.temp_dir]:
            os.makedirs(directory, exist_ok=True)

    def _load_recent_projects(self) -> List[str]:
        """加载最近项目列表"""
        return self.config_manager.get('editor.recent_files', [])

    def _save_recent_projects(self) -> None:
        """保存最近项目列表"""
        self.config_manager.set('editor.recent_files', self.recent_projects[:10])
        self.recent_projects_updated.emit(self.recent_projects[:10])

    def _add_to_recent_projects(self, project_path: str) -> None:
        """添加项目到最近列表"""
        if project_path in self.recent_projects:
            self.recent_projects.remove(project_path)
        self.recent_projects.insert(0, project_path)
        self._save_recent_projects()

    def _setup_auto_save(self) -> None:
        """设置自动保存"""
        from PySide6.QtCore import QTimer

        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_timer.start(60000)  # 每分钟检查一次

    def _auto_save(self) -> None:
        """自动保存当前项目"""
        if self.current_project and self.current_project.is_modified:
            auto_save_interval = self.current_project.settings.auto_save_interval
            if auto_save_interval > 0:
                # 检查是否需要自动保存
                time_since_last_save = (datetime.now() - self.current_project.metadata.modified_at).total_seconds()
                if time_since_last_save >= auto_save_interval:
                    self.save_project(self.current_project.id, auto_save=True)

    def create_project(self, name: str, project_type: ProjectType = ProjectType.VIDEO_EDITING,
                     description: str = "", template_id: Optional[str] = None) -> Optional[str]:
        """创建新项目"""
        try:
            # 生成项目ID和路径
            project_id = str(uuid.uuid4())
            project_path = os.path.join(self.projects_dir, f"{name}_{project_id[:8]}")

            # 创建项目目录
            os.makedirs(project_path, exist_ok=True)

            # 创建子目录
            subdirs = ['media', 'exports', 'backups', 'cache', 'assets']
            for subdir in subdirs:
                os.makedirs(os.path.join(project_path, subdir), exist_ok=True)

            # 创建项目元数据
            metadata = ProjectMetadata(
                name=name,
                description=description,
                project_type=project_type,
                author=os.getlogin()
            )

            # 创建项目对象
            project = Project(project_id, project_path, metadata)

            # 如果使用模板，复制模板设置
            if template_id and template_id in self.templates:
                template = self.templates[template_id]
                project.settings = template.settings
                project.timeline = template.timeline

            # 保存项目
            if project.save():
                self.projects[project_id] = project
                self.current_project = project
                self._add_to_recent_projects(project_path)

                self.project_created.emit(project_id)
                self.logger.info(f"Created project: {name} ({project_id})")
                return project_id

            # 如果保存失败，删除项目目录
            shutil.rmtree(project_path)
            return None

        except Exception as e:
            self.logger.error(f"Failed to create project {name}: {e}")
            self.error_occurred.emit("CREATE_ERROR", f"创建项目失败: {str(e)}")
            return None

    def open_project(self, project_path: str) -> Optional[str]:
        """打开项目"""
        try:
            # 检查项目文件是否存在
            project_file = os.path.join(project_path, 'project.json')
            if not os.path.exists(project_file):
                self.error_occurred.emit("OPEN_ERROR", f"项目文件不存在: {project_path}")
                return None

            # 检查项目锁
            lock_file = os.path.join(project_path, '.lock')
            if os.path.exists(lock_file):
                with open(lock_file, 'r') as f:
                    pid = f.read().strip()
                # 检查进程是否还在运行
                if self._is_process_running(pid):
                    self.error_occurred.emit("OPEN_ERROR", "项目已被其他进程打开")
                    return None

            # 加载项目数据
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # 创建项目元数据
            metadata = ProjectMetadata.from_dict(project_data['metadata'])

            # 创建项目对象
            project = Project(metadata.name, project_path, metadata)

            # 加载项目
            if project.load():
                self.projects[project.id] = project
                self.current_project = project
                self._add_to_recent_projects(project_path)

                # 创建项目锁
                with open(lock_file, 'w') as f:
                    f.write(str(os.getpid()))

                self.project_opened.emit(project.id)
                self.logger.info(f"Opened project: {metadata.name} ({project.id})")
                return project.id

            return None

        except Exception as e:
            self.logger.error(f"Failed to open project {project_path}: {e}")
            self.error_occurred.emit("OPEN_ERROR", f"打开项目失败: {str(e)}")
            return None

    def save_project(self, project_id: str, auto_save: bool = False) -> bool:
        """保存项目"""
        try:
            if project_id not in self.projects:
                return False

            project = self.projects[project_id]

            # 创建备份（如果需要）
            if project.settings.backup_enabled and not auto_save:
                backup_path = project.create_backup()
                if backup_path:
                    project.cleanup_old_backups(project.settings.backup_count)

            # 保存项目
            if project.save():
                self.project_saved.emit(project_id)
                if not auto_save:
                    self.logger.info(f"Saved project: {project.metadata.name} ({project_id})")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to save project {project_id}: {e}")
            self.error_occurred.emit("SAVE_ERROR", f"保存项目失败: {str(e)}")
            return False

    def close_project(self, project_id: str) -> bool:
        """关闭项目"""
        try:
            if project_id not in self.projects:
                return False

            project = self.projects[project_id]

            # 如果项目已修改，询问是否保存
            if project.is_modified:
                # 这里应该显示对话框询问用户
                # 为了简化，我们直接保存
                self.save_project(project_id)

            # 删除项目锁
            lock_file = os.path.join(project.path, '.lock')
            if os.path.exists(lock_file):
                os.remove(lock_file)

            # 如果是当前项目，清除当前项目
            if self.current_project and self.current_project.id == project_id:
                self.current_project = None

            self.project_closed.emit(project_id)
            self.logger.info(f"Closed project: {project.metadata.name} ({project_id})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to close project {project_id}: {e}")
            self.error_occurred.emit("CLOSE_ERROR", f"关闭项目失败: {str(e)}")
            return False

    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        try:
            if project_id not in self.projects:
                return False

            project = self.projects[project_id]

            # 关闭项目
            self.close_project(project_id)

            # 删除项目目录
            if os.path.exists(project.path):
                shutil.rmtree(project.path)

            # 从项目列表中移除
            del self.projects[project_id]

            # 从最近项目中移除
            if project.path in self.recent_projects:
                self.recent_projects.remove(project.path)
                self._save_recent_projects()

            self.project_deleted.emit(project_id)
            self.logger.info(f"Deleted project: {project.metadata.name} ({project_id})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete project {project_id}: {e}")
            self.error_occurred.emit("DELETE_ERROR", f"删除项目失败: {str(e)}")
            return False

    def export_project(self, project_id: str, export_path: str,
                     include_media: bool = True) -> bool:
        """导出项目"""
        try:
            if project_id not in self.projects:
                return False

            project = self.projects[project_id]

            # 创建ZIP文件
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 添加项目文件
                project_file = os.path.join(project.path, 'project.json')
                if os.path.exists(project_file):
                    zipf.write(project_file, 'project.json')

                # 添加媒体文件（如果需要）
                if include_media:
                    media_dir = os.path.join(project.path, 'media')
                    if os.path.exists(media_dir):
                        for root, dirs, files in os.walk(media_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, project.path)
                                zipf.write(file_path, arcname)

                # 添加导出信息
                export_info = {
                    'exported_at': datetime.now().isoformat(),
                    'project_version': project.metadata.version,
                    'cineai_version': '2.0.0',
                    'include_media': include_media
                }

                zipf.writestr('export_info.json', json.dumps(export_info, indent=2))

            self.project_exported.emit(project_id)
            self.logger.info(f"Exported project: {project.metadata.name} to {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export project {project_id}: {e}")
            self.error_occurred.emit("EXPORT_ERROR", f"导出项目失败: {str(e)}")
            return False

    def import_project(self, import_path: str) -> Optional[str]:
        """导入项目"""
        try:
            # 创建临时目录
            temp_dir = os.path.join(self.temp_dir, f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(temp_dir, exist_ok=True)

            # 解压ZIP文件
            with zipfile.ZipFile(import_path, 'r') as zipf:
                zipf.extractall(temp_dir)

            # 检查项目文件
            project_file = os.path.join(temp_dir, 'project.json')
            if not os.path.exists(project_file):
                self.error_occurred.emit("IMPORT_ERROR", "无效的项目文件")
                return None

            # 加载项目数据
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # 创建项目目录
            metadata = ProjectMetadata.from_dict(project_data['metadata'])
            project_name = f"{metadata.name}_imported"
            project_path = os.path.join(self.projects_dir, f"{project_name}_{uuid.uuid4().hex[:8]}")

            # 复制项目文件
            shutil.copytree(temp_dir, project_path)

            # 更新项目路径
            project_file = os.path.join(project_path, 'project.json')
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            project_data['metadata']['name'] = project_name
            project_data['metadata']['modified_at'] = datetime.now().isoformat()

            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)

            # 清理临时目录
            shutil.rmtree(temp_dir)

            # 打开项目
            project_id = self.open_project(project_path)
            if project_id:
                self.project_imported.emit(project_id)
                self.logger.info(f"Imported project: {project_name} from {import_path}")
                return project_id

            return None

        except Exception as e:
            self.logger.error(f"Failed to import project from {import_path}: {e}")
            self.error_occurred.emit("IMPORT_ERROR", f"导入项目失败: {str(e)}")
            return None

    def get_project(self, project_id: str) -> Optional[Project]:
        """获取项目"""
        return self.projects.get(project_id)

    def get_current_project(self) -> Optional[Project]:
        """获取当前项目"""
        return self.current_project

    def get_all_projects(self) -> List[Project]:
        """获取所有项目"""
        return list(self.projects.values())

    def get_recent_projects(self) -> List[str]:
        """获取最近项目列表"""
        return self.recent_projects.copy()

    def scan_projects(self) -> List[Project]:
        """扫描项目目录，发现所有项目"""
        discovered_projects = []

        try:
            for project_dir in os.listdir(self.projects_dir):
                project_path = os.path.join(self.projects_dir, project_dir)
                if os.path.isdir(project_path):
                    project_file = os.path.join(project_path, 'project.json')
                    if os.path.exists(project_file):
                        try:
                            with open(project_file, 'r', encoding='utf-8') as f:
                                project_data = json.load(f)

                            metadata = ProjectMetadata.from_dict(project_data['metadata'])
                            project = Project(metadata.name, project_path, metadata)
                            discovered_projects.append(project)

                        except Exception as e:
                            self.logger.warning(f"Failed to load project from {project_path}: {e}")

            return discovered_projects

        except Exception as e:
            self.logger.error(f"Failed to scan projects: {e}")
            return []

    def _load_templates(self) -> None:
        """加载项目模板"""
        try:
            if not os.path.exists(self.templates_dir):
                return

            for template_dir in os.listdir(self.templates_dir):
                template_path = os.path.join(self.templates_dir, template_dir)
                if os.path.isdir(template_path):
                    template_file = os.path.join(template_path, 'project.json')
                    if os.path.exists(template_file):
                        try:
                            with open(template_file, 'r', encoding='utf-8') as f:
                                template_data = json.load(f)

                            metadata = ProjectMetadata.from_dict(template_data['metadata'])
                            metadata.status = ProjectStatus.TEMPLATE

                            template = Project(metadata.name, template_path, metadata)
                            template.load()

                            self.templates[template_dir] = template

                        except Exception as e:
                            self.logger.warning(f"Failed to load template {template_dir}: {e}")

            self.logger.info(f"Loaded {len(self.templates)} templates")

        except Exception as e:
            self.logger.error(f"Failed to load templates: {e}")

    def get_templates(self) -> List[Project]:
        """获取所有模板"""
        return list(self.templates.values())

    def create_template(self, project_id: str, template_name: str) -> bool:
        """从项目创建模板"""
        try:
            if project_id not in self.projects:
                return False

            project = self.projects[project_id]

            # 创建模板目录
            template_path = os.path.join(self.templates_dir, template_name)
            os.makedirs(template_path, exist_ok=True)

            # 复制项目文件
            shutil.copy2(os.path.join(project.path, 'project.json'),
                        os.path.join(template_path, 'project.json'))

            # 更新模板元数据
            template_file = os.path.join(template_path, 'project.json')
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = json.load(f)

            template_data['metadata']['name'] = template_name
            template_data['metadata']['status'] = 'template'
            template_data['metadata']['description'] = f"模板创建自项目: {project.metadata.name}"
            template_data['metadata']['modified_at'] = datetime.now().isoformat()

            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=2, ensure_ascii=False)

            # 重新加载模板
            self._load_templates()

            self.logger.info(f"Created template: {template_name} from project {project_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create template from project {project_id}: {e}")
            return False

    def _is_process_running(self, pid_str: str) -> bool:
        """检查进程是否在运行"""
        try:
            import psutil
            pid = int(pid_str)
            return psutil.pid_exists(pid)
        except (ImportError, ValueError):
            # 如果没有psutil，返回False（假设进程不在运行）
            return False

    def cleanup(self) -> None:
        """清理资源"""
        # 关闭所有项目
        for project_id in list(self.projects.keys()):
            self.close_project(project_id)

        # 停止自动保存定时器
        if hasattr(self, 'auto_save_timer'):
            self.auto_save_timer.stop()

        # 清理临时目录
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temp directory: {e}")