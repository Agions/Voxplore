"""
SceneFab Plugin System
插件系统核心模块
"""

from app.plugins.interfaces.base import BasePlugin, PluginManifest, PluginType
from app.plugins.loader import PluginLoader
from app.plugins.registry import PluginRegistry

__all__ = [
    "BasePlugin",
    "PluginManifest",
    "PluginType",
    "PluginLoader",
    "PluginRegistry",
]
