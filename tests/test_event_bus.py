#!/usr/bin/env python3
"""测试事件总线"""

import pytest
from app.core.event_bus import EventBus


class TestEventBus:
    """测试事件总线"""

    def test_init(self):
        """测试初始化"""
        bus = EventBus()
        assert bus._handlers == {}

    def test_subscribe(self):
        """测试订阅"""
        bus = EventBus()
        def handler(x):
            return x
        
        bus.subscribe("test_event", handler)
        
        assert "test_event" in bus._handlers
        assert handler in bus._handlers["test_event"]

    def test_unsubscribe(self):
        """测试取消订阅"""
        bus = EventBus()
        def handler(x):
            return x
        
        bus.subscribe("test_event", handler)
        bus.unsubscribe("test_event", handler)
        
        assert handler not in bus._handlers.get("test_event", [])

    def test_publish(self):
        """测试发布"""
        bus = EventBus()
        result = []
        
        def handler(data):
            result.append(data)
        
        bus.subscribe("test_event", handler)
        bus.publish("test_event", "hello")
        
        assert result == ["hello"]

    def test_publish_without_data(self):
        """测试无数据发布"""
        bus = EventBus()
        result = []
        
        def handler(data):
            result.append(data)
        
        bus.subscribe("test_event", handler)
        bus.publish("test_event")
        
        assert result == [None]

    def test_multiple_handlers(self):
        """测试多个处理器"""
        bus = EventBus()
        result1 = []
        result2 = []
        
        def handler1(data):
            result1.append(data)
        
        def handler2(data):
            result2.append(data)
        
        bus.subscribe("test_event", handler1)
        bus.subscribe("test_event", handler2)
        bus.publish("test_event", "data")
        
        assert result1 == ["data"]
        assert result2 == ["data"]

    def test_duplicate_subscription(self):
        """测试重复订阅"""
        bus = EventBus()
        def handler(x):
            return x
        
        bus.subscribe("test_event", handler)
        bus.subscribe("test_event", handler)
        
        assert len(bus._handlers["test_event"]) == 1

    def test_clear_event_handlers(self):
        """测试清除事件处理器"""
        bus = EventBus()
        
        bus.subscribe("event1", lambda x: x)
        bus.subscribe("event2", lambda x: x)
        
        bus._handlers.clear()
        
        assert len(bus._handlers) == 0
