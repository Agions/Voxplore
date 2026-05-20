#!/usr/bin/env python3
"""
性能优化工具模块
提供：
1. GPU 检测和优先级排序
2. CPU 核心数检测
3. 内存监控
4. 动态线程池
5. 批量处理优化
"""
import os
import logging
from typing import Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """设备类型"""
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"  # Apple Silicon


@dataclass(slots=True)
class DeviceInfo:
    """设备信息"""
    device_type: DeviceType
    device_id: int
    name: str
    memory_total: float  # GB
    memory_available: float  # GB
    compute_capability: str | None = None
    is_available: bool = True


class PerformanceOptimizer:
    """
    性能优化工具
    自动检测最佳计算设备和工作线程数
    """
    
    @staticmethod
    def get_optimal_workers() -> int:
        """
        获取最佳工作线程数
        
        Returns:
            推荐的工作线程数
        """
        cpu_count = os.cpu_count() or 4
        
        # I/O 密集型任务：可以用更多线程
        # CPU 密集型任务：不超过 CPU 核心数
        # 根据经验，I/O 等待时可加倍
        return min(8, cpu_count * 2)
    
    @staticmethod
    def get_gpu_info() -> list[DeviceInfo]:
        """
        获取 GPU 信息
        
        Returns:
            GPU 设备列表
        """
        devices = []
        
        # 检测 CUDA
        try:
            import torch
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    total_mem = props.total_memory / (1024**3)
                    
                    devices.append(DeviceInfo(
                        device_type=DeviceType.CUDA,
                        device_id=i,
                        name=props.name,
                        memory_total=total_mem,
                        memory_available=total_mem,  # 暂不支持精确查询
                        compute_capability=f"{props.major}.{props.minor}",
                    ))
                    
            # 检测 MPS (Apple Silicon)
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                devices.append(DeviceInfo(
                    device_type=DeviceType.MPS,
                    device_id=0,
                    name="Apple Silicon",
                    memory_total=0,  # MPS 不提供此信息
                    memory_available=0,
                ))
                
        except ImportError:
            logger.warning("PyTorch not available for GPU detection")
        except Exception as e:
            logger.warning(f"GPU detection failed: {e}")
        
        # 按计算能力排序（优先使用计算能力高的）
        devices.sort(
            key=lambda d: d.compute_capability or "0.0",
            reverse=True
        )
        
        return devices
    
    @staticmethod
    def get_best_device() -> DeviceInfo:
        """
        获取最佳计算设备
        
        Returns:
            最佳设备信息
        """
        gpus = PerformanceOptimizer.get_gpu_info()
        
        if gpus:
            # 返回第一个（已按计算能力排序）
            return gpus[0]
        
        # 回退到 CPU
        return DeviceInfo(
            device_type=DeviceType.CPU,
            device_id=0,
            name=f"CPU (x{os.cpu_count()})",
            memory_total=0,
            memory_available=0,
        )
    
    @staticmethod
    def check_dependencies() -> dict[str, bool]:
        """
        检查性能相关依赖
        
        Returns:
            依赖可用性字典
        """
        deps = {
            "torch": False,
            "torch.cuda": False,
            "torch.mps": False,
            "cv2": False,
            "librosa": False,
            "numpy": False,
        }
        
        try:
            import torch
            deps["torch"] = True
            deps["torch.cuda"] = torch.cuda.is_available()
            deps["torch.mps"] = hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
        except ImportError:
            pass
        
        try:
            import cv2 as _cv2  # noqa: F401
            deps["cv2"] = True
        except ImportError:
            pass
        
        try:
            import librosa as _librosa  # noqa: F401
            deps["librosa"] = True
        except ImportError:
            pass
        
        try:
            import numpy as _numpy  # noqa: F401
            deps["numpy"] = True
        except ImportError:
            pass
        
        return deps
    
    @staticmethod
    def get_memory_info() -> dict[str, float]:
        """
        获取系统内存信息
        
        Returns:
            内存信息（GB）
        """
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "total": mem.total / (1024**3),
                "available": mem.available / (1024**3),
                "used": mem.used / (1024**3),
                "percent": mem.percent,
            }
        except ImportError:
            return {"total": 0, "available": 0, "used": 0, "percent": 0}


class BatchProcessor:
    """
    批量处理器
    优化批量任务的处理策略
    """
    
    def __init__(
        self,
        batch_size: int = 10,
        max_workers: int = None,
        progress_callback=None,
    ):
        """
        Args:
            batch_size: 批大小
            max_workers: 最大工作线程数（默认自动检测）
            progress_callback: 进度回调
        """
        self.batch_size = batch_size
        self.max_workers = max_workers or PerformanceOptimizer.get_optimal_workers()
        self.progress_callback = progress_callback
    
    def process_batch(
        self,
        items: list[Any],
        process_func,
        **kwargs
    ) -> list[Any]:
        """
        批量处理
        
        Args:
            items: 待处理项列表
            process_func: 处理函数
            **kwargs: 传递给 process_func 的额外参数
            
        Returns:
            处理结果列表
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = []
        total = len(items)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(process_func, item, **kwargs): item
                for item in items
            }
            
            completed = 0
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Batch item failed: {e}")
                    results.append(None)
                
                completed += 1
                if self.progress_callback:
                    self.progress_callback(completed, total)
        
        return results


# 便捷函数
def get_optimal_threads() -> int:
    """获取最佳线程数"""
    return PerformanceOptimizer.get_optimal_workers()


def get_compute_device() -> DeviceInfo:
    """获取最佳计算设备"""
    return PerformanceOptimizer.get_best_device()


def is_gpu_available() -> bool:
    """检查 GPU 是否可用"""
    return PerformanceOptimizer.get_best_device().device_type != DeviceType.CPU


def get_system_info() -> dict[str, Any]:
    """获取系统性能信息"""
    return {
        "optimal_workers": PerformanceOptimizer.get_optimal_workers(),
        "gpu": PerformanceOptimizer.get_best_device().__dict__,
        "memory": PerformanceOptimizer.get_memory_info(),
        "dependencies": PerformanceOptimizer.check_dependencies(),
    }


__all__ = [
    "PerformanceOptimizer",
    "BatchProcessor",
    "DeviceType",
    "DeviceInfo",
    "get_optimal_threads",
    "get_compute_device",
    "is_gpu_available",
    "get_system_info",
]
