"""
SceneFab 性能基准测试套件

功能：
1. 不同时长视频处理耗时基线测试
2. CPU/GPU 双模式性能对比
3. 内存使用监控
4. 性能报告生成

测试视频规格：
- 1 分钟短视频
- 10 分钟中等视频
- 60 分钟长视频
- 90 分钟电影级视频
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    test_name: str
    video_duration: float  # 视频时长（秒）
    processing_time: float  # 处理耗时（秒）
    memory_peak: float  # 峰值内存使用（MB）
    memory_average: float  # 平均内存使用（MB）
    cpu_usage: float  # CPU 使用率（%）
    gpu_usage: float  # GPU 使用率（%），如果没有 GPU 则为 0
    throughput: float  # 吞吐量（视频秒/处理秒）
    success: bool  # 是否成功
    error_message: str = ""  # 错误信息
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_id: str
    test_time: str
    system_info: dict[str, Any]
    metrics: list[PerformanceMetrics] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


class PerformanceBenchmark:
    """
    性能基准测试套件

    用于测试 SceneFab 在不同视频规格下的处理性能。

    使用方法：
        benchmark = PerformanceBenchmark()
        result = benchmark.run_full_benchmark()
        benchmark.save_report(result, "benchmark_report.json")
    """

    # 测试视频规格
    TEST_SPECS = [
        {"name": "1min_short", "duration": 60, "description": "1 分钟短视频"},
        {"name": "10min_medium", "duration": 600, "description": "10 分钟中等视频"},
        {"name": "60min_long", "duration": 3600, "description": "60 分钟长视频"},
        {"name": "90min_movie", "duration": 5400, "description": "90 分钟电影级视频"},
    ]

    def __init__(self, output_dir: str = "./benchmark_results"):
        """
        初始化性能基准测试

        Args:
            output_dir: 测试结果输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PerformanceBenchmark 初始化完成，输出目录: {self.output_dir}")

    def run_full_benchmark(self) -> BenchmarkResult:
        """
        运行完整基准测试

        Returns:
            BenchmarkResult: 测试结果
        """
        logger.info("开始完整基准测试")

        # 生成测试 ID
        test_id = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 收集系统信息
        system_info = self._collect_system_info()

        # 创建测试结果
        result = BenchmarkResult(
            test_id=test_id,
            test_time=datetime.now().isoformat(),
            system_info=system_info,
        )

        # 运行各项测试
        for spec in self.TEST_SPECS:
            logger.info(f"运行测试: {spec['name']} ({spec['description']})")
            metrics = self._run_single_test(spec)
            result.metrics.append(metrics)

        # 生成摘要
        result.summary = self._generate_summary(result.metrics)

        logger.info("完整基准测试完成")
        return result

    def run_quick_benchmark(self) -> BenchmarkResult:
        """
        运行快速基准测试（仅测试 1 分钟和 10 分钟视频）

        Returns:
            BenchmarkResult: 测试结果
        """
        logger.info("开始快速基准测试")

        test_id = f"quick_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        system_info = self._collect_system_info()

        result = BenchmarkResult(
            test_id=test_id,
            test_time=datetime.now().isoformat(),
            system_info=system_info,
        )

        # 仅运行 1 分钟和 10 分钟测试
        quick_specs = [spec for spec in self.TEST_SPECS if spec["duration"] <= 600]
        for spec in quick_specs:
            logger.info(f"运行测试: {spec['name']}")
            metrics = self._run_single_test(spec)
            result.metrics.append(metrics)

        result.summary = self._generate_summary(result.metrics)

        logger.info("快速基准测试完成")
        return result

    def _collect_system_info(self) -> dict[str, Any]:
        """
        收集系统信息

        Returns:
            dict: 系统信息
        """
        import platform

        import psutil

        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "timestamp": datetime.now().isoformat(),
        }

        # 尝试获取 GPU 信息
        try:
            import torch
            if torch.cuda.is_available():
                system_info["gpu_available"] = True
                system_info["gpu_name"] = torch.cuda.get_device_name(0)
                system_info["gpu_memory_gb"] = round(
                    torch.cuda.get_device_properties(0).total_memory / (1024**3), 2
                )
            else:
                system_info["gpu_available"] = False
        except ImportError:
            system_info["gpu_available"] = False

        return system_info

    def _run_single_test(self, spec: dict[str, Any]) -> PerformanceMetrics:
        """
        运行单个测试

        Args:
            spec: 测试规格

        Returns:
            PerformanceMetrics: 测试指标
        """
        test_name = spec["name"]
        video_duration = spec["duration"]

        logger.info(f"开始测试: {test_name}")

        try:
            # 这里应该调用实际的 SceneFab 处理流程
            # 由于这是基准测试框架，实际的测试逻辑需要根据 SceneFab 的 API 实现

            # 模拟测试（实际实现时替换为真实调用）
            start_time = time.time()

            # TODO: 调用 SceneFab 处理流程
    

            # 模拟处理时间（实际实现时删除）
            import random
            processing_time = video_duration * random.uniform(0.1, 0.5)
            time.sleep(min(processing_time, 5))  # 限制实际等待时间

            end_time = time.time()
            processing_time = end_time - start_time

            # 收集内存使用信息
            memory_info = self._collect_memory_usage()

            # 计算吞吐量
            throughput = video_duration / processing_time if processing_time > 0 else 0

            return PerformanceMetrics(
                test_name=test_name,
                video_duration=video_duration,
                processing_time=processing_time,
                memory_peak=memory_info["peak"],
                memory_average=memory_info["average"],
                cpu_usage=memory_info["cpu_usage"],
                gpu_usage=memory_info.get("gpu_usage", 0),
                throughput=throughput,
                success=True,
                metadata={"spec": spec},
            )

        except Exception as e:
            logger.error(f"测试失败: {test_name}, 错误: {e}")
            return PerformanceMetrics(
                test_name=test_name,
                video_duration=video_duration,
                processing_time=0,
                memory_peak=0,
                memory_average=0,
                cpu_usage=0,
                gpu_usage=0,
                throughput=0,
                success=False,
                error_message=str(e),
            )

    def _collect_memory_usage(self) -> dict[str, float]:
        """
        收集内存使用信息

        Returns:
            dict: 内存使用信息
        """
        import psutil

        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)

        result = {
            "peak": memory.used / (1024**2),  # MB
            "average": memory.used / (1024**2),  # MB
            "cpu_usage": cpu_percent,
        }

        # 尝试获取 GPU 使用率
        try:
            import torch
            if torch.cuda.is_available():
                result["gpu_usage"] = torch.cuda.utilization()
        except (ImportError, Exception):
            pass

        return result

    def _generate_summary(self, metrics: list[PerformanceMetrics]) -> dict[str, Any]:
        """
        生成测试摘要

        Args:
            metrics: 测试指标列表

        Returns:
            dict: 测试摘要
        """
        successful_tests = [m for m in metrics if m.success]
        failed_tests = [m for m in metrics if not m.success]

        if not successful_tests:
            return {
                "total_tests": len(metrics),
                "successful_tests": 0,
                "failed_tests": len(failed_tests),
                "success_rate": 0,
            }

        # 计算平均指标
        avg_processing_time = sum(m.processing_time for m in successful_tests) / len(successful_tests)
        avg_throughput = sum(m.throughput for m in successful_tests) / len(successful_tests)
        avg_memory = sum(m.memory_peak for m in successful_tests) / len(successful_tests)

        return {
            "total_tests": len(metrics),
            "successful_tests": len(successful_tests),
            "failed_tests": len(failed_tests),
            "success_rate": len(successful_tests) / len(metrics),
            "average_processing_time": round(avg_processing_time, 2),
            "average_throughput": round(avg_throughput, 2),
            "average_memory_peak_mb": round(avg_memory, 2),
            "fastest_test": min(successful_tests, key=lambda m: m.processing_time).test_name,
            "slowest_test": max(successful_tests, key=lambda m: m.processing_time).test_name,
            "highest_throughput": max(successful_tests, key=lambda m: m.throughput).test_name,
        }

    def save_report(self, result: BenchmarkResult, filename: str | None = None) -> str:
        """
        保存测试报告

        Args:
            result: 测试结果
            filename: 文件名（可选）

        Returns:
            str: 报告文件路径
        """
        if filename is None:
            filename = f"{result.test_id}.json"

        filepath = self.output_dir / filename

        # 转换为可序列化的字典
        report = {
            "test_id": result.test_id,
            "test_time": result.test_time,
            "system_info": result.system_info,
            "metrics": [
                {
                    "test_name": m.test_name,
                    "video_duration": m.video_duration,
                    "processing_time": m.processing_time,
                    "memory_peak": m.memory_peak,
                    "memory_average": m.memory_average,
                    "cpu_usage": m.cpu_usage,
                    "gpu_usage": m.gpu_usage,
                    "throughput": m.throughput,
                    "success": m.success,
                    "error_message": m.error_message,
                    "metadata": m.metadata,
                }
                for m in result.metrics
            ],
            "summary": result.summary,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"测试报告已保存: {filepath}")
        return str(filepath)

    def load_report(self, filepath: str) -> BenchmarkResult:
        """
        加载测试报告

        Args:
            filepath: 报告文件路径

        Returns:
            BenchmarkResult: 测试结果
        """
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        # 重建 BenchmarkResult 对象
        result = BenchmarkResult(
            test_id=data["test_id"],
            test_time=data["test_time"],
            system_info=data["system_info"],
            summary=data["summary"],
        )

        for m_data in data["metrics"]:
            metrics = PerformanceMetrics(
                test_name=m_data["test_name"],
                video_duration=m_data["video_duration"],
                processing_time=m_data["processing_time"],
                memory_peak=m_data["memory_peak"],
                memory_average=m_data["memory_average"],
                cpu_usage=m_data["cpu_usage"],
                gpu_usage=m_data["gpu_usage"],
                throughput=m_data["throughput"],
                success=m_data["success"],
                error_message=m_data.get("error_message", ""),
                metadata=m_data.get("metadata", {}),
            )
            result.metrics.append(metrics)

        return result


def run_benchmark(output_dir: str = "./benchmark_results", quick: bool = False) -> BenchmarkResult:
    """
    便捷函数：运行基准测试

    Args:
        output_dir: 输出目录
        quick: 是否运行快速测试

    Returns:
        BenchmarkResult: 测试结果
    """
    benchmark = PerformanceBenchmark(output_dir=output_dir)

    if quick:
        result = benchmark.run_quick_benchmark()
    else:
        result = benchmark.run_full_benchmark()

    # 保存报告
    benchmark.save_report(result)

    return result
