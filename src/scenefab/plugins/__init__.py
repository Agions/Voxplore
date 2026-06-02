"""
SceneFab Plugin System
插件系统核心模块
"""

from scenefab.plugins.interfaces.base import BasePlugin, PluginManifest, PluginType
from scenefab.plugins.loader import PluginLoader
from scenefab.plugins.registry import PluginRegistry

__all__ = [
    "BasePlugin",
    "PluginManifest",
    "PluginType",
    "PluginLoader",
    "PluginRegistry",
]
