#!/usr/bin/env python3
"""
SceneFab 核心模块（兼容层 - 已废弃）
请直接导入 scenefab.service_container 或 scenefab.core
"""
import warnings

warnings.warn(
    "scenefab.engine is deprecated. "
    "Use scenefab.service_container for ServiceContainer, "
    "or scenefab.core for EventBus/ApplicationState.",
    DeprecationWarning,
    stacklevel=2,
)

# 透明代理到增强版实现
from scenefab.service_container import (
    ServiceContainer as ServiceContainer,
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

# 保持旧 API 的全局实例（来自 service_container）
from scenefab import service_container

__all__ = [
    "ServiceContainer",  # 来自 service_container.py（增强版）
    "ServiceLifetime",
    "_ServiceEntry",
    "EventBus",
    "EventEmitter",
    "ApplicationState",
    "ErrorInfo",
    "event_bus",
    "service_container",
]