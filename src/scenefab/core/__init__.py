"""
SceneFab 核心模块 v2.0

基础组件：
- application: 应用程序生命周期
- base_worker: 统一 Worker 基类 (v2.0)
- audit: 操作审计日志 (v2.0)
- pipeline_engine: DAG 并行流水线引擎 (v2.0)
- ffmpeg_safe: FFmpeg 安全封装 (v2.0)
- batch_processor: 批量任务处理器 (v2.0)
- short_drama: 短剧解说特化 (v2.0)
- platform_adapter: 多平台智能适配 (v2.0)
- streaming_llm_worker: LLM 流式输出 Worker (v2.0)
"""

import logging
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# ============================================
# v1.x 公开 API（保留以确保向后兼容）
# ============================================

# ApplicationState 已统一到 scenefab.application（Phase 5 重构）
# 旧定义保留导入以保持向后兼容
from scenefab.application import ApplicationState


@dataclass
class ErrorInfo:
    """错误信息"""

    error_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    details: str | None = None
    exception: Exception | None = None
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class EventBus:
    """
    事件总线
    提供松耦合的组件通信
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_name: str, handler: Callable) -> None:
        """订阅事件"""
        with self._lock:
            if event_name not in self._handlers:
                self._handlers[event_name] = []
            if handler not in self._handlers[event_name]:
                self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Callable) -> None:
        """取消订阅"""
        with self._lock:
            if event_name in self._handlers:
                if handler in self._handlers[event_name]:
                    self._handlers[event_name].remove(handler)

    def publish(self, event_name: str, data: Any = None) -> None:
        """发布事件（优化版 - 并行调用处理器）"""
        handlers = []
        with self._lock:
            handlers = self._handlers.get(event_name, []).copy()

        if not handlers:
            return

        # 并行调用所有处理器
        if len(handlers) > 1:
            with ThreadPoolExecutor(max_workers=min(len(handlers), 4)) as executor:
                futures = [executor.submit(self._safe_call, h, data) for h in handlers]
                for f in futures:
                    f.result()  # 等待完成以捕获异常
        else:
            self._safe_call(handlers[0], data)

    def _safe_call(self, handler: Callable, data: Any):
        """安全调用处理器"""
        try:
            handler(data)
        except Exception as e:
            logger.error(f"Event handler failed: {e}")

    def clear(self, event_name: str | None = None) -> None:
        """清除事件处理器"""
        with self._lock:
            if event_name:
                self._handlers.pop(event_name, None)
            else:
                self._handlers.clear()


class EventEmitter:
    """
    事件发射器基类
    支持 PySide6 信号（如果可用）或其他事件系统
    """

    def __init__(self):
        self._events = EventBus()

    def on(self, event: str, handler: Callable) -> "EventEmitter":
        """订阅事件（链式调用）"""
        self._events.subscribe(event, handler)
        return self

    def off(self, event: str, handler: Callable) -> "EventEmitter":
        """取消订阅（链式调用）"""
        self._events.unsubscribe(event, handler)
        return self

    def emit(self, event: str, data: Any = None) -> None:
        """发射事件"""
        self._events.publish(event, data)


# 全局事件总线实例
event_bus = EventBus()


# ============================================
# v2.0 新增模块（保持平铺 re-export）
# ============================================

from scenefab.core.audit import AuditEntry, AuditLogger
from scenefab.core.base_worker import BaseWorker, WorkerResult
from scenefab.core.batch_processor import (
    BatchCheckpoint,
    BatchConfig,
    BatchProcessor,
    BatchTask,
)
from scenefab.core.batch_processor import (
    TaskStatus as BatchTaskStatus,
)
from scenefab.core.ffmpeg_safe import (
    FFmpegResult,
    FFmpegSecurityError,
    SafeFFmpegCommand,
    is_safe_path,
)
from scenefab.core.pipeline_engine import (
    PipelineConfig,
    PipelineEngine,
    PipelineStep,
    StepResult,
    StepStatus,
)
from scenefab.core.platform_adapter import (
    PLATFORM_CONFIGS,
    CoverGenerator,
    CoverStyle,
    CropRegion,
    MultiPlatformExporter,
    Platform,
    PlatformConfig,
    SmartCropper,
)
from scenefab.core.short_drama import (
    EpisodeInfo,
    SeriesContext,
    ShortDramaNarrator,
    ShortDramaPreset,
    ShortDramaStyle,
    TropeType,
)
from scenefab.core.streaming_llm_worker import StreamingLLMWorker

__all__ = [
    # v1.x 公开 API
    "ApplicationState",
    "ErrorInfo",
    "EventBus",
    "EventEmitter",
    "event_bus",
    # v2.0 新增
    "BaseWorker",
    "WorkerResult",
    "AuditLogger",
    "AuditEntry",
    "PipelineEngine",
    "PipelineStep",
    "PipelineConfig",
    "StepStatus",
    "StepResult",
    "SafeFFmpegCommand",
    "FFmpegResult",
    "FFmpegSecurityError",
    "is_safe_path",
    "BatchProcessor",
    "BatchConfig",
    "BatchTask",
    "BatchCheckpoint",
    "BatchTaskStatus",
    "ShortDramaStyle",
    "ShortDramaPreset",
    "ShortDramaNarrator",
    "TropeType",
    "EpisodeInfo",
    "SeriesContext",
    "Platform",
    "PlatformConfig",
    "PLATFORM_CONFIGS",
    "CropRegion",
    "SmartCropper",
    "CoverStyle",
    "CoverGenerator",
    "MultiPlatformExporter",
    "StreamingLLMWorker",
]
