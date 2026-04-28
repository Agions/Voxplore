#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能优化模块
提供懒加载、缓存和性能监控功能
"""

import functools
import time
from typing import Any, Callable, Optional, Dict, List
from threading import Lock


class LazyLoader:
    """
    懒加载器

    延迟加载大型对象，提高启动速度
    """

    def __init__(self, loader_fn: Callable[[], Any]):
        self._loader_fn = loader_fn
        self._loaded = False
        self._instance = None
        self._lock = Lock()

    def get(self) -> Any:
        """获取实例，延迟加载"""
        if not self._loaded:
            with self._lock:
                if not self._loaded:
                    self._instance = self._loader_fn()
                    self._loaded = True
        return self._instance

    def reset(self):
        """重置加载状态"""
        with self._lock:
            self._loaded = False
            self._instance = None


class MemoryCache:
    """
    内存缓存

    简单的内存缓存，带过期时间
    """

    def __init__(self, max_size: int = 100, ttl: int = 3600):
        self._cache: Dict[str, Dict] = {}
        self._max_size = max_size
        self._ttl = ttl  # 秒
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                # 检查是否过期
                if time.time() - entry['timestamp'] < self._ttl:
                    entry['hits'] += 1
                    return entry['value']
                else:
                    del self._cache[key]
        return None

    def set(self, key: str, value: Any):
        """设置缓存"""
        with self._lock:
            # 如果满了，删除最老的
            if len(self._cache) >= self._max_size:
                oldest = min(self._cache.items(), key=lambda x: x[1]['timestamp'])
                del self._cache[oldest[0]]

            self._cache[key] = {
                'value': value,
                'timestamp': time.time(),
                'hits': 0,
            }

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> Dict:
        """获取缓存统计"""
        with self._lock:
            total_hits = sum(e['hits'] for e in self._cache.values())
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'total_hits': total_hits,
            }


def cached(cache: MemoryCache, key_fn: Optional[Callable] = None):
    """
    缓存装饰器

    Args:
        cache: MemoryCache 实例
        key_fn: 可选的键生成函数
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_fn:
                cache_key = key_fn(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # 尝试从缓存获取
            result = cache.get(cache_key)
            if result is not None:
                return result

            # 执行函数
            result = func(*args, **kwargs)

            # 存入缓存
            cache.set(cache_key, result)

            return result
        return wrapper
    return decorator


class PerformanceMonitor:
    """
    性能监控器

    监控函数执行时间和内存使用
    """

    def __init__(self):
        self._metrics: Dict[str, List[float]] = {}
        self._lock = Lock()

    def record(self, name: str, duration: float):
        """记录执行时间"""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            self._metrics[name].append(duration)

    def timing(self, name: str):
        """计时装饰器"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    return func(*args, **kwargs)
                finally:
                    duration = time.time() - start
                    self.record(name or func.__name__, duration)
            return wrapper
        return decorator

    def get_stats(self, name: str = None) -> Dict:
        """获取统计数据"""
        with self._lock:
            if name:
                times = self._metrics.get(name, [])
                if not times:
                    return {}
                return {
                    'count': len(times),
                    'total': sum(times),
                    'avg': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times),
                }
            else:
                # 返回所有
                return {
                    name: self.get_stats(name)
                    for name in self._metrics.keys()
                }

    def reset(self):
        """重置统计"""
        with self._lock:
            self._metrics.clear()


# 全局实例
default_cache = MemoryCache(max_size=200, ttl=1800)  # 30分钟
perf_monitor = PerformanceMonitor()


# 便捷装饰器
def cached_property(ttl: int = 300):
    """缓存属性装饰器"""
    cache = MemoryCache(max_size=100, ttl=ttl)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self):
            key = f"{self.__class__.__name__}.{func.__name__}"
            result = cache.get(key)
            if result is None:
                result = func(self)
                cache.set(key, result)
            return result
        return wrapper
    return decorator


def timed(name: str = None):
    """性能计时装饰器"""
    return perf_monitor.timing(name or "default")
