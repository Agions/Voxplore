"""
Plugin Interfaces
插件接口定义
"""

from scenefab.plugins.interfaces.base import (
    AppContext,
    BasePlugin,
    PluginManifest,
    PluginType,
)

__all__ = ["BasePlugin", "PluginManifest", "PluginType", "AppContext"]
