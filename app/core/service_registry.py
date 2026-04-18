#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 服务注册表 - 高级服务管理系统
支持依赖注入、生命周期管理、配置驱动的服务初始化
"""

import inspect
import threading
from typing import Dict, List, Type, Any, Optional, Callable, TypeVar
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from .logger import Logger
from .event_bus import EventBus
from .registry_models import (
    ServiceState,
    ServiceLifetime,
    ServiceDependency,
    ServiceDefinition,
    ServiceLifecycleHook,
    ServiceError,
    ServiceNotFoundError,
    ServiceDependencyError,
    ServiceInitializationError,
    ServiceTimeoutError,
)


T = TypeVar('T')


class ServiceRegistry:
    """高级服务注册表"""

    def __init__(self, logger: Logger, event_bus: EventBus):
        self._logger = logger
        self._event_bus = event_bus

        # 服务注册表
        self._definitions: Dict[str, ServiceDefinition] = {}
        self._instances: Dict[str, Any] = {}
        self._scoped_instances: Dict[str, Dict[str, Any]] = {}

        # 服务状态管理
        self._states: Dict[str, ServiceState] = {}
        self._initialization_lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ServiceInit")

        # 生命周期钩子
        self._hooks: List[ServiceLifecycleHook] = []

        # 配置
        self._config: Dict[str, Any] = {}

        # 统计信息
        self._stats = {
            "total_services": 0,
            "running_services": 0,
            "failed_services": 0,
            "initialization_time": {}
        }

    def register(self, definition: ServiceDefinition) -> None:
        """注册服务"""
        with self._initialization_lock:
            if definition.name in self._definitions:
                self._logger.warning(f"Service {definition.name} already registered, overwriting")

            # 执行注册前钩子
            for hook in self._hooks:
                hook.before_register(definition)

            # 验证依赖
            self._validate_dependencies(definition)

            # 注册服务
            self._definitions[definition.name] = definition
            self._states[definition.name] = ServiceState.REGISTERED
            self._stats["total_services"] += 1

            # 执行注册后钩子
            for hook in self._hooks:
                hook.after_register(definition)

            self._logger.info(f"Service {definition.name} registered successfully")
            self._event_bus.publish("service.registered", {"name": definition.name})

    def register_singleton(self, name: str, service_type: Type,
                          factory: Optional[Callable] = None,
                          dependencies: Optional[List[str]] = None,
                          auto_start: bool = False,
                          priority: int = 0) -> None:
        """注册单例服务（便捷方法）"""
        deps = []
        if dependencies:
            deps = [ServiceDependency(dep) for dep in dependencies]

        definition = ServiceDefinition(
            name=name,
            service_type=service_type,
            factory=factory,
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=deps,
            auto_start=auto_start,
            priority=priority
        )
        self.register(definition)

    def register_transient(self, name: str, service_type: Type,
                          factory: Optional[Callable] = None,
                          dependencies: Optional[List[str]] = None) -> None:
        """注册瞬态服务（便捷方法）"""
        deps = []
        if dependencies:
            deps = [ServiceDependency(dep) for dep in dependencies]

        definition = ServiceDefinition(
            name=name,
            service_type=service_type,
            factory=factory,
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=deps,
            auto_start=False,
            priority=0
        )
        self.register(definition)

    def get(self, service_name: str, scope: Optional[str] = None) -> Any:
        """获取服务实例"""
        if service_name not in self._definitions:
            raise ServiceNotFoundError(f"Service {service_name} not registered")

        definition = self._definitions[service_name]

        if definition.lifetime == ServiceLifetime.TRANSIENT:
            return self._create_instance(definition)
        elif definition.lifetime == ServiceLifetime.SCOPED:
            if not scope:
                raise ServiceError(f"Scope required for scoped service {service_name}")
            return self._get_scoped_instance(definition, scope)
        else:  # SINGLETON
            return self._get_singleton_instance(definition)

    def get_async(self, service_name: str, timeout: float = 10.0,
                  scope: Optional[str] = None) -> Any:
        """异步获取服务实例"""
        future = self._executor.submit(self.get, service_name, scope)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            raise ServiceTimeoutError(f"Timeout getting service {service_name}")

    def start_service(self, service_name: str, timeout: float = 30.0) -> bool:
        """启动服务"""
        if service_name not in self._definitions:
            raise ServiceNotFoundError(f"Service {service_name} not registered")

        if self._states.get(service_name) == ServiceState.RUNNING:
            return True

        definition = self._definitions[service_name]

        try:
            future = self._executor.submit(self._initialize_and_start_service, definition)
            result = future.result(timeout=timeout)

            if result:
                self._stats["running_services"] += 1
                self._event_bus.publish("service.started", {"name": service_name})

            return result

        except FutureTimeoutError:
            self._states[service_name] = ServiceState.ERROR
            self._stats["failed_services"] += 1
            self._event_bus.publish("service.error", {"name": service_name, "error": "timeout"})
            raise ServiceTimeoutError(f"Timeout starting service {service_name}")

    def start_all_services(self, timeout: float = 60.0) -> Dict[str, bool]:
        """启动所有自动启动的服务"""
        results = {}

        # 按优先级排序
        auto_services = [
            (name, defn) for name, defn in self._definitions.items()
            if defn.auto_start
        ]
        auto_services.sort(key=lambda x: x[1].priority)

        futures = {}
        for name, definition in auto_services:
            if self._states.get(name) not in [ServiceState.RUNNING]:
                future = self._executor.submit(self.start_service, name, timeout)
                futures[future] = name

        # 等待所有服务启动完成
        for future in futures:
            service_name = futures[future]
            try:
                results[service_name] = future.result(timeout=timeout)
            except Exception as e:
                self._logger.error(f"Failed to start service {service_name}: {e}")
                results[service_name] = False

        return results

    def stop_service(self, service_name: str, timeout: float = 30.0) -> bool:
        """停止服务"""
        if service_name not in self._definitions:
            raise ServiceNotFoundError(f"Service {service_name} not registered")

        definition = self._definitions[service_name]
        current_state = self._states.get(service_name)

        if current_state in [ServiceState.REGISTERED, ServiceState.STOPPED]:
            return True

        if current_state != ServiceState.RUNNING:
            self._logger.warning(f"Service {service_name} is not running (state: {current_state})")
            return False

        try:
            self._states[service_name] = ServiceState.STOPPING

            # 执行停止前钩子
            for hook in self._hooks:
                hook.before_stop(definition, self._instances.get(service_name))

            instance = self._instances.get(service_name)
            if instance and hasattr(instance, 'stop'):
                future = self._executor.submit(instance.stop)
                future.result(timeout=timeout)

            self._states[service_name] = ServiceState.STOPPED
            self._stats["running_services"] -= 1

            # 执行停止后钩子
            for hook in self._hooks:
                hook.after_stop(definition, instance)

            self._logger.info(f"Service {service_name} stopped successfully")
            self._event_bus.publish("service.stopped", {"name": service_name})
            return True

        except FutureTimeoutError:
            self._states[service_name] = ServiceState.ERROR
            raise ServiceTimeoutError(f"Timeout stopping service {service_name}")

    def stop_all_services(self, timeout: float = 60.0) -> Dict[str, bool]:
        """停止所有运行中的服务"""
        results = {}

        # 按优先级逆序停止（低优先级先停止）
        running_services = [
            (name, defn) for name, defn in self._definitions.items()
            if self._states.get(name) == ServiceState.RUNNING
        ]
        running_services.sort(key=lambda x: x[1].priority, reverse=True)

        futures = {}
        for name, definition in running_services:
            future = self._executor.submit(self.stop_service, name, timeout)
            futures[future] = name

        # 等待所有服务停止完成
        for future in futures:
            service_name = futures[future]
            try:
                results[service_name] = future.result(timeout=timeout)
            except Exception as e:
                self._logger.error(f"Failed to stop service {service_name}: {e}")
                results[service_name] = False

        return results

    def health_check(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """服务健康检查"""
        if service_name:
            return self._check_single_service_health(service_name)
        else:
            return self._check_all_services_health()

    def add_hook(self, hook: ServiceLifecycleHook) -> None:
        """添加生命周期钩子"""
        self._hooks.append(hook)

    def remove_hook(self, hook: ServiceLifecycleHook) -> None:
        """移除生命周期钩子"""
        if hook in self._hooks:
            self._hooks.remove(hook)

    def get_service_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取服务信息"""
        if service_name not in self._definitions:
            return None

        definition = self._definitions[service_name]
        state = self._states.get(service_name)

        return {
            "name": definition.name,
            "type": definition.service_type.__name__,
            "lifetime": definition.lifetime.value,
            "state": state.value if state else "unknown",
            "dependencies": [dep.service_name for dep in definition.dependencies],
            "auto_start": definition.auto_start,
            "priority": definition.priority,
            "initialized": service_name in self._instances,
            "initialization_time": self._stats["initialization_time"].get(service_name, 0)
        }

    def get_all_services_info(self) -> Dict[str, Any]:
        """获取所有服务信息"""
        return {
            name: self.get_service_info(name)
            for name in self._definitions.keys()
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "states": {state.value: sum(1 for s in self._states.values() if s == state)
                     for state in ServiceState}
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        """设置配置"""
        self._config = config
        self._event_bus.publish("service.config_updated", config)

    def cleanup(self) -> None:
        """清理资源"""
        self.stop_all_services()
        self._executor.shutdown(wait=True)
        self._instances.clear()
        self._scoped_instances.clear()

    # 私有方法

    def _validate_dependencies(self, definition: ServiceDefinition) -> None:
        """验证服务依赖"""
        for dep in definition.dependencies:
            if dep.required and dep.service_name not in self._definitions:
                if dep.service_name != definition.name:  # 不验证自引用
                    raise ServiceDependencyError(
                        f"Required dependency {dep.service_name} not found for service {definition.name}"
                    )

    def _resolve_dependencies(self, definition: ServiceDefinition) -> Dict[str, Any]:
        """解析服务依赖"""
        dependencies = {}

        for dep in definition.dependencies:
            if not dep.required:
                try:
                    dependencies[dep.service_name] = self.get(dep.service_name)
                except ServiceNotFoundError:
                    pass
            else:
                dependencies[dep.service_name] = self.get(dep.service_name)

        return dependencies

    def _create_instance(self, definition: ServiceDefinition) -> Any:
        """创建服务实例"""
        try:
            # 解析依赖
            dependencies = self._resolve_dependencies(definition)

            # 创建实例
            if definition.factory:
                # 使用工厂函数
                sig = inspect.signature(definition.factory)
                kwargs = {}
                for param_name, param in sig.parameters.items():
                    if param_name in dependencies:
                        kwargs[param_name] = dependencies[param_name]
                    elif param_name == "config" and definition.config_section:
                        kwargs[param_name] = self._config.get(definition.config_section, {})
                    elif param.default != inspect.Parameter.empty:
                        kwargs[param_name] = param.default

                instance = definition.factory(**kwargs)
            else:
                # 使用构造函数
                instance = definition.service_type(**dependencies)

            return instance

        except Exception as e:
            raise ServiceInitializationError(f"Failed to create instance of {definition.name}: {e}")

    def _get_singleton_instance(self, definition: ServiceDefinition) -> Any:
        """获取单例实例"""
        if definition.name in self._instances:
            return self._instances[definition.name]

        with self._initialization_lock:
            if definition.name in self._instances:
                return self._instances[definition.name]

            instance = self._create_instance(definition)
            self._instances[definition.name] = instance

            return instance

    def _get_scoped_instance(self, definition: ServiceDefinition, scope: str) -> Any:
        """获取作用域实例"""
        if scope not in self._scoped_instances:
            self._scoped_instances[scope] = {}

        scope_instances = self._scoped_instances[scope]
        if definition.name in scope_instances:
            return scope_instances[definition.name]

        instance = self._create_instance(definition)
        scope_instances[definition.name] = instance

        return instance

    def _initialize_and_start_service(self, definition: ServiceDefinition) -> bool:
        """初始化并启动服务"""
        import time
        start_time = time.time()

        try:
            # 执行初始化前钩子
            for hook in self._hooks:
                hook.before_init(definition)

            # 创建实例
            instance = self._get_singleton_instance(definition)

            # 初始化服务
            if hasattr(instance, 'initialize'):
                self._states[definition.name] = ServiceState.INITIALIZING
                instance.initialize()

            self._states[definition.name] = ServiceState.READY

            # 执行初始化后钩子
            for hook in self._hooks:
                hook.after_init(definition, instance)

            # 启动服务
            if hasattr(instance, 'start'):
                # 执行启动前钩子
                for hook in self._hooks:
                    hook.before_start(definition, instance)

                self._states[definition.name] = ServiceState.STARTING
                instance.start()
                self._states[definition.name] = ServiceState.RUNNING

                # 执行启动后钩子
                for hook in self._hooks:
                    hook.after_start(definition, instance)
            else:
                self._states[definition.name] = ServiceState.RUNNING

            # 记录初始化时间
            self._stats["initialization_time"][definition.name] = time.time() - start_time

            self._logger.info(f"Service {definition.name} initialized and started successfully")
            return True

        except Exception as e:
            self._states[definition.name] = ServiceState.ERROR
            self._stats["failed_services"] += 1
            self._logger.error(f"Failed to initialize service {definition.name}: {e}")
            self._event_bus.publish("service.error", {"name": definition.name, "error": str(e)})
            return False

    def _check_single_service_health(self, service_name: str) -> Dict[str, Any]:
        """检查单个服务健康状态"""
        if service_name not in self._definitions:
            return {"status": "not_found"}

        definition = self._definitions[service_name]
        state = self._states.get(service_name, ServiceState.UNREGISTERED)

        health_info = {
            "name": service_name,
            "state": state.value,
            "status": "healthy" if state == ServiceState.RUNNING else "unhealthy"
        }

        # 执行自定义健康检查
        if definition.health_check:
            try:
                instance = self._instances.get(service_name)
                if instance:
                    custom_health = definition.health_check(instance)
                    health_info.update(custom_health)
            except Exception as e:
                health_info["status"] = "error"
                health_info["error"] = str(e)

        return health_info

    def _check_all_services_health(self) -> Dict[str, Any]:
        """检查所有服务健康状态"""
        results = {}
        for service_name in self._definitions:
            results[service_name] = self._check_single_service_health(service_name)

        return {
            "services": results,
            "summary": {
                "total": len(results),
                "healthy": sum(1 for r in results.values() if r.get("status") == "healthy"),
                "unhealthy": sum(1 for r in results.values() if r.get("status") in ["unhealthy", "error"]),
                "not_found": sum(1 for r in results.values() if r.get("status") == "not_found")
            }
        }