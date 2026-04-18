#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能基准测试
"""

import pytest
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class BenchmarkSuite:
    """基准测试套件"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """设置"""
        self.results = {}
        
    def benchmark(self, name, func, *args, **kwargs):
        """运行基准测试"""
        # 预热
        for _ in range(3):
            func(*args, **kwargs)
            
        # 正式测试
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        
        self.results[name] = duration
        return result, duration


class TestPerformanceBenchmarks:
    """性能基准测试"""
    
    def test_cache_performance(self):
        """缓存性能测试"""
        from app.utils.performance import MemoryCache
        
        cache = MemoryCache(max_size=1000, ttl=60)
        
        # 写入性能
        start = time.perf_counter()
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")
        write_time = time.perf_counter() - start
        
        # 读取性能
        start = time.perf_counter()
        for i in range(1000):
            cache.get(f"key_{i}")
        read_time = time.perf_counter() - start
        
        print(f"Cache write: {write_time*1000:.2f}ms")
        print(f"Cache read: {read_time*1000:.2f}ms")
        
        assert write_time < 1.0  # 写入应在1秒内
        assert read_time < 0.5   # 读取应在0.5秒内

    def test_task_creation(self):
        """任务创建性能"""
        from app.utils.task_manager import Task
        
        start = time.perf_counter()
        for i in range(1000):
            _ = Task(id=f"task_{i}", name=f"Task {i}")
        duration = time.perf_counter() - start
        
        print(f"1000 task creations: {duration*1000:.2f}ms")
        
        assert duration < 1.0


class TestMemoryBenchmarks:
    """内存基准测试"""
    
    def test_cache_memory(self):
        """缓存内存使用"""
        import sys
        from app.utils.performance import MemoryCache
        
        cache = MemoryCache(max_size=10000, ttl=60)
        
        # 填充缓存
        for i in range(10000):
            cache.set(f"key_{i}", "x" * 100)  # 100 bytes each
        
        # 获取大小
        stats = cache.get_stats()
        
        print(f"Cache size: {stats['size']} items")
        assert stats['size'] > 9000  # 至少90%的缓存被使用


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
