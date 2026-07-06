"""
SingletonMeta - 消除项目中重复的单例 __new__/__init__ 守卫模式

使用示例::

    class MyService(metaclass=SingletonMeta):
        def _init_singleton(self) -> None:
            # 只在首次实例化时执行
            self.data = {}

    MyService()  # 首次创建
    MyService()  # 返回同一实例, _init_singleton 不会再次执行
"""

from __future__ import annotations

import threading
from typing import Any


class SingletonMeta(type):
    """
    线程安全的单例元类.

    替代项目中 6+ 处重复的 __new__ + _initialized 守卫模式:
        _instance = None
        _lock = threading.Lock()
        def __new__(cls):
            if cls._instance is None:
                with cls._lock:
                    if cls._instance is None:
                        cls._instance = super().__new__(cls)
                        cls._instance._initialized = False
            return cls._instance
        def __init__(self):
            if self._initialized: return
            self._initialized = True
            ...

    子类只需覆写 _init_singleton() 即可, 无需手动管理 _instance/_lock/_initialized.
    """

    _instances: dict[type, Any] = {}
    _lock = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            with cls._lock:
                # 双重检查锁定
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
                    # 触发一次性初始化钩子（子类可覆写 _init_singleton）
                    init = getattr(instance, "_init_singleton", None)
                    if callable(init):
                        init()
        return cls._instances[cls]


