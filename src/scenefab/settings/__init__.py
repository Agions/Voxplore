"""SceneFab 配置管理包。

公开 API:
- ConfigManager: 全局配置管理（原 scenefab.settings）
- ProjectSettingsManager: 项目设置管理（原 scenefab.settings_manager）
- SettingDefinition / SettingType: 类型定义（原 settings_types）
- get_all_settings_definitions: 设置项定义集合（原 settings_data）
"""

from .config import ConfigManager
from .manager import ProjectSettingsManager
from .definitions import get_all_settings_definitions
from .types import SettingDefinition, SettingType, ProjectSettingsProfile

__all__ = [
    "ConfigManager",
    "ProjectSettingsManager",
    "SettingDefinition",
    "SettingType",
    "ProjectSettingsProfile",
    "get_all_settings_definitions",
]
