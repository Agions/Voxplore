from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ServiceLifetime(str, Enum):
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    FACTORY = "factory"


@dataclass
class _ServiceEntry:
    lifetime: ServiceLifetime
    instance: Any = None
    service_type: type | None = None
    factory: Callable | None = None
    name: str | None = None


class DIContainer:
    def __init__(self, *, name: str = "default"):
        self._name = name
        self._services: dict[type, _ServiceEntry] = {}
        self._by_name: dict[str, _ServiceEntry] = {}
        self._lock = threading.RLock()

    def _register_entry(self, service_key: type | str, entry: _ServiceEntry) -> None:
        if isinstance(service_key, str):
            entry.name = service_key
            self._by_name[service_key] = entry
        else:
            entry.service_type = service_key
            self._services[service_key] = entry

    def register(self, service_type: type, instance: Any) -> None:
        with self._lock:
            self._register_entry(
                service_type,
                _ServiceEntry(lifetime=ServiceLifetime.SINGLETON, instance=instance),
            )

    def register_by_name(self, name: str, instance: Any) -> None:
        with self._lock:
            self._register_entry(
                name,
                _ServiceEntry(lifetime=ServiceLifetime.SINGLETON, instance=instance),
            )

    def register_singleton(
        self,
        service_type: type | str,
        instance: Any,
    ) -> None:
        with self._lock:
            self._register_entry(
                service_type,
                _ServiceEntry(lifetime=ServiceLifetime.SINGLETON, instance=instance),
            )

    def register_transient(
        self,
        service_type: type | str,
        factory_or_type: type | Callable,
    ) -> None:
        entry = _ServiceEntry(lifetime=ServiceLifetime.TRANSIENT)
        if isinstance(factory_or_type, type):
            entry.service_type = factory_or_type
        else:
            entry.factory = factory_or_type
        with self._lock:
            self._register_entry(service_type, entry)

    def register_factory(
        self,
        service_type: type | str,
        factory: Callable,
    ) -> None:
        with self._lock:
            self._register_entry(
                service_type,
                _ServiceEntry(lifetime=ServiceLifetime.FACTORY, factory=factory),
            )

    def get(self, service_type: type) -> Any | None:
        with self._lock:
            entry = self._services.get(service_type)
        if entry is None:
            return None
        return self._resolve(entry)

    def get_by_name(self, name: str) -> Any | None:
        with self._lock:
            entry = self._by_name.get(name)
        if entry is None:
            return None
        return self._resolve(entry)

    def resolve(self, service_type: type | str) -> Any:
        if isinstance(service_type, str):
            instance = self.get_by_name(service_type)
        else:
            instance = self.get(service_type)
        if instance is None:
            name = service_type if isinstance(service_type, str) else getattr(service_type, "__name__", str(service_type))
            from app.core.exceptions import ServiceNotFoundError
            raise ServiceNotFoundError(name)
        return instance

    def get_required(self, service_type: type | str) -> Any:
        """获取必需服务，如果未注册则抛出 ServiceNotFoundError 异常。"""
        return self.resolve(service_type)

    def get_or_create(self, service_type: type, factory: Callable) -> Any:
        with self._lock:
            if service_type in self._services:
                return self._resolve(self._services[service_type])
        instance = factory()
        self.register_singleton(service_type, instance)
        return instance

    def _resolve(self, entry: _ServiceEntry) -> Any:
        if entry.lifetime == ServiceLifetime.SINGLETON:
            return entry.instance
        elif entry.lifetime == ServiceLifetime.TRANSIENT:
            if entry.service_type is not None and isinstance(entry.service_type, type):
                return entry.service_type()
            elif entry.factory is not None:
                return entry.factory()
            return entry.instance
        elif entry.lifetime == ServiceLifetime.FACTORY:
            return entry.factory()
        return entry.instance

    def has(self, service_type: type) -> bool:
        return service_type in self._services

    def has_by_name(self, name: str) -> bool:
        return name in self._by_name

    def remove(self, service_type: type) -> None:
        self._services.pop(service_type, None)

    def remove_by_name(self, name: str) -> None:
        self._by_name.pop(name, None)

    def clear(self) -> None:
        with self._lock:
            self._services.clear()
            self._by_name.clear()

    def all_names(self) -> list[str]:
        return list(self._by_name.keys())

    def all_types(self) -> list[type]:
        return list(self._services.keys())


_global_container: DIContainer | None = None
_global_container_lock = threading.Lock()


def get_app_container() -> DIContainer:
    global _global_container
    if _global_container is None:
        with _global_container_lock:
            if _global_container is None:
                _global_container = DIContainer(name="app")
                try:
                    from app.core.unified_event_bus import get_event_bus

                    _global_container.register_singleton("event_bus", get_event_bus())
                    _global_container.register_singleton(
                        type(get_event_bus()), get_event_bus()
                    )
                except ImportError:
                    pass
    return _global_container


def set_app_container(container: DIContainer) -> None:
    global _global_container
    with _global_container_lock:
        _global_container = container


__all__ = [
    "DIContainer",
    "ServiceLifetime",
    "get_app_container",
    "set_app_container",
]
