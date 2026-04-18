"""
Plugin Loader
插件加载器，负责扫描目录和加载插件
"""

import os
import json
import importlib
import importlib.util
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.plugins.interfaces.base import PluginManifest, PluginType, AppContext
from app.plugins.registry import PluginRegistry


class PluginLoader:
    """
    插件加载器
    
    功能:
    - 扫描插件目录
    - 解析清单文件
    - 验证插件依赖
    - 加载插件到注册表
    """

    def __init__(self, registry: PluginRegistry):
        self._registry = registry
        self._plugin_dirs: List[Path] = []

    def add_plugin_directory(self, directory: str) -> None:
        """添加插件搜索目录"""
        path = Path(directory).expanduser().absolute()
        if not path.exists():
            raise ValueError(f"Plugin directory does not exist: {path}")
        self._plugin_dirs.append(path)

    def discover_plugins(self) -> List[PluginManifest]:
        """
        扫描所有插件目录，发现插件
        
        Returns:
            发现的插件清单列表
        """
        discovered = []

        for plugin_dir in self._plugin_dirs:
            if not plugin_dir.exists():
                continue

            # 扫描所有子目录
            for entry in plugin_dir.iterdir():
                if not entry.is_dir():
                    continue
                if entry.name.startswith("_") or entry.name.startswith("."):
                    continue

                manifest = self._discover_plugin_in_dir(entry)
                if manifest:
                    discovered.append(manifest)

        return discovered

    def _discover_plugin_in_dir(self, plugin_path: Path) -> Optional[PluginManifest]:
        """
        在指定目录中发现插件
        
        查找顺序:
        1. manifest.json
        2. __manifest__.json
        3. plugin.json
        """
        candidates = [
            plugin_path / "manifest.json",
            plugin_path / "__manifest__.json",
            plugin_path / "plugin.json",
        ]

        manifest_path = None
        for candidate in candidates:
            if candidate.exists():
                manifest_path = candidate
                break

        if not manifest_path:
            return None

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 转换 plugin_type 字符串为枚举
            if isinstance(data.get("plugin_type"), str):
                data["plugin_type"] = PluginType(data["plugin_type"])

            manifest = PluginManifest(**data)
            return manifest

        except Exception as e:
            print(f"Failed to load manifest from {manifest_path}: {e}")
            return None

    def load_plugin_from_directory(
        self,
        plugin_dir: Path,
        manifest: PluginManifest,
        context: AppContext,
    ) -> bool:
        """
        从目录加载单个插件
        
        步骤:
        1. 注册到清单
        2. 实例化
        3. 初始化
        """
        try:
            # 注册
            self._registry.register_plugin(manifest)

            # 添加插件路径到 sys.path（如果需要）
            plugin_path_str = str(plugin_dir)
            if plugin_path_str not in importlib.sys.path:
                importlib.sys.path.insert(0, plugin_path_str)

            # 加载
            self._registry.load_plugin(manifest.id)

            # 初始化
            self._registry.initialize_plugin(manifest.id)

            # 启用
            self._registry.enable_plugin(manifest.id)

            return True

        except Exception as e:
            print(f"Failed to load plugin {manifest.id}: {e}")
            return False

    def load_all_discovered(
        self,
        context: AppContext,
        enabled_plugins: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """
        加载所有发现的插件
        
        Args:
            context: 应用上下文
            enabled_plugins: 指定启用的插件 ID 列表，None 则全部启用
            
        Returns:
            插件 ID -> 是否成功
        """
        results = {}
        discovered = self.discover_plugins()

        for manifest in discovered:
            plugin_id = manifest.id

            # 检查是否在启用的插件列表中
            if enabled_plugins is not None and plugin_id not in enabled_plugins:
                continue

            # 查找插件目录
            plugin_dir = self._find_plugin_dir(manifest.id)
            if not plugin_dir:
                results[plugin_id] = False
                continue

            # 加载
            success = self.load_plugin_from_directory(plugin_dir, manifest, context)
            results[plugin_id] = success

        return results

    def _find_plugin_dir(self, plugin_id: str) -> Optional[Path]:
        """根据插件 ID 查找目录"""
        parts = plugin_id.split(".")
        for plugin_dir in self._plugin_dirs:
            path = plugin_dir.joinpath(*parts)
            if path.exists() and path.is_dir():
                return path
        return None

    def validate_dependencies(
        self,
        manifest: PluginManifest,
        available_packages: Dict[str, str],
    ) -> List[str]:
        """
        验证插件依赖是否满足
        
        Returns:
            缺失或不满足的依赖列表
        """
        missing = []

        for package, version_spec in manifest.dependencies.items():
            if package not in available_packages:
                missing.append(f"{package} (required, not installed)")
                continue

            # 简单版本检查（实际应该用 packaging.version）
            installed = available_packages[package]
            if not self._check_version(installed, version_spec):
                missing.append(f"{package} {version_spec} (have {installed})")

        return missing

    def _check_version(self, installed: str, spec: str) -> bool:
        """
        简单版本检查
        
        支持:
        - ">=1.0.0"
        - "~=1.0.0"
        - "==1.0.0"
        - "^1.0.0"
        """
        spec = spec.strip()

        if spec.startswith(">="):
            required = spec[2:].strip()
            return self._parse_version(installed) >= self._parse_version(required)
        elif spec.startswith("=="):
            required = spec[2:].strip()
            return self._parse_version(installed) == self._parse_version(required)
        elif spec.startswith("~="):
            required = spec[2:].strip()
            return self._parse_version(installed) >= self._parse_version(required)
        elif spec.startswith("^"):
            required = spec[1:].strip()
            inst = self._parse_version(installed)
            req = self._parse_version(required)
            return inst.major == req.major and inst >= req

        return True

    def _parse_version(self, version: str) -> tuple:
        """解析版本号为元组"""
        import re
        match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
        if match:
            return tuple(int(x) for x in match.groups())
        return (0, 0, 0)
