#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目版本管理器
提供项目版本控制、备份和恢复功能
"""

import os
import json
import shutil
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal
from .version_models import ProjectVersion, ProjectBranch


@dataclass
class ProjectVersionManager(QObject):
    """项目版本管理器"""

    # 信号定义
    version_created = Signal(str, str)    # 版本创建信号 (project_id, version_id)
    version_restored = Signal(str, str)   # 版本恢复信号 (project_id, version_id)
    branch_created = Signal(str, str)     # 分支创建信号 (project_id, branch_name)
    branch_switched = Signal(str, str)    # 分支切换信号 (project_id, branch_name)
    error_occurred = Signal(str, str)     # 错误发生信号

    def __init__(self, project_path: str):
        super().__init__()

        self.project_path = project_path
        self.logger = logging.getLogger(__name__)
        self.version_dir = os.path.join(project_path, 'versions')
        self.current_branch = 'main'

        # 确保版本目录存在
        os.makedirs(self.version_dir, exist_ok=True)

        # 加载版本信息
        self.versions: Dict[str, ProjectVersion] = {}
        self.branches: Dict[str, ProjectBranch] = {}
        self._load_version_info()

    def _load_version_info(self) -> None:
        """加载版本信息"""
        try:
            # 加载版本信息
            versions_file = os.path.join(self.version_dir, 'versions.json')
            if os.path.exists(versions_file):
                with open(versions_file, 'r', encoding='utf-8') as f:
                    versions_data = json.load(f)
                    for version_id, version_data in versions_data.items():
                        self.versions[version_id] = ProjectVersion.from_dict(version_data)

            # 加载分支信息
            branches_file = os.path.join(self.version_dir, 'branches.json')
            if os.path.exists(branches_file):
                with open(branches_file, 'r', encoding='utf-8') as f:
                    branches_data = json.load(f)
                    for branch_name, branch_data in branches_data.items():
                        self.branches[branch_name] = ProjectBranch.from_dict(branch_data)

            # 确保主分支存在
            if 'main' not in self.branches:
                self._create_main_branch()

        except Exception as e:
            self.logger.error(f"Failed to load version info: {e}")

    def _create_main_branch(self) -> None:
        """创建主分支"""
        main_branch = ProjectBranch(
            name='main',
            created_at=datetime.now(),
            description='主分支',
            is_active=True
        )
        self.branches['main'] = main_branch
        self._save_branch_info()

    def _save_version_info(self) -> None:
        """保存版本信息"""
        try:
            versions_file = os.path.join(self.version_dir, 'versions.json')
            versions_data = {vid: v.to_dict() for vid, v in self.versions.items()}
            with open(versions_file, 'w', encoding='utf-8') as f:
                json.dump(versions_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save version info: {e}")

    def _save_branch_info(self) -> None:
        """保存分支信息"""
        try:
            branches_file = os.path.join(self.version_dir, 'branches.json')
            branches_data = {name: b.to_dict() for name, b in self.branches.items()}
            with open(branches_file, 'w', encoding='utf-8') as f:
                json.dump(branches_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save branch info: {e}")

    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to calculate file hash: {e}")
            return ""

    def _copy_project_files(self, source_path: str, dest_path: str) -> bool:
        """复制项目文件"""
        try:
            # 确保目标目录存在
            os.makedirs(dest_path, exist_ok=True)

            # 复制项目文件
            project_file = os.path.join(source_path, 'project.json')
            if os.path.exists(project_file):
                shutil.copy2(project_file, os.path.join(dest_path, 'project.json'))

            # 复制媒体目录
            media_source = os.path.join(source_path, 'media')
            if os.path.exists(media_source):
                media_dest = os.path.join(dest_path, 'media')
                shutil.copytree(media_source, media_dest, dirs_exist_ok=True)

            # 复制资产目录
            assets_source = os.path.join(source_path, 'assets')
            if os.path.exists(assets_source):
                assets_dest = os.path.join(dest_path, 'assets')
                shutil.copytree(assets_source, assets_dest, dirs_exist_ok=True)

            return True

        except Exception as e:
            self.logger.error(f"Failed to copy project files: {e}")
            return False

    def create_version(self, description: str, changes: List[str],
                      tags: List[str] = None, is_major: bool = False,
                      is_auto_backup: bool = False) -> Optional[str]:
        """创建新版本"""
        try:
            # 生成版本ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version_id = f"v_{timestamp}"

            # 计算项目文件哈希
            project_file = os.path.join(self.project_path, 'project.json')
            file_hash = self._calculate_file_hash(project_file)

            # 获取文件大小
            file_size = os.path.getsize(project_file) if os.path.exists(project_file) else 0

            # 创建版本信息
            version = ProjectVersion(
                version_id=version_id,
                timestamp=datetime.now(),
                description=description,
                changes=changes,
                file_hash=file_hash,
                size=file_size,
                tags=tags or [],
                is_auto_backup=is_auto_backup,
                is_major=is_major
            )

            # 创建版本目录
            version_path = os.path.join(self.version_dir, version_id)
            os.makedirs(version_path, exist_ok=True)

            # 复制项目文件
            if self._copy_project_files(self.project_path, version_path):
                # 保存版本信息
                self.versions[version_id] = version
                self._save_version_info()

                # 添加到当前分支
                if self.current_branch in self.branches:
                    self.branches[self.current_branch].versions.append(version_id)
                    self._save_branch_info()

                self.logger.info(f"Created version: {version_id}")
                return version_id

            return None

        except Exception as e:
            self.logger.error(f"Failed to create version: {e}")
            self.error_occurred.emit("VERSION_ERROR", f"创建版本失败: {str(e)}")
            return None

    def restore_version(self, version_id: str) -> bool:
        """恢复到指定版本"""
        try:
            if version_id not in self.versions:
                self.error_occurred.emit("VERSION_ERROR", f"版本不存在: {version_id}")
                return False

            _version = self.versions[version_id]
            version_path = os.path.join(self.version_dir, version_id)

            if not os.path.exists(version_path):
                self.error_occurred.emit("VERSION_ERROR", f"版本文件不存在: {version_id}")
                return False

            # 创建当前版本的备份
            _backup_version_id = self.create_version(
                description=f"恢复前备份 - {version_id}",
                changes=["自动创建恢复前备份"],
                is_auto_backup=True
            )

            # 恢复文件
            if self._copy_project_files(version_path, self.project_path):
                self.logger.info(f"Restored to version: {version_id}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to restore version {version_id}: {e}")
            self.error_occurred.emit("VERSION_ERROR", f"恢复版本失败: {str(e)}")
            return False

    def delete_version(self, version_id: str) -> bool:
        """删除版本"""
        try:
            if version_id not in self.versions:
                return False

            # 从所有分支中移除
            for branch in self.branches.values():
                if version_id in branch.versions:
                    branch.versions.remove(version_id)

            # 删除版本目录
            version_path = os.path.join(self.version_dir, version_id)
            if os.path.exists(version_path):
                shutil.rmtree(version_path)

            # 删除版本信息
            del self.versions[version_id]
            self._save_version_info()
            self._save_branch_info()

            self.logger.info(f"Deleted version: {version_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete version {version_id}: {e}")
            return False

    def get_version(self, version_id: str) -> Optional[ProjectVersion]:
        """获取版本信息"""
        return self.versions.get(version_id)

    def get_all_versions(self) -> List[ProjectVersion]:
        """获取所有版本"""
        return sorted(self.versions.values(), key=lambda v: v.timestamp, reverse=True)

    def get_versions_by_branch(self, branch_name: str) -> List[ProjectVersion]:
        """获取指定分支的版本"""
        if branch_name not in self.branches:
            return []

        branch = self.branches[branch_name]
        versions = []
        for version_id in branch.versions:
            if version_id in self.versions:
                versions.append(self.versions[version_id])

        return sorted(versions, key=lambda v: v.timestamp, reverse=True)

    def create_branch(self, branch_name: str, description: str,
                     parent_branch: str = None) -> bool:
        """创建新分支"""
        try:
            if branch_name in self.branches:
                self.error_occurred.emit("BRANCH_ERROR", f"分支已存在: {branch_name}")
                return False

            # 创建分支
            branch = ProjectBranch(
                name=branch_name,
                created_at=datetime.now(),
                description=description,
                parent_branch=parent_branch or self.current_branch
            )

            self.branches[branch_name] = branch
            self._save_branch_info()

            self.logger.info(f"Created branch: {branch_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create branch {branch_name}: {e}")
            self.error_occurred.emit("BRANCH_ERROR", f"创建分支失败: {str(e)}")
            return False

    def switch_branch(self, branch_name: str) -> bool:
        """切换分支"""
        try:
            if branch_name not in self.branches:
                self.error_occurred.emit("BRANCH_ERROR", f"分支不存在: {branch_name}")
                return False

            # 保存当前项目状态到当前分支
            _current_backup = self.create_version(
                description="切换分支前备份",
                changes=["自动创建分支切换备份"],
                is_auto_backup=True
            )

            # 切换分支
            self.current_branch = branch_name

            # 如果目标分支有版本，恢复到最新版本
            branch = self.branches[branch_name]
            if branch.versions:
                latest_version_id = branch.versions[-1]
                self.restore_version(latest_version_id)

            self.logger.info(f"Switched to branch: {branch_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to switch to branch {branch_name}: {e}")
            self.error_occurred.emit("BRANCH_ERROR", f"切换分支失败: {str(e)}")
            return False

    def delete_branch(self, branch_name: str) -> bool:
        """删除分支"""
        try:
            if branch_name == 'main':
                self.error_occurred.emit("BRANCH_ERROR", "不能删除主分支")
                return False

            if branch_name not in self.branches:
                return False

            # 如果是当前分支，切换到主分支
            if self.current_branch == branch_name:
                self.switch_branch('main')

            # 删除分支
            del self.branches[branch_name]
            self._save_branch_info()

            self.logger.info(f"Deleted branch: {branch_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete branch {branch_name}: {e}")
            return False

    def get_branch(self, branch_name: str) -> Optional[ProjectBranch]:
        """获取分支信息"""
        return self.branches.get(branch_name)

    def get_all_branches(self) -> List[ProjectBranch]:
        """获取所有分支"""
        return list(self.branches.values())

    def get_current_branch(self) -> Optional[ProjectBranch]:
        """获取当前分支"""
        return self.branches.get(self.current_branch)

    def get_version_diff(self, version_id1: str, version_id2: str) -> Dict[str, Any]:
        """获取版本差异"""
        try:
            if version_id1 not in self.versions or version_id2 not in self.versions:
                return {}

            version1 = self.versions[version_id1]
            version2 = self.versions[version_id2]

            diff = {
                'version1': version1.to_dict(),
                'version2': version2.to_dict(),
                'time_diff': (version2.timestamp - version1.timestamp).total_seconds(),
                'size_diff': version2.size - version1.size,
                'hash_changed': version1.file_hash != version2.file_hash
            }

            return diff

        except Exception as e:
            self.logger.error(f"Failed to get version diff: {e}")
            return {}

    def cleanup_old_versions(self, keep_count: int = 50) -> int:
        """清理旧版本"""
        try:
            all_versions = sorted(self.versions.values(), key=lambda v: v.timestamp)
            deleted_count = 0

            # 保留主要版本和最近的版本
            _major_versions = [_v for _v in all_versions if _v.is_major]
            recent_versions = all_versions[-keep_count:]

            # 确定要删除的版本
            versions_to_delete = []
            for version in all_versions:
                if not version.is_major and version not in recent_versions:
                    versions_to_delete.append(version)

            # 删除版本
            for version in versions_to_delete:
                if self.delete_version(version.version_id):
                    deleted_count += 1

            self.logger.info(f"Cleaned up {deleted_count} old versions")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to cleanup old versions: {e}")
            return 0

    def export_version(self, version_id: str, export_path: str) -> bool:
        """导出版本"""
        try:
            if version_id not in self.versions:
                return False

            _version = self.versions[version_id]
            version_path = os.path.join(self.version_dir, version_id)

            if not os.path.exists(version_path):
                return False

            # 创建导出信息
            export_info = {
                'version': _version.to_dict(),
                'exported_at': datetime.now().isoformat(),
                'project_path': self.project_path
            }

            # 保存导出信息
            info_file = os.path.join(version_path, 'export_info.json')
            with open(info_file, 'w') as f:
                json.dump(export_info, f, indent=2)

            # 复制到导出路径
            shutil.copytree(version_path, export_path)

            self.logger.info(f"Exported version: {version_id} to {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export version {version_id}: {e}")
            return False

    def import_version(self, import_path: str, description: str = "") -> Optional[str]:
        """导入版本"""
        try:
            # 检查导入信息
            info_file = os.path.join(import_path, 'export_info.json')
            if not os.path.exists(info_file):
                return None

            with open(info_file, 'r') as f:
                import_info = json.load(f)

            version_data = import_info['version']
            version_data['description'] = description or f"导入版本 - {version_data['description']}"

            # 生成新版本ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version_id = f"imported_{timestamp}"

            # 创建版本目录
            version_path = os.path.join(self.version_dir, version_id)
            os.makedirs(version_path, exist_ok=True)

            # 复制版本文件
            shutil.copytree(import_path, version_path, dirs_exist_ok=True)

            # 创建版本信息
            version = ProjectVersion.from_dict(version_data)
            version.version_id = version_id

            self.versions[version_id] = version
            self._save_version_info()

            # 添加到当前分支
            if self.current_branch in self.branches:
                self.branches[self.current_branch].versions.append(version_id)
                self._save_branch_info()

            self.logger.info(f"Imported version: {version_id}")
            return version_id

        except Exception as e:
            self.logger.error(f"Failed to import version from {import_path}: {e}")
            return None

    def get_version_statistics(self) -> Dict[str, Any]:
        """获取版本统计信息"""
        try:
            total_versions = len(self.versions)
            total_branches = len(self.branches)
            total_size = sum(v.size for v in self.versions.values())

            # 版本类型统计
            major_versions = sum(1 for v in self.versions.values() if v.is_major)
            auto_backups = sum(1 for v in self.versions.values() if v.is_auto_backup)

            # 时间统计
            if self.versions:
                oldest_version = min(self.versions.values(), key=lambda v: v.timestamp)
                newest_version = max(self.versions.values(), key=lambda v: v.timestamp)
                time_span = (newest_version.timestamp - oldest_version.timestamp).days
            else:
                time_span = 0

            return {
                'total_versions': total_versions,
                'total_branches': total_branches,
                'total_size_mb': total_size / (1024 * 1024),
                'major_versions': major_versions,
                'auto_backups': auto_backups,
                'time_span_days': time_span,
                'current_branch': self.current_branch
            }

        except Exception as e:
            self.logger.error(f"Failed to get version statistics: {e}")
            return {}

    def compact_versions(self) -> bool:
        """压缩版本存储"""
        try:
            # 删除空目录
            for version_id in list(self.versions.keys()):
                version_path = os.path.join(self.version_dir, version_id)
                if not os.path.exists(version_path):
                    del self.versions[version_id]
                    self._save_version_info()

            # 清理分支中不存在的版本
            for branch in self.branches.values():
                branch.versions = [v for v in branch.versions if v in self.versions]

            self._save_branch_info()
            self.logger.info("Version storage compacted")
            return True

        except Exception as e:
            self.logger.error(f"Failed to compact versions: {e}")
            return False