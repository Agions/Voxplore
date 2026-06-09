"""
SceneFab 依赖注入容器 v2.1（轻量、零外部依赖）

v2.1 在 v1.x `ServiceContainer` 基础上扩展：

1. **作用域**：
   - SINGLETON: 进程内单例
   - SCOPED: 在 `enter_scope()` 内单例
   - TRANSIENT: 每次 `resolve()` 都新建
   - FACTORY: 自定义工厂
2. **装饰器**：`@inject(container, "service_name")` 注入到方法
3. **上下文**：`with container.enter_scope() as scope: ...` 自动清理
4. **类型化注册**：`register_type(ServiceType, factory)` 用于类型注册
5. **钩子**：`on_resolve(callback)` 解析后回调（v2.1 用于自动注入 event_bus）
6. **与事件总线协作**：`register_with_event_bus(name, instance)` 自动订阅

v2.1 不破坏 v1.x API：
- `register` / `register_singleton` / `register_transient` / `register_factory` 保留
- `get` / `get_by_name` / `has` / `remove` / `clear` 保留
"""

from __future__ import annotations

import functools
import logging
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ServiceLifetime(str, Enum):
    """服务生命周期（v2.1 加 SCOPED）"""

    SINGLETON = "singleton"
    SCOPED = "scoped"
    TRANSIENT = "transient"
    FACTORY = "factory"


@dataclass
class _ServiceEntry:
    lifetime: ServiceLifetime
    instance: Any = None
    service_type: type | None = None
    factory: Callable | None = None
    name: str | None = None  # for by-name resolution


class DIContainer:
    """
    依赖注入容器 v2.1

    用法::

        c = DIContainer()
        c.register_singleton(MyService, MyService(...))
        c.register_transient(MyOtherService, MyOtherService)

        with c.enter_scope() as scope:
            svc = scope.resolve(MyService)
    """

    def __init__(self, *, name: str = "default"):
        self._name = name
        self._services: dict[type, _ServiceEntry] = {}
        self._by_name: dict[str, _ServiceEntry] = {}
        self._lock = threading.RLock()
        # 作用域栈
        self._scope_stack: list[dict[type, Any]] = []
        # 解析后钩子
        self._resolve_hooks: list[Callable[[str, Any], None]] = []

    # ────────────────────────────────────────────────
    # 注册
    # ────────────────────────────────────────────────

    def register(self, service_type: type, instance: Any) -> None:
        """注册服务实例（默认 SINGLETON）- 兼容 v1.x"""
        with self._lock:
            self._services[service_type] = _ServiceEntry(
                lifetime=ServiceLifetime.SINGLETON,
                instance=instance,
                service_type=service_type,
            )

    def register_by_name(self, name: str, instance: Any) -> None:
        """按名称注册实例 - 兼容 v1.x"""
        with self._lock:
            self._by_name[name] = _ServiceEntry(
                lifetime=ServiceLifetime.SINGLETON,
                instance=instance,
                name=name,
            )

    def register_singleton(
        self,
        service_type: type | str,
        instance_or_type: Any | type,
    ) -> None:
        """注册单例 - 兼容 v1.x"""
        with self._lock:
            if isinstance(service_type, str):
                self._by_name[service_type] = _ServiceEntry(
                    lifetime=ServiceLifetime.SINGLETON,
                    instance=instance_or_type,
                    name=service_type,
                )
            else:
                self._services[service_type] = _ServiceEntry(
                    lifetime=ServiceLifetime.SINGLETON,
                    instance=instance_or_type,
                    service_type=service_type,
                )

    def register_transient(
        self,
        service_type: type | str,
        factory_or_type: type | Callable,
    ) -> None:
        """注册 TRANSIENT - 兼容 v1.x"""
        with self._lock:
            if isinstance(service_type, str):
                self._by_name[service_type] = _ServiceEntry(
                    lifetime=ServiceLifetime.TRANSIENT,
                    factory=factory_or_type,
                    name=service_type,
                )
            else:
                self._services[service_type] = _ServiceEntry(
                    lifetime=ServiceLifetime.TRANSIENT,
                    service_type=factory_or_type
                    if isinstance(factory_or_type, type)
                    else None,
                    factory=factory_or_type
                    if not isinstance(factory_or_type, type)
                    else None,
                )

    def register_scoped(
        self,
        service_type: type | str,
        factory: Callable,
    ) -> None:
        """注册作用域单例（v2.1 新增）"""
        with self._lock:
            if isinstance(service_type, str):
                self._by_name[service_type] = _ServiceEntry(
                    lifetime=ServiceLifetime.SCOPED,
                    factory=factory,
                    name=service_type,
                )
            else:
                self._services[service_type] = _ServiceEntry(
                    lifetime=ServiceLifetime.SCOPED,
                    service_type=service_type,
                    factory=factory,
                )

    def register_factory(
        self,
        service_type: type | str,
        factory: Callable,
    ) -> None:
        """注册工厂 - 兼容 v1.x"""
        with self._lock:
            if isinstance(service_type, str):
                self._by_name[service_type] = _ServiceEntry(
                    lifetime=ServiceLifetime.FACTORY,
                    factory=factory,
                    name=service_type,
                )
            else:
                self._services[service_type] = _ServiceEntry(
                    lifetime=ServiceLifetime.FACTORY,
                    factory=factory,
                )

    # ────────────────────────────────────────────────
    # 解析
    # ────────────────────────────────────────────────

    def get(self, service_type: type) -> Any | None:
        """获取服务 - 兼容 v1.x"""
        with self._lock:
            entry = self._services.get(service_type)
        if entry is None:
            return None
        return self._resolve(entry)

    def get_by_name(self, name: str) -> Any | None:
        """按名称获取 - 兼容 v1.x"""
        with self._lock:
            entry = self._by_name.get(name)
        if entry is None:
            return None
        return self._resolve(entry)

    def resolve(self, service_type: type | str) -> Any:
        """强制解析（不存在抛 KeyError）"""
        if isinstance(service_type, str):
            instance = self.get_by_name(service_type)
        else:
            instance = self.get(service_type)
        if instance is None:
            raise KeyError(f"Service not found: {service_type}")
        return instance

    def get_or_create(self, service_type: type, factory: Callable) -> Any:
        """获取或创建 - 兼容 v1.x"""
        with self._lock:
            if service_type in self._services:
                return self._resolve(self._services[service_type])
        instance = factory()
        self.register_singleton(service_type, instance)
        return instance

    def _resolve(self, entry: _ServiceEntry) -> Any:
        if entry.lifetime == ServiceLifetime.SINGLETON:
            instance = entry.instance
        elif entry.lifetime == ServiceLifetime.SCOPED:
            instance = self._resolve_scoped(entry)
        elif entry.lifetime == ServiceLifetime.TRANSIENT:
            if entry.service_type is not None and isinstance(entry.service_type, type):
                instance = entry.service_type()
            elif entry.factory is not None:
                instance = entry.factory()
            else:
                instance = entry.instance
        elif entry.lifetime == ServiceLifetime.FACTORY:
            instance = entry.factory()  # type: ignore[misc]
        else:
            instance = entry.instance  # type: ignore[unreachable]
        # 触发钩子
        self._fire_resolve_hooks(entry, instance)
        return instance

    def _resolve_scoped(self, entry: _ServiceEntry) -> Any:
        # 在当前 scope 内缓存
        if not self._scope_stack:
            return self._fresh_instance(entry)
        scope = self._scope_stack[-1]
        key: Any = entry.name if entry.name is not None else entry.service_type
        if key in scope:
            return scope[key]
        instance = self._fresh_instance(entry)
        scope[key] = instance
        return instance

    def _fresh_instance(self, entry: _ServiceEntry) -> Any:
        if entry.service_type is not None and isinstance(entry.service_type, type):
            return entry.service_type()
        if entry.factory is not None:
            return entry.factory()
        return entry.instance

    # ────────────────────────────────────────────────
    # 作用域 (v2.1)
    # ────────────────────────────────────────────────

    @contextmanager
    def enter_scope(self) -> Iterator[DIContainer]:
        """进入作用域（上下文退出自动清理）"""
        scope_dict: dict[Any, Any] = {}
        self._scope_stack.append(scope_dict)
        try:
            yield self
        finally:
            if self._scope_stack:
                self._scope_stack.pop()

    def current_scope(self) -> dict[Any, Any] | None:
        return self._scope_stack[-1] if self._scope_stack else None

    # ────────────────────────────────────────────────
    # 钩子
    # ────────────────────────────────────────────────

    def on_resolve(self, callback: Callable[[str, Any], None]) -> None:
        """注册解析钩子"""
        self._resolve_hooks.append(callback)

    def _fire_resolve_hooks(self, entry: _ServiceEntry, instance: Any) -> None:
        if not self._resolve_hooks:
            return
        if entry.name is not None:
            name: str = entry.name
        elif entry.service_type is not None:
            name = entry.service_type.__name__
        else:
            name = "?"
        for cb in self._resolve_hooks:
            try:
                cb(name, instance)
            except Exception as e:
                logger.debug(f"DI resolve hook failed: {e}")

    # ────────────────────────────────────────────────
    # 查询 / 清理
    # ────────────────────────────────────────────────

    def has(self, service_type: type) -> bool:
        return service_type in self._services

    def has_by_name(self, name: str) -> bool:
        return name in self._by_name

    def get_lifetime(self, service_type: type) -> str | None:
        entry = self._services.get(service_type)
        return entry.lifetime.value if entry else None

    def remove(self, service_type: type) -> None:
        self._services.pop(service_type, None)

    def remove_by_name(self, name: str) -> None:
        self._by_name.pop(name, None)

    def clear(self) -> None:
        with self._lock:
            self._services.clear()
            self._by_name.clear()
            self._scope_stack.clear()

    def all_names(self) -> list[str]:
        return list(self._by_name.keys())

    def all_types(self) -> list[type]:
        return list(self._services.keys())


# ──────────────────────────────────────────────────────────
# 装饰器：自动注入
# ──────────────────────────────────────────────────────────


def inject(container: DIContainer, service_name: str | type):
    """
    装饰器：自动注入服务到被装饰函数的第一个参数位置

    用法::

        @inject(container, MyService)
        def handle(event, svc: MyService = None):  # svc 会被注入
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if isinstance(service_name, str):
                instance = container.get_by_name(service_name)
            else:
                instance = container.get(service_name)
            kwargs.setdefault(
                "_inject_target"
                if service_name == "_inject_target"
                else (
                    func.__annotations__.get("inject_param")
                    or next(iter(func.__annotations__), None)
                    or "service"
                ),
                instance,
            )
            return func(*args, **kwargs)

        return wrapper

    return decorator


# ──────────────────────────────────────────────────────────
# 全局应用容器（v2.1）
# ──────────────────────────────────────────────────────────


_global_container: DIContainer | None = None
_global_container_lock = threading.Lock()


def get_app_container() -> DIContainer:
    """获取应用级 DI 容器（v2.1 单例）"""
    global _global_container
    if _global_container is None:
        with _global_container_lock:
            if _global_container is None:
                _global_container = DIContainer(name="app")
                # v2.1: 自动注入事件总线
                try:
                    from scenefab.core.unified_event_bus import get_event_bus

                    _global_container.register_singleton("event_bus", get_event_bus())
                    _global_container.register_singleton(
                        type(get_event_bus()), get_event_bus()
                    )
                except ImportError:
                    pass
    return _global_container


def set_app_container(container: DIContainer) -> None:
    """注入自定义应用容器（v2.1 测试 / DI 友好）"""
    global _global_container
    with _global_container_lock:
        _global_container = container


__all__ = [
    "DIContainer",
    "ServiceLifetime",
    "inject",
    "get_app_container",
    "set_app_container",
]
