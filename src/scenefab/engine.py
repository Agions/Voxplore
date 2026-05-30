"""
SceneFab 核心模块（兼容层）

已迁移至 scenefab.service_container 或 scenefab.core
"""
from scenefab.service_container import (
    ServiceContainer,
    ServiceLifetime,
    _ServiceEntry,
)
from scenefab.core import (
    EventBus,
    EventEmitter,
    ApplicationState,
    ErrorInfo,
    event_bus,
)
from scenefab import service_container

__all__ = [
    "ServiceContainer",
    "ServiceLifetime",
    "_ServiceEntry",
    "EventBus",
    "EventEmitter",
    "ApplicationState",
    "ErrorInfo",
    "event_bus",
    "service_container",
]