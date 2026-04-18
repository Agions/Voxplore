#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 事件总线模块
提供事件发布/订阅功能
"""

import threading
from typing import Dict, List, Callable, Any
from contextlib import contextmanager
from .logger import Logger


class EventBus:
    """事件总线（线程安全）"""

    def __init__(self):
        """初始化事件总线"""
        self._handlers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self.logger = Logger("EventBus")

    def subscribe(self, event_name: str, handler: Callable) -> None:
        """订阅事件（线程安全）
        
        Args:
            event_name: 事件名称
            handler: 事件处理函数
        """
        with self._lock:
            if event_name not in self._handlers:
                self._handlers[event_name] = []
            
            # 避免重复订阅
            if handler not in self._handlers[event_name]:
                self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Callable) -> None:
        """取消订阅事件（线程安全）
        
        Args:
            event_name: 事件名称
            handler: 事件处理函数
        """
        with self._lock:
            if event_name in self._handlers:
                try:
                    self._handlers[event_name].remove(handler)
                except ValueError:
                    logger.debug("Handler not found for removal, ignoring")

    def publish(self, event_name: str, data: Any = None) -> None:
        """发布事件（线程安全）
        
        Args:
            event_name: 事件名称
            data: 事件数据，可选
        """
        with self._lock:
            handlers = self._handlers.get(event_name, []).copy()
        
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                self.logger.error(f"事件 {event_name} 处理错误: {e}")

    def subscribe_once(self, event_name: str, handler: Callable) -> None:
        """订阅事件，但只在第一次发布时触发，之后自动取消订阅（线程安全）
        
        Args:
            event_name: 事件名称
            handler: 事件处理函数
        """
        def wrapper(data):
            try:
                handler(data)
            finally:
                self.unsubscribe(event_name, wrapper)
        
        with self._lock:
            if event_name not in self._handlers:
                self._handlers[event_name] = []
            self._handlers[event_name].append(wrapper)

    @contextmanager
    def temporary_handler(self, event_name: str, handler: Callable):
        """上下文管理器：临时添加事件处理器，退出时自动移除
        
        Args:
            event_name: 事件名称
            handler: 事件处理函数
        
        Usage:
            with event_bus.temporary_handler("my_event", my_handler):
                event_bus.publish("my_event", data)
            # handler 已自动移除
        """
        self.subscribe(event_name, handler)
        try:
            yield
        finally:
            self.unsubscribe(event_name, handler)

    def emit(self, event_name: str, data: Any = None) -> None:
        """发布事件（emit是publish的别名，保持API兼容性）
        
        Args:
            event_name: 事件名称
            data: 事件数据，可选
        """
        self.publish(event_name, data)

    def clear_handlers(self, event_name: str = None) -> None:
        """清除事件处理器（线程安全）
        
        Args:
            event_name: 可选，指定事件名称，若为None则清除所有事件处理器
        """
        with self._lock:
            if event_name:
                if event_name in self._handlers:
                    self._handlers[event_name].clear()
            else:
                self._handlers.clear()

    def unsubscribe_all(self, event_name: str) -> int:
        """取消订阅指定事件的所有处理器（线程安全）
        
        Args:
            event_name: 事件名称
        
        Returns:
            int: 被移除的处理器数量
        """
        with self._lock:
            if event_name in self._handlers:
                count = len(self._handlers[event_name])
                self._handlers[event_name].clear()
                return count
            return 0

    def get_handler_count(self, event_name: str = None) -> int:
        """获取事件处理器数量（线程安全）
        
        Args:
            event_name: 可选，指定事件名称，若为None则返回所有事件处理器总数
        
        Returns:
            int: 事件处理器数量
        """
        with self._lock:
            if event_name:
                return len(self._handlers.get(event_name, []))
            else:
                return sum(len(handlers) for handlers in self._handlers.values())

    def has_handlers(self, event_name: str) -> bool:
        """检查事件是否有处理器（线程安全）
        
        Args:
            event_name: 事件名称
        
        Returns:
            bool: 若事件有处理器则返回True，否则返回False
        """
        with self._lock:
            return event_name in self._handlers and len(self._handlers[event_name]) > 0

    def get_registered_events(self) -> List[str]:
        """获取所有已注册的事件名称列表（线程安全）
        
        Returns:
            List[str]: 事件名称列表
        """
        with self._lock:
            return list(self._handlers.keys())