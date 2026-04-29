#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目设置管理器
提供项目设置的统一管理和配置功能
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict
from pathlib import Path
import logging

from PySide6.QtCore import QObject, Signal

from .config_manager import ConfigManager
from .secure_key_manager import get_secure_key_manager
from .settings_types import SettingType, SettingDefinition, ProjectSettingsProfile
from .settings_data import get_all_settings_definitions


class ProjectSettingsManager(QObject):
    """项目设置管理器"""

    # 信号定义
    settings_changed = Signal(str, object)  # 设置变更信号
    profile_created = Signal(str)            # 配置文件创建信号
    profile_applied = Signal(str)            # 配置文件应用信号
    settings_reset = Signal()               # 设置重置信号
    error_occurred = Signal(str, str)       # 错误发生信号

    def __init__(self, config_manager: ConfigManager):
        super().__init__()

        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.secure_key_manager = get_secure_key_manager()

        # 设置存储
        self.settings: Dict[str, Any] = {}
        self.settings_definitions: Dict[str, SettingDefinition] = {}
        self.profiles: Dict[str, ProjectSettingsProfile] = {}

        # 设置文件路径
        self.settings_file = os.path.expanduser("~/Voxplore/settings/project_settings.json")
        self.profiles_file = os.path.expanduser("~/Voxplore/settings/profiles.json")

        # 初始化
        self._init_settings_definitions()
        self._load_settings()
        self._load_profiles()


    def _init_settings_definitions(self) -> None:
        """初始化设置定义"""
        # 从 settings_data 模块加载所有设置定义
        self.settings_definitions.update(get_all_settings_definitions())

    def _load_settings(self) -> None:
        """加载设置"""
        try:
            # 首先设置默认值
            for key, definition in self.settings_definitions.items():
                self.settings[key] = definition.default_value

            # 从文件加载设置
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    self._update_settings(loaded_settings)

            self.logger.info("Project settings loaded successfully")

        except Exception as e:
            self.logger.error(f"Failed to load settings: {e}")

    def _load_profiles(self) -> None:
        """加载配置文件"""
        try:
            if os.path.exists(self.profiles_file):
                with open(self.profiles_file, 'r', encoding='utf-8') as f:
                    profiles_data = json.load(f)
                    for name, profile_data in profiles_data.items():
                        profile = ProjectSettingsProfile(**profile_data)
                        self.profiles[name] = profile

            # 创建默认配置文件
            self._create_default_profiles()

            self.logger.info("Project profiles loaded successfully")

        except Exception as e:
            self.logger.error(f"Failed to load profiles: {e}")

    def _create_default_profiles(self) -> None:
        """创建默认配置文件"""
        default_profiles = [
            ProjectSettingsProfile(
                name="高性能",
                description="针对高性能设备的优化配置",
                settings={
                    'performance.enable_gpu': True,
                    'performance.memory_limit': 8192,
                    'performance.thread_count': 8,
                    'video.resolution': '3840x2160',
                    'video.bitrate': '16000k',
                    'audio.sample_rate': 48000,
                    'audio.bitrate': '320k'
                },
                created_at=datetime.now().isoformat(),
                modified_at=datetime.now().isoformat(),
                tags=['性能', '高质量'],
                is_builtin=True
            ),
            ProjectSettingsProfile(
                name="标准配置",
                description="平衡性能和质量的标准配置",
                settings={
                    'performance.enable_gpu': True,
                    'performance.memory_limit': 4096,
                    'performance.thread_count': 4,
                    'video.resolution': '1920x1080',
                    'video.bitrate': '8000k',
                    'audio.sample_rate': 44100,
                    'audio.bitrate': '192k'
                },
                created_at=datetime.now().isoformat(),
                modified_at=datetime.now().isoformat(),
                tags=['标准', '平衡'],
                is_builtin=True
            ),
            ProjectSettingsProfile(
                name="节省资源",
                description="针对低性能设备的优化配置",
                settings={
                    'performance.enable_gpu': False,
                    'performance.memory_limit': 2048,
                    'performance.thread_count': 2,
                    'video.resolution': '1280x720',
                    'video.bitrate': '4000k',
                    'audio.sample_rate': 44100,
                    'audio.bitrate': '128k'
                },
                created_at=datetime.now().isoformat(),
                modified_at=datetime.now().isoformat(),
                tags=['省资源', '兼容'],
                is_builtin=True
            )
        ]

        for profile in default_profiles:
            if profile.name not in self.profiles:
                self.profiles[profile.name] = profile

    def _update_settings(self, new_settings: Dict[str, Any]) -> None:
        """更新设置"""
        for key, value in new_settings.items():
            if key in self.settings_definitions:
                if self._validate_setting(key, value):
                    self.settings[key] = value
                else:
                    self.logger.warning(f"Invalid value for setting {key}: {value}")

    def _validate_setting(self, key: str, value: Any) -> bool:
        """验证设置值"""
        if key not in self.settings_definitions:
            return False

        definition = self.settings_definitions[key]

        # 类型检查
        try:
            if definition.setting_type == SettingType.STRING:
                if not isinstance(value, str):
                    return False
            elif definition.setting_type == SettingType.INTEGER:
                if not isinstance(value, int):
                    return False
            elif definition.setting_type == SettingType.FLOAT:
                if not isinstance(value, (int, float)):
                    return False
            elif definition.setting_type == SettingType.BOOLEAN:
                if not isinstance(value, bool):
                    return False
            elif definition.setting_type == SettingType.LIST:
                if not isinstance(value, list):
                    return False
            elif definition.setting_type == SettingType.DICT:
                if not isinstance(value, dict):
                    return False
        except Exception as e:
            self.logger.debug(f"Setting validation error: {e}")
            return False

        # 范围检查
        if definition.min_value is not None:
            if value < definition.min_value:
                return False

        if definition.max_value is not None:
            if value > definition.max_value:
                return False

        # 选项检查
        if definition.options:
            if value not in definition.options:
                return False

        # 自定义验证
        if definition.validator:
            try:
                validator_func = getattr(self, definition.validator)
                if not validator_func(value):
                    return False
            except Exception as e:
                self.logger.debug(f"Validator error for {definition.key}: {e}")
                return False

        return True

    def get_setting(self, key: str, default: Any = None) -> Any:
        """获取设置值"""
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> bool:
        """设置值"""
        if key not in self.settings_definitions:
            self.error_occurred.emit("SETTING_ERROR", f"未知的设置项: {key}")
            return False

        if not self._validate_setting(key, value):
            self.error_occurred.emit("SETTING_ERROR", f"无效的设置值: {value}")
            return False

        old_value = self.settings.get(key)
        if old_value != value:
            self.settings[key] = value
            self.settings_changed.emit(key, value)
            self._save_settings()

        return True

    def get_settings_by_category(self, category: str) -> Dict[str, Any]:
        """按类别获取设置"""
        category_settings = {}
        for key, definition in self.settings_definitions.items():
            if definition.category == category:
                category_settings[key] = {
                    'value': self.settings.get(key, definition.default_value),
                    'definition': definition
                }
        return category_settings

    def get_all_settings(self) -> Dict[str, Any]:
        """获取所有设置"""
        return self.settings.copy()

    def reset_settings(self) -> None:
        """重置设置为默认值"""
        for key, definition in self.settings_definitions.items():
            self.settings[key] = definition.default_value

        self._save_settings()
        self.settings_reset.emit()
        self.logger.info("Settings reset to defaults")

    def reset_setting(self, key: str) -> bool:
        """重置单个设置为默认值"""
        if key not in self.settings_definitions:
            return False

        default_value = self.settings_definitions[key].default_value
        return self.set_setting(key, default_value)

    def _save_settings(self) -> None:
        """保存设置"""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")

    def create_profile(self, name: str, description: str,
                     settings_filter: List[str] = None) -> bool:
        """创建配置文件"""
        try:
            if name in self.profiles and not self.profiles[name].is_builtin:
                self.error_occurred.emit("PROFILE_ERROR", f"配置文件已存在: {name}")
                return False

            # 确定要包含的设置
            if settings_filter:
                profile_settings = {k: v for k, v in self.settings.items() if k in settings_filter}
            else:
                profile_settings = self.settings.copy()

            profile = ProjectSettingsProfile(
                name=name,
                description=description,
                settings=profile_settings,
                created_at=datetime.now().isoformat(),
                modified_at=datetime.now().isoformat()
            )

            self.profiles[name] = profile
            self._save_profiles()

            self.profile_created.emit(name)
            self.logger.info(f"Created profile: {name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create profile {name}: {e}")
            return False

    def apply_profile(self, profile_name: str) -> bool:
        """应用配置文件"""
        try:
            if profile_name not in self.profiles:
                self.error_occurred.emit("PROFILE_ERROR", f"配置文件不存在: {profile_name}")
                return False

            profile = self.profiles[profile_name]
            changes_made = []

            for key, value in profile.settings.items():
                if key in self.settings_definitions:
                    if self._validate_setting(key, value):
                        old_value = self.settings.get(key)
                        if old_value != value:
                            self.settings[key] = value
                            changes_made.append((key, old_value, value))

            if changes_made:
                self._save_settings()
                for key, _old_value, new_value in changes_made:
                    self.settings_changed.emit(key, new_value)

            self.profile_applied.emit(profile_name)
            self.logger.info(f"Applied profile: {profile_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to apply profile {profile_name}: {e}")
            return False

    def delete_profile(self, profile_name: str) -> bool:
        """删除配置文件"""
        try:
            if profile_name not in self.profiles:
                return False

            profile = self.profiles[profile_name]

            # 不能删除内置配置文件
            if profile.is_builtin:
                self.error_occurred.emit("PROFILE_ERROR", "不能删除内置配置文件")
                return False

            del self.profiles[profile_name]
            self._save_profiles()

            self.logger.info(f"Deleted profile: {profile_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete profile {profile_name}: {e}")
            return False

    def get_profile(self, profile_name: str) -> Optional[ProjectSettingsProfile]:
        """获取配置文件"""
        return self.profiles.get(profile_name)

    def get_all_profiles(self) -> List[ProjectSettingsProfile]:
        """获取所有配置文件"""
        return list(self.profiles.values())

    def get_builtin_profiles(self) -> List[ProjectSettingsProfile]:
        """获取内置配置文件"""
        return [p for p in self.profiles.values() if p.is_builtin]

    def _save_profiles(self) -> None:
        """保存配置文件"""
        try:
            os.makedirs(os.path.dirname(self.profiles_file), exist_ok=True)
            profiles_data = {name: asdict(profile) for name, profile in self.profiles.items()}
            with open(self.profiles_file, 'w', encoding='utf-8') as f:
                json.dump(profiles_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save profiles: {e}")

    def export_settings(self, export_path: str, profile_name: str = None) -> bool:
        """导出设置"""
        try:
            if profile_name:
                if profile_name not in self.profiles:
                    return False
                settings_to_export = self.profiles[profile_name].settings
            else:
                settings_to_export = self.settings

            export_data = {
                'settings': settings_to_export,
                'exported_at': datetime.now().isoformat(),
                'cineai_version': '2.0.0',
                'profile_name': profile_name
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Exported settings to {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export settings: {e}")
            return False

    def import_settings(self, import_path: str, merge: bool = True) -> bool:
        """导入设置"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            imported_settings = import_data.get('settings', {})

            if merge:
                # 合并设置
                for key, value in imported_settings.items():
                    if key in self.settings_definitions:
                        self.set_setting(key, value)
            else:
                # 替换设置
                self._update_settings(imported_settings)
                self._save_settings()

            self.logger.info(f"Imported settings from {import_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to import settings: {e}")
            return False

    def get_setting_definition(self, key: str) -> Optional[SettingDefinition]:
        """获取设置定义"""
        return self.settings_definitions.get(key)

    def get_all_setting_definitions(self) -> Dict[str, SettingDefinition]:
        """获取所有设置定义"""
        return self.settings_definitions.copy()

    def get_categories(self) -> List[str]:
        """获取所有设置类别"""
        categories = set()
        for definition in self.settings_definitions.values():
            categories.add(definition.category)
        return sorted(categories)

    def search_settings(self, query: str) -> List[Dict[str, Any]]:
        """搜索设置"""
        results = []
        query_lower = query.lower()

        for key, definition in self.settings_definitions.items():
            if (query_lower in definition.name.lower() or
                query_lower in definition.description.lower() or
                query_lower in key.lower()):
                results.append({
                    'key': key,
                    'value': self.settings.get(key, definition.default_value),
                    'definition': definition
                })

        return results

    def validate_settings(self) -> Dict[str, List[str]]:
        """验证所有设置"""
        validation_result = {}

        for key, value in self.settings.items():
            if key in self.settings_definitions:
                if not self._validate_setting(key, value):
                    validation_result[key] = [f"Invalid value: {value}"]
            else:
                validation_result[key] = ["Unknown setting"]

        return validation_result

    def get_settings_summary(self) -> Dict[str, Any]:
        """获取设置摘要"""
        try:
            # 按类别统计设置
            category_stats = {}
            for definition in self.settings_definitions.values():
                category = definition.category
                if category not in category_stats:
                    category_stats[category] = {
                        'total': 0,
                        'advanced': 0,
                        'modified': 0
                    }
                category_stats[category]['total'] += 1
                if definition.advanced:
                    category_stats[category]['advanced'] += 1

            # 统计修改的设置
            for key, value in self.settings.items():
                if key in self.settings_definitions:
                    definition = self.settings_definitions[key]
                    if value != definition.default_value:
                        category_stats[definition.category]['modified'] += 1

            return {
                'total_settings': len(self.settings_definitions),
                'modified_settings': sum(1 for k, v in self.settings.items()
                                       if k in self.settings_definitions and
                                       v != self.settings_definitions[k].default_value),
                'category_stats': category_stats,
                'profiles_count': len(self.profiles),
                'builtin_profiles_count': len([p for p in self.profiles.values() if p.is_builtin])
            }

        except Exception as e:
            self.logger.error(f"Failed to get settings summary: {e}")
            return {}

    # 自定义验证器
    def _validate_resolution(self, value: str) -> bool:
        """验证分辨率格式"""
        try:
            parts = value.split('x')
            if len(parts) != 2:
                return False
            width, height = int(parts[0]), int(parts[1])
            return width > 0 and height > 0
        except ValueError:
            return False

    def _validate_path(self, value: str) -> bool:
        """验证路径"""
        try:
            path = Path(value)
            return path.exists() or path.parent.exists()
        except Exception as e:
            self.logger.debug(f"Path validation error: {e}")
            return False

    def _validate_color(self, value: str) -> bool:
        """验证颜色格式"""
        try:
            # 支持十六进制颜色格式
            if value.startswith('#'):
                return len(value) in [4, 7, 9]  # #RGB, #RRGGBB, #RRGGBBAA
            # 支持RGB/RGBA格式
            return value in ['red', 'green', 'blue', 'white', 'black', 'transparent']
        except Exception as e:
            self.logger.debug(f"Color validation error: {e}")
            return False