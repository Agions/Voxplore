"""
Base Plugin Interface
所有插件的基类和类型定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
import json
import importlib


class PluginType(Enum):
    """插件类型枚举"""
    AI_GENERATOR = "ai_generator"       # AI 生成器插件
    EXPORT = "export"                     # 导出格式插件
    UI_EXTENSION = "ui_extension"         # UI 扩展插件
    VOICE_CLONE = "voice_clone"           # 音色克隆插件
    SUBTITLE_STYLE = "subtitle_style"     # 字幕样式插件
    VIDEO_EFFECT = "video_effect"         # 视频特效插件
    SCENE_DETECTOR = "scene_detector"     # 场景检测插件


@dataclass
class PluginManifest:
    """插件清单数据结构"""
    id: str                               # 唯一标识符 (e.g. "voxplore.wordstrike-subtitle")
    name: str                              # 显示名称
    version: str                           # 版本号 (semver)
    author: str                            # 作者
    description: str                       # 描述
    plugin_type: PluginType                # 插件类型
    homepage: Optional[str] = None         # 主页
    license: str = "MIT"                  # 许可证
    dependencies: Dict[str, str] = field(default_factory=dict)  # 依赖
    entry_point: str = ""                  # 入口点 "module.path:ClassName"
    permissions: List[str] = field(default_factory=list)          # 权限列表
    min_app_version: str = "1.0.0"         # 最低应用版本
    tags: List[str] = field(default_factory=list)                # 标签

    @classmethod
    def from_json(cls, json_str: str) -> "PluginManifest":
        """从 JSON 字符串加载"""
        data = json.loads(json_str)
        data["plugin_type"] = PluginType(data["plugin_type"])
        return cls(**data)

    def to_json(self) -> str:
        """序列化为 JSON"""
        data = self.__dict__.copy()
        data["plugin_type"] = self.plugin_type.value
        return json.dumps(data, indent=2, ensure_ascii=False)

    def validate(self) -> List[str]:
        """
        验证清单完整性
        Returns: 错误列表，空则验证通过
        """
        errors = []
        if not self.id or "." not in self.id:
            errors.append("Plugin ID must contain a dot (e.g. com.example.plugin)")
        if not self.name:
            errors.append("Plugin name is required")
        if not self.version:
            errors.append("Plugin version is required")
        if not self.entry_point or ":" not in self.entry_point:
            errors.append("Entry point must be in format 'module.path:ClassName'")
        return errors

    def load_entry_point(self) -> type:
        """
        动态加载入口类
        Returns: 插件类
        """
        module_path, class_name = self.entry_point.split(":", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)


@dataclass
class AppContext:
    """应用上下文，插件通过此获取应用服务"""
    app_name: str = "Voxplore"
    app_version: str = "1.0.0"
    data_dir: str = ""                    # 用户数据目录
    config_dir: str = ""                  # 配置目录
    cache_dir: str = ""                   # 缓存目录
    plugin_dir: str = ""                  # 插件目录
    services: Optional[Dict[str, Any]] = field(default_factory=dict)  # 可用服务


class BasePlugin(ABC):
    """
    所有插件的抽象基类

    插件生命周期:
    1. __init__(manifest) - 创建实例
    2. initialize(context) - 初始化
    3. enable() - 启用
    4. [使用插件功能]
    5. disable() - 禁用
    6. destroy() - 销毁清理
    """

    def __init__(self, manifest: PluginManifest):
        self.manifest = manifest
        self._enabled = False
        self._initialized = False
        self._context: Optional[AppContext] = None
        self._logger: Optional[Any] = None

    @property
    def id(self) -> str:
        return self.manifest.id

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def version(self) -> str:
        return self.manifest.version

    @property
    def plugin_type(self) -> PluginType:
        return self.manifest.plugin_type

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def initialize(self, context: AppContext) -> None:
        """
        初始化插件

        在此阶段:
        - 读取配置
        - 注册事件监听
        - 初始化资源
        """
        self._context = context
        self._initialized = True
        self._setup_logger()

    def enable(self) -> None:
        """启用插件"""
        if not self._initialized:
            raise RuntimeError("Plugin must be initialized before enabling")
        self._enabled = True
        self._on_enable()

    def disable(self) -> None:
        """禁用插件"""
        self._enabled = False
        self._on_disable()

    def destroy(self) -> None:
        """
        销毁插件，释放所有资源
        在 disable 后调用
        """
        self._on_destroy()
        self._context = None
        self._logger = None

    # ─────────────────────────────────────────────────────────────
    # Subclass Override Hooks
    # ─────────────────────────────────────────────────────────────

    def _setup_logger(self) -> None:
        """设置日志记录器（可选覆盖）"""
        import logging
        self._logger = logging.getLogger(f"plugin.{self.id}")

    def _on_enable(self) -> None:
        """启用时的回调（可选覆盖）"""
        pass

    def _on_disable(self) -> None:
        """禁用时的回调（可选覆盖）"""
        pass

    def _on_destroy(self) -> None:
        """销毁时的回调（可选覆盖）"""
        pass

    # ─────────────────────────────────────────────────────────────
    # Abstract Methods
    # ─────────────────────────────────────────────────────────────

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取插件元数据

        返回的字典会暴露给:
        - 插件管理 UI
        - API 端点
        - 插件市场
        """
        ...

    # ─────────────────────────────────────────────────────────────
    # Utility Methods
    # ─────────────────────────────────────────────────────────────

    def get_service(self, service_name: str) -> Any:
        """从上下文获取应用服务"""
        if not self._context:
            raise RuntimeError("Plugin not initialized")
        return self._context.services.get(service_name)

    def emit_event(self, event_name: str, **kwargs) -> None:
        """发射事件到事件总线"""
        if self._context and "event_bus" in self._context.services:
            self._context.services["event_bus"].emit(event_name, **kwargs)

    def subscribe_event(self, event_name: str, callback) -> None:
        """订阅事件"""
        if self._context and "event_bus" in self._context.services:
            self._context.services["event_bus"].subscribe(event_name, callback)

    def log_info(self, message: str) -> None:
        if self._logger:
            self._logger.info(message)

    def log_error(self, message: str) -> None:
        if self._logger:
            self._logger.error(message)

    def log_warning(self, message: str) -> None:
        if self._logger:
            self._logger.warning(message)
