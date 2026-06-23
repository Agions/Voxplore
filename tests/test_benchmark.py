#!/usr/bin/env python3

"""
性能基准测试
"""

import time

import pytest


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

    def test_task_creation(self):
        """任务创建性能（v2.1 - 用 scenefab.core.task_model.UnifiedTask）"""
        from scenefab.core.task_model import UnifiedTask

        start = time.perf_counter()
        for i in range(1000):
            _ = UnifiedTask(task_id=f"task_{i}", name=f"Task {i}")
        duration = time.perf_counter() - start

        print(f"1000 task creations: {duration * 1000:.2f}ms")

        assert duration < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
