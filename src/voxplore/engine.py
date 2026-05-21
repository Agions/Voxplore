#!/usr/bin/env python3
"""
Voxplore 核心模块
包含应用生命周期管理、事件总线、服务容器
"""
import logging
import threading
from enum import Enum
from typing import Any
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class ApplicationState(Enum):
    """应用状态"""
    INITIALIZING = "initializing"
    STARTING = "starting"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"
    ERROR = "error"


@dataclass
class ErrorInfo:
    """错误信息"""
    error_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    details: str | None = None
    exception: Exception | None = None
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class EventBus:
    """
    事件总线
    提供松耦合的组件通信
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_name: str, handler: Callable) -> None:
        """订阅事件"""
        with self._lock:
            if event_name not in self._handlers:
                self._handlers[event_name] = []
            if handler not in self._handlers[event_name]:
                self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Callable) -> None:
        """取消订阅"""
        with self._lock:
            if event_name in self._handlers:
                if handler in self._handlers[event_name]:
                    self._handlers[event_name].remove(handler)

    def publish(self, event_name: str, data: Any = None) -> None:
        """发布事件（优化版 - 并行调用处理器）"""
        handlers = []
        with self._lock:
            handlers = self._handlers.get(event_name, []).copy()

        if not handlers:
            return

        # 并行调用所有处理器
        if len(handlers) > 1:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(len(handlers), 4)) as executor:
                futures = [executor.submit(self._safe_call, h, data) for h in handlers]
                for f in futures:
                    f.result()  # 等待完成以捕获异常
        else:
            self._safe_call(handlers[0], data)

    def _safe_call(self, handler: Callable, data: Any):
        """安全调用处理器"""
        try:
            handler(data)
        except Exception as e:
            logger.error(f"Event handler failed: {e}")

    def clear(self, event_name: str = None) -> None:
        """清除事件处理器"""
        with self._lock:
            if event_name:
                self._handlers.pop(event_name, None)
            else:
                self._handlers.clear()


class ServiceContainer:
    """
    服务容器
    简单的依赖注入容器
    """

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Callable] = {}
        self._lock = threading.Lock()

    def register(self, name: str, service: Any) -> None:
        """注册服务实例"""
        with self._lock:
            self._services[name] = service

    def register_factory(self, name: str, factory: Callable) -> None:
        """注册服务工厂"""
        with self._lock:
            self._factories[name] = factory

    def get(self, name: str, default: Any = None) -> Any:
        """获取服务"""
        with self._lock:
            if name in self._services:
                return self._services[name]
            if name in self._factories:
                factory = self._factories[name]
                service = factory()
                self._services[name] = service
                return service
        return default

    def has(self, name: str) -> bool:
        """检查服务是否存在"""
        with self._lock:
            return name in self._services or name in self._factories

    def unregister(self, name: str) -> None:
        """注销服务"""
        with self._lock:
            self._services.pop(name, None)
            self._factories.pop(name, None)

    def clear(self) -> None:
        """清空所有服务"""
        with self._lock:
            self._services.clear()
            self._factories.clear()


class EventEmitter:
    """
    事件发射器基类
    支持 PySide6 信号（如果可用）或其他事件系统
    """

    def __init__(self):
        self._events = EventBus()

    def on(self, event: str, handler: Callable) -> 'EventEmitter':
        """订阅事件（链式调用）"""
        self._events.subscribe(event, handler)
        return self

    def off(self, event: str, handler: Callable) -> 'EventEmitter':
        """取消订阅（链式调用）"""
        self._events.unsubscribe(event, handler)
        return self

    def emit(self, event: str, data: Any = None) -> None:
        """发射事件"""
        self._events.publish(event, data)


# 全局事件总线
event_bus = EventBus()
service_container = ServiceContainer()


__all__ = [
    "ApplicationState",
    "ErrorInfo",
    "EventBus",
    "ServiceContainer",
    "EventEmitter",
    "event_bus",
    "service_container",
]
