"""
Plugin Registry
插件注册中心，管理所有已加载的插件
"""

import json
import os
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from app.plugins.interfaces.base import BasePlugin, PluginManifest, PluginType, AppContext


class PluginState(Enum):
    """插件状态"""
    UNINSTALLED = "uninstalled"
    INSTALLED = "installed"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginEntry:
    """插件条目"""
    manifest: PluginManifest
    state: PluginState = PluginState.UNINSTALLED
    instance: Optional[BasePlugin] = None
    error_message: Optional[str] = None
    load_order: int = 0  # 加载优先级


class PluginRegistry:
    """
    插件注册中心

    职责:
    - 注册/注销插件
    - 管理插件生命周期
    - 提供插件查询接口
    """

    def __init__(self):
        self._plugins: Dict[str, PluginEntry] = {}
        self._hooks: Dict[str, List[Callable]] = {
            "plugin_enabled": [],
            "plugin_disabled": [],
            "plugin_error": [],
        }
        self._context: Optional[AppContext] = None

    def set_context(self, context: AppContext) -> None:
        """设置应用上下文"""
        self._context = context

    # ─────────────────────────────────────────────────────────────
    # Registration
    # ─────────────────────────────────────────────────────────────

    def register_plugin(self, manifest: PluginManifest) -> None:
        """
        注册插件（但不加载）

        验证清单并添加到注册表
        """
        errors = manifest.validate()
        if errors:
            raise ValueError(f"Invalid manifest: {', '.join(errors)}")

        if manifest.id in self._plugins:
            raise ValueError(f"Plugin {manifest.id} already registered")

        entry = PluginEntry(manifest=manifest, state=PluginState.INSTALLED)
        self._plugins[manifest.id] = entry
        self.log_info(f"Registered plugin: {manifest.id} v{manifest.version}")

    def unregister_plugin(self, plugin_id: str) -> None:
        """注销插件"""
        if plugin_id not in self._plugins:
            return

        entry = self._plugins[plugin_id]
        if entry.state in (PluginState.ENABLED, PluginState.INITIALIZED):
            self.disable_plugin(plugin_id)

        del self._plugins[plugin_id]
        self.log_info(f"Unregistered plugin: {plugin_id}")

    # ─────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────

    def load_plugin(self, plugin_id: str) -> None:
        """加载插件（实例化）"""
        entry = self._plugins.get(plugin_id)
        if not entry:
            raise KeyError(f"Plugin not found: {plugin_id}")

        if entry.state != PluginState.INSTALLED:
            raise RuntimeError(
                f"Plugin {plugin_id} cannot be loaded in state: {entry.state.value}"
            )

        try:
            # 动态实例化
            plugin_class = entry.manifest.load_entry_point()
            instance: BasePlugin = plugin_class(manifest=entry.manifest)
            entry.instance = instance
            entry.state = PluginState.LOADED
            self.log_info(f"Loaded plugin: {plugin_id}")
        except Exception as e:
            entry.state = PluginState.ERROR
            entry.error_message = str(e)
            self._emit_hook("plugin_error", plugin_id=plugin_id, error=e)
            raise

    def initialize_plugin(self, plugin_id: str) -> None:
        """初始化插件"""
        entry = self._plugins.get(plugin_id)
        if not entry or not entry.instance:
            raise KeyError(f"Plugin not loaded: {plugin_id}")

        if entry.state != PluginState.LOADED:
            raise RuntimeError(
                f"Plugin {plugin_id} cannot be initialized in state: {entry.state.value}"
            )

        try:
            if self._context:
                entry.instance.initialize(self._context)
            entry.state = PluginState.INITIALIZED
            self.log_info(f"Initialized plugin: {plugin_id}")
        except Exception as e:
            entry.state = PluginState.ERROR
            entry.error_message = str(e)
            self._emit_hook("plugin_error", plugin_id=plugin_id, error=e)
            raise

    def enable_plugin(self, plugin_id: str) -> None:
        """启用插件"""
        entry = self._plugins.get(plugin_id)
        if not entry or not entry.instance:
            raise KeyError(f"Plugin not initialized: {plugin_id}")

        if entry.state == PluginState.ENABLED:
            return

        entry.instance.enable()
        entry.state = PluginState.ENABLED
        self._emit_hook("plugin_enabled", plugin_id=plugin_id)
        self.log_info(f"Enabled plugin: {plugin_id}")

    def disable_plugin(self, plugin_id: str) -> None:
        """禁用插件"""
        entry = self._plugins.get(plugin_id)
        if not entry or not entry.instance:
            return

        if entry.state != PluginState.ENABLED:
            return

        entry.instance.disable()
        entry.state = PluginState.DISABLED
        self._emit_hook("plugin_disabled", plugin_id=plugin_id)
        self.log_info(f"Disabled plugin: {plugin_id}")

    def destroy_plugin(self, plugin_id: str) -> None:
        """销毁插件"""
        entry = self._plugins.get(plugin_id)
        if not entry:
            return

        if entry.state == PluginState.ENABLED:
            self.disable_plugin(plugin_id)

        if entry.instance:
            entry.instance.destroy()
            entry.instance = None

        self.unregister_plugin(plugin_id)

    # ─────────────────────────────────────────────────────────────
    # Query
    # ─────────────────────────────────────────────────────────────

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """获取插件实例"""
        entry = self._plugins.get(plugin_id)
        return entry.instance if entry else None

    def get_manifest(self, plugin_id: str) -> Optional[PluginManifest]:
        """获取插件清单"""
        entry = self._plugins.get(plugin_id)
        return entry.manifest if entry else None

    def get_state(self, plugin_id: str) -> Optional[PluginState]:
        """获取插件状态"""
        entry = self._plugins.get(plugin_id)
        return entry.state if entry else None

    def list_plugins(
        self,
        plugin_type: Optional[PluginType] = None,
        state: Optional[PluginState] = None,
        enabled_only: bool = False,
    ) -> List[PluginManifest]:
        """列出插件"""
        result = []
        for entry in self._plugins.values():
            if enabled_only and not entry.instance.is_enabled:
                continue
            if plugin_type and entry.manifest.plugin_type != plugin_type:
                continue
            if state and entry.state != state:
                continue
            result.append(entry.manifest)
        return result

    def list_enabled_plugins(self) -> List[BasePlugin]:
        """列出所有已启用的插件"""
        return [
            entry.instance
            for entry in self._plugins.values()
            if entry.instance and entry.instance.is_enabled
        ]

    def list_plugins_by_type(self, plugin_type: PluginType) -> List[PluginManifest]:
        """按类型列出插件"""
        return self.list_plugins(plugin_type=plugin_type)

    # ─────────────────────────────────────────────────────────────
    # Hooks
    # ─────────────────────────────────────────────────────────────

    def add_hook(self, event: str, callback: Callable) -> None:
        """添加生命周期钩子"""
        if event in self._hooks:
            self._hooks[event].append(callback)

    def remove_hook(self, event: str, callback: Callable) -> None:
        """移除生命周期钩子"""
        if event in self._hooks:
            self._hooks[event].remove(callback)

    def _emit_hook(self, event: str, **kwargs) -> None:
        """触发钩子"""
        for callback in self._hooks.get(event, []):
            try:
                callback(**kwargs)
            except Exception as e:
                self.log_error(f"Hook error in {event}: {e}")

    # ─────────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────────

    def load_enabled_list(self, path: str) -> List[str]:
        """从文件加载已启用的插件列表"""
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_enabled_list(self, path: str) -> None:
        """保存已启用的插件列表"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        enabled = [
            pid for pid, entry in self._plugins.items()
            if entry.state == PluginState.ENABLED
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(enabled, f, indent=2)

    # ─────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────

    def log_info(self, message: str) -> None:
        import logging
        logging.getLogger("voxplore.plugins").info(message)

    def log_error(self, message: str) -> None:
        import logging
        logging.getLogger("voxplore.plugins").error(message)

    def __len__(self) -> int:
        return len(self._plugins)

    def __contains__(self, plugin_id: str) -> bool:
        return plugin_id in self._plugins

    def get(self, plugin_id: str, default=None):
        """获取插件条目（dict 兼容接口）"""
        entry = self._plugins.get(plugin_id)
        if entry is None:
            return default
        return {
            "manifest": entry.manifest,
            "state": entry.state.value if entry.state else None,
            "enabled": entry.state == PluginState.ENABLED,
            "instance": entry.instance,
        }
