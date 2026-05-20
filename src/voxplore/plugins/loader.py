"""
Plugin Loader
插件加载器，负责扫描目录和加载插件
支持两种发现机制：
  1. 目录扫描 - 本地插件（已有）
  2. setuptools entry_points - 第三方包插件（新增）
"""

import sys
import json
import importlib
import importlib.util
from pathlib import Path
from typing import List, Optional, Dict

from voxplore.plugins.interfaces.base import PluginManifest, PluginType, AppContext
from voxplore.plugins.registry import PluginRegistry


class PluginLoader:
    """
    插件加载器

    功能:
    - 扫描插件目录（本地插件）
    - 扫描 setuptools entry_points（第三方插件）
    - 解析清单文件
    - 验证插件依赖
    - 加载插件到注册表
    """

    # entry_points 中的组名
    ENTRY_POINT_GROUP = "voxplore.plugins"

    def __init__(self, registry: PluginRegistry = None):
        self._registry = registry if registry is not None else PluginRegistry()
        self._plugin_dirs: List[Path] = []

    def add_plugin_directory(self, directory: str) -> None:
        """添加插件搜索目录"""
        path = Path(directory).expanduser().absolute()
        if not path.exists():
            raise ValueError(f"Plugin directory does not exist: {path}")
        self._plugin_dirs.append(path)

    def get_registry(self) -> PluginRegistry:
        """获取插件注册表实例"""
        return self._registry

    def discover_plugins(self) -> List[PluginManifest]:
        """
        扫描所有插件目录，发现插件（目录扫描 + entry_points）

        Returns:
            发现的插件清单列表
        """
        discovered = []

        # 1. 目录扫描
        for plugin_dir in self._plugin_dirs:
            if not plugin_dir.exists():
                continue
            for entry in plugin_dir.iterdir():
                if not entry.is_dir():
                    continue
                if entry.name.startswith("_") or entry.name.startswith("."):
                    continue
                manifest = self._discover_plugin_in_dir(entry)
                if manifest:
                    discovered.append(manifest)

        # 2. entry_points 自动发现（新增）
        discovered.extend(self._discover_via_entry_points())

        return discovered

    def _discover_via_entry_points(self) -> List[PluginManifest]:
        """
        通过 setuptools entry_points 发现已安装的第三方插件

        第三方包需要在 setup.py / pyproject.toml 中声明：
            entry_points={
                "voxplore.plugins": [
                    "my-plugin = my_plugin.module:PluginClass"
                ]
            }
        """
        manifests = []
        try:
            # Python 3.10+ / importlib.metadata
            from importlib.metadata import entry_points
        except ImportError:
            # Python 3.9 兼容
            from importlib_metadata import entry_points

        try:
            # Python 3.12+ 修改了 entry_points() 返回结构
            eps = entry_points()
            if hasattr(eps, "select"):
                # Python 3.12+ 或 importlib_metadata 4.x+
                plugin_eps = eps.select(group=self.ENTRY_POINT_GROUP)
            else:
                # Python 3.10-3.11
                plugin_eps = eps.get(self.ENTRY_POINT_GROUP, [])
        except Exception:
            plugin_eps = []

        for ep in plugin_eps:
            manifest = self._load_manifest_from_entry_point(ep)
            if manifest:
                manifests.append(manifest)

        return manifests

    def _load_manifest_from_entry_point(self, ep) -> Optional[PluginManifest]:
        """
        从 entry_point 加载插件清单

        策略：
        1. 尝试让插件自己返回清单（如果它实现了 get_manifest 工厂函数）
        2. 否则根据 entry_point 信息构造最小清单
        """
        try:
            # 尝试获取插件模块
            plugin_class = ep.load()

            # 策略1：插件提供 get_manifest() 工厂函数
            if hasattr(plugin_class, "get_manifest"):
                manifest_data = plugin_class.get_manifest()
                if isinstance(manifest_data, dict):
                    manifest_data.setdefault("entry_point", f"{ep.module}:{ep.attr}")
                    if isinstance(manifest_data.get("plugin_type"), str):
                        manifest_data["plugin_type"] = PluginType(manifest_data["plugin_type"])
                    return PluginManifest(**manifest_data)

            # 策略2：从插件类的 Meta 属性读取
            if hasattr(plugin_class, "Meta") and hasattr(plugin_class.Meta, "manifest"):
                meta = plugin_class.Meta.manifest
                if isinstance(meta, dict):
                    meta.setdefault("entry_point", f"{ep.module}:{ep.attr}")
                    if isinstance(meta.get("plugin_type"), str):
                        meta["plugin_type"] = PluginType(meta["plugin_type"])
                    return PluginManifest(**meta)

            # 策略3：从类名推断最小清单（最后手段）
            return self._infer_manifest_from_ep(ep, plugin_class)

        except Exception as e:
            print(f"Failed to load entry_point {ep}: {e}")
            return None

    def _infer_manifest_from_ep(self, ep, plugin_class) -> Optional[PluginManifest]:
        """从 entry_point 信息推断最小清单"""
        # 从类名推断插件类型
        plugin_type = PluginType.AI_GENERATOR  # 默认类型
        class_name_lower = plugin_class.__name__.lower()
        if "subtitle" in class_name_lower:
            plugin_type = PluginType.SUBTITLE_STYLE
        elif "export" in class_name_lower:
            plugin_type = PluginType.EXPORT
        elif "voice" in class_name_lower:
            plugin_type = PluginType.VOICE_CLONE
        elif "effect" in class_name_lower:
            plugin_type = PluginType.VIDEO_EFFECT
        elif "scene" in class_name_lower:
            plugin_type = PluginType.SCENE_DETECTOR

        # 从模块名提取插件 ID
        module_parts = ep.module.split(".")
        plugin_id = ".".join(module_parts[-2:]) if len(module_parts) >= 2 else module_parts[-1]

        return PluginManifest(
            id=plugin_id,
            name=plugin_class.__name__.replace("_", " ").replace("-", " ").title(),
            version="1.0.0",
            author="Unknown",
            description=f"Discovered via entry_points: {ep.module}:{ep.attr}",
            plugin_type=plugin_type,
            entry_point=f"{ep.module}:{ep.attr}",
        )

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
        """
        try:
            self._registry.register_plugin(manifest)
            self._safe_load_entry_point(plugin_dir, manifest)
            self._registry.load_plugin(manifest.id)
            self._registry.initialize_plugin(manifest.id)
            self._registry.enable_plugin(manifest.id)
            return True
        except Exception as e:
            print(f"Failed to load plugin {manifest.id}: {e}")
            return False

    def load_plugin_from_entry_point(
        self,
        manifest: PluginManifest,
        context: AppContext,
    ) -> bool:
        """
        从 entry_point 加载单个插件（不经过文件系统）

        步骤:
        1. 注册到清单
        2. 实例化
        3. 初始化
        """
        try:
            self._registry.register_plugin(manifest)

            # 直接 importlib 加载，不触碰文件系统
            module_path, class_name = manifest.entry_point.split(":", 1)
            module = importlib.import_module(module_path)
            plugin_class = getattr(module, class_name)
            plugin_instance = plugin_class(manifest)

            # 初始化 + 启用
            plugin_instance.initialize(context)
            plugin_instance.enable()

            # 注册实例
            entry = self._registry._plugins.get(manifest.id)
            if entry:
                entry.instance = plugin_instance
                entry.state = self._registry.PluginState.ENABLED

            return True

        except Exception as e:
            print(f"Failed to load plugin from entry_point {manifest.id}: {e}")
            return False

    def _safe_load_entry_point(self, plugin_dir: Path, manifest: PluginManifest) -> None:
        """
        安全地加载插件入口点，避免 sys.path 注入攻击
        """
        plugin_dir_resolved = plugin_dir.resolve()
        is_allowed = any(
            allowed_dir.resolve() in plugin_dir_resolved.parents
            or plugin_dir_resolved == allowed_dir.resolve()
            for allowed_dir in self._plugin_dirs
        )
        if not is_allowed:
            raise ValueError(f"Plugin directory not in allowed plugin dirs: {plugin_dir}")

        module_path, class_name = manifest.entry_point.split(":", 1)
        module_file_path = plugin_dir / f"{module_path.replace('.', '/')}.py"

        module_file_resolved = module_file_path.resolve()
        if not module_file_resolved.is_relative_to(plugin_dir_resolved):
            raise ValueError(f"Entry point path escapes plugin directory: {module_file_path}")

        spec = importlib.util.spec_from_file_location(module_path, module_file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {module_file_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_path] = module
        spec.loader.exec_module(module)

    def load_all_discovered(
        self,
        context: AppContext,
        enabled_plugins: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """
        加载所有发现的插件
        """
        results = {}
        discovered = self.discover_plugins()

        for manifest in discovered:
            plugin_id = manifest.id
            if enabled_plugins is not None and plugin_id not in enabled_plugins:
                continue

            # 判断来源：entry_point vs 目录
            if ":" in manifest.entry_point and not any(
                allowed_dir.resolve() in Path(self._find_plugin_dir(plugin_id) or ".")
                .resolve()
                .parents
                for allowed_dir in self._plugin_dirs
            ):
                # entry_point 来源（检查是否是目录插件）
                plugin_dir = self._find_plugin_dir(plugin_id)
                if plugin_dir and plugin_dir.exists():
                    success = self.load_plugin_from_directory(plugin_dir, manifest, context)
                else:
                    success = self.load_plugin_from_entry_point(manifest, context)
            else:
                # 目录来源
                plugin_dir = self._find_plugin_dir(plugin_id)
                if not plugin_dir:
                    results[plugin_id] = False
                    continue
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
        """验证插件依赖是否满足"""
        missing = []
        for package, version_spec in manifest.dependencies.items():
            if package not in available_packages:
                missing.append(f"{package} (required, not installed)")
                continue
            installed = available_packages[package]
            if not self._check_version(installed, version_spec):
                missing.append(f"{package} {version_spec} (have {installed})")
        return missing

    def _check_version(self, installed: str, spec: str) -> bool:
        """简单版本检查"""
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
