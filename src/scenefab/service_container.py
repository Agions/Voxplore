"""
服务容器 - 增强版

支持三种生命周期：
  - Singleton（单例）：全局唯一，多次 get() 返回同一实例
  - Transient（瞬态）：每次 get() 创建新实例
  - Factory（厂方法）：每次 get() 调用用户提供的工厂函数

用法示例：
    container = ServiceContainer()

    # 注册单例
    container.register_singleton(ConfigManager, ConfigManager())
    container.register_singleton("config", ConfigManager())

    # 注册瞬态（类）
    container.register_transient(ProjectManager)

    # 注册厂方法
    container.register_factory("logger", lambda: logging.getLogger("scenefab"))

    # 获取
    cfg = container.get(ConfigManager)
    logger = container.get_by_name("logger")
"""

from typing import Dict, Any, Optional, Type, Callable, Union


class ServiceLifetime:
    """服务生命周期枚举"""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    FACTORY = "factory"


class _ServiceEntry:
    """内部服务条目"""

    def __init__(
        self,
        lifetime: str,
        instance: Any = None,
        service_type: Optional[Type] = None,
        factory: Optional[Callable] = None,
    ):
        self.lifetime = lifetime
        self.instance = instance  # 仅 SINGLETON 使用
        self.service_type = service_type  # 仅 TRANSIENT 使用（类）
        self.factory = factory  # FACTORY / TRANSIENT(类工厂) 使用


class ServiceContainer:
    """增强版服务容器"""

    def __init__(self):
        self._services: Dict[Type, _ServiceEntry] = {}
        self._services_by_name: Dict[str, _ServiceEntry] = {}

    # ─── 注册 ───────────────────────────────────────────────

    def register(self, service_type: Type, instance: Any) -> None:
        """注册服务实例（默认单例）"""
        self._services[service_type] = _ServiceEntry(
            lifetime=ServiceLifetime.SINGLETON,
            instance=instance,
            service_type=service_type,
        )

    def register_by_name(self, name: str, instance: Any) -> None:
        """按名称注册服务实例（默认单例）"""
        self._services_by_name[name] = _ServiceEntry(
            lifetime=ServiceLifetime.SINGLETON,
            instance=instance,
        )

    def register_singleton(
        self,
        service_type: Union[Type, str],
        instance_or_type: Union[Any, Type],
    ) -> None:
        """注册单例服务"""
        if isinstance(service_type, str):
            self._services_by_name[service_type] = _ServiceEntry(
                lifetime=ServiceLifetime.SINGLETON,
                instance=instance_or_type,
            )
        else:
            self._services[service_type] = _ServiceEntry(
                lifetime=ServiceLifetime.SINGLETON,
                instance=instance_or_type,
                service_type=service_type,
            )

    def register_transient(
        self,
        service_type: Union[Type, str],
        factory_or_type: Union[Type, Callable],
    ) -> None:
        """注册瞬态服务（类或工厂函数）"""
        if isinstance(service_type, str):
            self._services_by_name[service_type] = _ServiceEntry(
                lifetime=ServiceLifetime.TRANSIENT,
                factory=factory_or_type,
            )
        else:
            self._services[service_type] = _ServiceEntry(
                lifetime=ServiceLifetime.TRANSIENT,
                service_type=factory_or_type,
                factory=factory_or_type if not isinstance(factory_or_type, type) else None,
            )

    def register_factory(
        self,
        service_type: Union[Type, str],
        factory: Callable,
    ) -> None:
        """注册工厂方法服务"""
        if isinstance(service_type, str):
            self._services_by_name[service_type] = _ServiceEntry(
                lifetime=ServiceLifetime.FACTORY,
                factory=factory,
            )
        else:
            self._services[service_type] = _ServiceEntry(
                lifetime=ServiceLifetime.FACTORY,
                factory=factory,
            )

    # ─── 获取 ───────────────────────────────────────────────

    def get(self, service_type: Type) -> Optional[Any]:
        """获取服务实例"""
        entry = self._services.get(service_type)
        if entry is None:
            return None
        return self._resolve(entry)

    def get_by_name(self, name: str) -> Optional[Any]:
        """按名称获取服务实例"""
        entry = self._services_by_name.get(name)
        if entry is None:
            return None
        return self._resolve(entry)

    def get_or_create(self, service_type: Type, factory: Callable) -> Any:
        """获取服务，若不存在则用工厂创建（作为单例）"""
        entry = self._services.get(service_type)
        if entry is None:
            instance = factory()
            self.register_singleton(service_type, instance)
            return instance
        return self._resolve(entry)

    # ─── 解析 ───────────────────────────────────────────────

    def _resolve(self, entry: _ServiceEntry) -> Any:
        """根据生命周期解析实例"""
        if entry.lifetime == ServiceLifetime.SINGLETON:
            return entry.instance

        if entry.lifetime == ServiceLifetime.TRANSIENT:
            # 支持直接是类，或工厂函数
            if entry.service_type is not None and isinstance(entry.service_type, type):
                # 类 → 实例化
                return entry.service_type()
            elif entry.factory is not None:
                return entry.factory()
            # instance directly stored (backward compat)
            return entry.instance

        if entry.lifetime == ServiceLifetime.FACTORY:
            return entry.factory()

        return entry.instance

    # ─── 查询 ───────────────────────────────────────────────

    def has(self, service_type: Type) -> bool:
        """检查服务是否存在"""
        return service_type in self._services

    def has_by_name(self, name: str) -> bool:
        """按名称检查服务是否存在"""
        return name in self._services_by_name

    def get_lifetime(self, service_type: Type) -> Optional[str]:
        """获取服务生命周期类型"""
        entry = self._services.get(service_type)
        return entry.lifetime if entry else None

    # ─── 移除 / 清空 ─────────────────────────────────────────

    def remove(self, service_type: Type) -> None:
        """移除服务"""
        self._services.pop(service_type, None)

    def remove_by_name(self, name: str) -> None:
        """按名称移除服务"""
        self._services_by_name.pop(name, None)

    def clear(self) -> None:
        """清空所有服务"""
        self._services.clear()
        self._services_by_name.clear()


__all__ = ["ServiceContainer", "ServiceLifetime", "service_container"]

# 全局服务容器实例
service_container = ServiceContainer()