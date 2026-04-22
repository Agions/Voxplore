#!/usr/bin/env python3
"""测试服务容器"""

from app.core.service_container import ServiceContainer


class TestServiceContainer:
    """测试服务容器"""

    def test_init(self):
        """测试初始化"""
        container = ServiceContainer()
        
        assert container._services == {}
        assert container._services_by_name == {}

    def test_register(self):
        """测试注册服务"""
        container = ServiceContainer()
        service = object()
        
        container.register(str, service)
        
        assert container.get(str) is service

    def test_register_by_name(self):
        """测试按名称注册"""
        container = ServiceContainer()
        service = object()
        
        container.register_by_name("my_service", service)
        
        assert container.get_by_name("my_service") is service

    def test_get_not_exists(self):
        """测试获取不存在的服务"""
        container = ServiceContainer()
        
        result = container.get(str)
        
        assert result is None

    def test_get_by_name_not_exists(self):
        """测试按名称获取不存在的服务"""
        container = ServiceContainer()
        
        result = container.get_by_name("not_exists")
        
        assert result is None

    def test_has(self):
        """测试检查服务存在"""
        container = ServiceContainer()
        service = object()
        
        container.register(str, service)
        
        assert container.has(str) is True
        assert container.has(int) is False

    def test_has_by_name(self):
        """测试按名称检查存在"""
        container = ServiceContainer()
        service = object()
        
        container.register_by_name("test", service)
        
        assert container.has_by_name("test") is True
        assert container.has_by_name("not_exists") is False

    def test_remove(self):
        """测试移除服务"""
        container = ServiceContainer()
        service = object()
        
        container.register(str, service)
        container.remove(str)
        
        assert container.get(str) is None

    def test_remove_by_name(self):
        """测试按名称移除"""
        container = ServiceContainer()
        service = object()
        
        container.register_by_name("test", service)
        container.remove_by_name("test")
        
        assert container.get_by_name("test") is None

    def test_clear(self):
        """测试清空"""
        container = ServiceContainer()
        
        container.register(str, object())
        container.register_by_name("test", object())
        container.clear()
        
        assert container.get(str) is None
        assert container.get_by_name("test") is None
