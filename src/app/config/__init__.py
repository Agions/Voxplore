"""SceneFab 配置管理包。

公开 API:
- ConfigManager: 全局配置管理（原 scenefab.config）
- ProjectSettingsManager: 项目设置管理（原 scenefab.config_manager）
- SettingDefinition / SettingType: 类型定义（原 config_types）
- get_all_config_definitions: 设置项定义集合（原 config_data）
"""

from .config import ConfigManager
from .definitions import get_all_config_definitions
from .manager import ProjectSettingsManager
from .types import ProjectSettingsProfile, SettingDefinition, SettingType

__all__ = [
    "ConfigManager",
    "ProjectSettingsManager",
    "SettingDefinition",
    "SettingType",
    "ProjectSettingsProfile",
    "get_all_config_definitions",
]
