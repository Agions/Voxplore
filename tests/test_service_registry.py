#!/usr/bin/env python3
"""测试服务注册表"""

import pytest
from unittest.mock import Mock

from app.core.service_registry import (
    ServiceState,
    ServiceLifetime,
    ServiceDependency,
    ServiceDefinition,
    ServiceRegistry,
)


class TestServiceState:
    """测试服务状态枚举"""

    def test_all_states(self):
        """测试所有状态"""
        states = [
            ServiceState.UNREGISTERED,
            ServiceState.REGISTERED,
            ServiceState.INITIALIZING,
            ServiceState.READY,
            ServiceState.STARTING,
            ServiceState.RUNNING,
            ServiceState.STOPPING,
            ServiceState.STOPPED,
            ServiceState.ERROR,
        ]
        
        assert len(states) == 9
        assert ServiceState.READY.value == "ready"


class TestServiceLifetime:
    """测试服务生命周期枚举"""

    def test_lifetime_values(self):
        """测试生命周期值"""
        assert ServiceLifetime.SINGLETON.value == "singleton"
        assert ServiceLifetime.TRANSIENT.value == "transient"
        assert ServiceLifetime.SCOPED.value == "scoped"


class TestServiceDependency:
    """测试服务依赖"""

    def test_creation_required(self):
        """测试创建必需依赖"""
        dep = ServiceDependency("database")
        
        assert dep.service_name == "database"
        assert dep.required is True
        assert dep.lazy is False

    def test_creation_optional_lazy(self):
        """测试创建可选延迟依赖"""
        dep = ServiceDependency("cache", required=False, lazy=True)
        
        assert dep.required is False
        assert dep.lazy is True


class TestServiceDefinition:
    """测试服务定义"""

    def test_basic_creation(self):
        """测试基本创建"""
        def factory():
            return Mock()
        
        definition = ServiceDefinition(
            name="test_service",
            service_type=Mock,
            factory=factory,
            lifetime=ServiceLifetime.SINGLETON,
        )
        
        assert definition.name == "test_service"
        assert definition.service_type == Mock
        assert definition.factory is factory
        assert definition.lifetime == ServiceLifetime.SINGLETON

    def test_with_dependencies(self):
        """测试带依赖的服务定义"""
        deps = [
            ServiceDependency("db", required=True),
            ServiceDependency("cache", required=False),
        ]
        
        definition = ServiceDefinition(
            name="test",
            service_type=Mock,
            dependencies=deps,
        )
        
        assert len(definition.dependencies) == 2


class TestServiceRegistry:
    """测试服务注册表"""

    @pytest.fixture
    def registry(self):
        """创建测试用 ServiceRegistry（带 mock 依赖）"""
        from app.core.logger import Logger
        from app.core.event_bus import EventBus
        logger = Logger("test")
        event_bus = EventBus()
        return ServiceRegistry(logger=logger, event_bus=event_bus)

    def test_init(self, registry):
        """测试初始化"""
        assert isinstance(registry._definitions, dict)
        assert isinstance(registry._instances, dict)
        assert isinstance(registry._states, dict)

    def test_register_definition(self, registry):
        """测试注册服务定义"""
        definition = ServiceDefinition(
            name="test_service",
            service_type=Mock,
        )

        registry.register(definition)

        assert "test_service" in registry._definitions
        assert registry._states["test_service"] == ServiceState.REGISTERED

    def test_register_singleton(self, registry):
        """测试注册单例服务"""
        def my_factory():
            return Mock()

        registry.register_singleton(
            name="my_service",
            service_type=Mock,
            factory=my_factory,
        )

        assert "my_service" in registry._definitions

    def test_get_not_registered(self, registry):
        """测试获取未注册服务抛出异常"""
        from app.core.service_registry import ServiceNotFoundError

        with pytest.raises(ServiceNotFoundError):
            registry.get("nonexistent")

    def test_has_service(self, registry):
        """测试检查服务是否存在"""
        definition = ServiceDefinition(name="exists", service_type=Mock)
        registry.register(definition)

        assert "exists" in registry._definitions
        assert "not_exists" not in registry._definitions
