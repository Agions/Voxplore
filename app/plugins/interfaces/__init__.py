"""
Plugin Interfaces
插件接口定义
"""

from app.plugins.interfaces.base import BasePlugin, PluginManifest, PluginType, AppContext

__all__ = ["BasePlugin", "PluginManifest", "PluginType", "AppContext"]
