#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
服务注册表数据模型

定义服务注册、依赖注入和生命周期管理相关的数据结构。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List, Optional, Type


class ServiceState(Enum):
    """服务状态"""
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    READY = "ready"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ServiceLifetime(Enum):
    """服务生命周期类型"""
    SINGLETON = "singleton"  # 单例，整个应用生命周期内唯一
    TRANSIENT = "transient"  # 瞬态，每次请求都创建新实例
    SCOPED = "scoped"        # 作用域，在特定作用域内唯一


@dataclass
class ServiceDependency:
    """服务依赖定义"""
    service_name: str
    required: bool = True  # 是否必需
    lazy: bool = False     # 是否延迟加载


@dataclass
class ServiceDefinition:
    """服务定义"""
    name: str
    service_type: Type
    factory: Optional[Callable] = None
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON
    dependencies: List[ServiceDependency] = field(default_factory=list)
    auto_start: bool = False
    priority: int = 0  # 初始化优先级，数值越小优先级越高
    config_section: Optional[str] = None  # 配置节名称
    thread_safe: bool = True  # 是否线程安全
    health_check: Optional[Callable] = None  # 健康检查函数


class ServiceLifecycleHook(ABC):
    """服务生命周期钩子基类"""

    @abstractmethod
    def before_register(self, definition: ServiceDefinition) -> None:
        """注册前钩子"""
        pass

    @abstractmethod
    def after_register(self, definition: ServiceDefinition) -> None:
        """注册后钩子"""
        pass

    @abstractmethod
    def before_init(self, definition: ServiceDefinition) -> None:
        """初始化前钩子"""
        pass

    @abstractmethod
    def after_init(self, definition: ServiceDefinition, instance: Any) -> None:
        """初始化后钩子"""
        pass

    @abstractmethod
    def before_start(self, definition: ServiceDefinition, instance: Any) -> None:
        """启动前钩子"""
        pass

    @abstractmethod
    def after_start(self, definition: ServiceDefinition, instance: Any) -> None:
        """启动后钩子"""
        pass

    @abstractmethod
    def before_stop(self, definition: ServiceDefinition, instance: Any) -> None:
        """停止前钩子"""
        pass

    @abstractmethod
    def after_stop(self, definition: ServiceDefinition, instance: Any) -> None:
        """停止后钩子"""
        pass


class ServiceError(Exception):
    """服务相关错误基类"""
    pass


class ServiceNotFoundError(ServiceError):
    """服务未找到错误"""
    pass


class ServiceDependencyError(ServiceError):
    """服务依赖错误"""
    pass


class ServiceInitializationError(ServiceError):
    """服务初始化错误"""
    pass


class ServiceTimeoutError(ServiceError):
    """服务操作超时错误"""
    pass


__all__ = [
    "ServiceState",
    "ServiceLifetime",
    "ServiceDependency",
    "ServiceDefinition",
    "ServiceLifecycleHook",
    "ServiceError",
    "ServiceNotFoundError",
    "ServiceDependencyError",
    "ServiceInitializationError",
    "ServiceTimeoutError",
]
