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


# EventBus v1.x 兼容类（v2.1 委托到 UnifiedEventBus）
# 单源真相：scenefab.core.unified_event_bus.UnifiedEventBus
from scenefab.core.unified_event_bus import (
    UnifiedEventBus as _UnifiedEventBus,
)


# v1.x 兼容类 - 薄包装，委托到 UnifiedEventBus 单例
class EventBus:
    """
    事件总线（v1.x 兼容 - v2.1 委托实现）

    ⚠️ v2.1 内部实现统一到 scenefab.core.unified_event_bus.UnifiedEventBus。
    所有 v1.x 公开 API 完全保持兼容，但所有 EventBus 实例共享同一份事件状态。
    新能力（type-safe events / replay / stats）通过 publish_event() 暴露。
    """

    def __init__(self):
        self._backend: _UnifiedEventBus = _UnifiedEventBus.get_default()

    def subscribe(self, event_name: str, handler: Callable) -> None:
        self._backend.subscribe(event_name, handler)

    def unsubscribe(self, event_name: str, handler: Callable) -> None:
        self._backend.unsubscribe(event_name, handler)

    def publish(self, event_name: str, data: Any = None) -> None:
        self._backend.publish(event_name, data)

    def clear(self, event_name: str | None = None) -> None:
        self._backend.clear_handlers(event_name)

    # v2.1 新增
    def publish_event(self, event: Any) -> None:
        self._backend.publish_event(event)

    def replay_all(self) -> int:
        return self._backend.replay_all()

    def stats(self) -> dict[str, Any]:
        return self._backend.stats()


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

# ============================================
# v2.1 架构升级
# ============================================

from scenefab.core.event_types import (
    DomainEvent,
    FFmpegExecuted,
    LLMTokenGenerated,
    PipelineCompleted,
    PipelineStarted,
    PipelineStepCompleted,
    PipelineStepStarted,
    TaskCreated,
    TaskProgressUpdated,
    TaskStatusChanged,
)
from scenefab.core.unified_event_bus import (
    AsyncEventHandler,
    EventHandler,
    EventLog,
    EventRecord,
    EventStats,
    UnifiedEventBus,
    get_event_bus,
    set_event_bus,
)
from scenefab.core.task_model import (
    CancelToken,
    IllegalTransitionError,
    TaskSource,
    TaskStatus,
    TaskStep,
    UnifiedTask,
    can_transition,
)
from scenefab.core.di_container import DIContainer, get_app_container, set_app_container
from scenefab.core.task_store import (
    InMemoryTaskStore,
    SQLiteTaskStore,
    TaskStore,
    create_task_store,
    get_task_store,
    set_task_store,
)
from scenefab.core.event_store import (
    EventStore,
    InMemoryEventStore,
    SQLiteEventStore,
    create_event_store,
    get_event_store,
    install_event_store_into_bus,
    set_event_store,
)
from scenefab.core.config_v2 import (
    APISettings,
    AppProfile,
    LLMProviderConfig,
    LLMProviderName,
    LLMSettings,
    PipelineSettings,
    SecuritySettings,
    SettingsV2,
    StorageSettings,
    TaskStoreBackend,
    TTSProviderConfig,
    TTSProviderName,
    TTSSettings,
    get_settings,
    is_settings_v2_available,
    set_settings,
)
from scenefab.core.ws_hub import WSHub, WSConnection, get_ws_hub, set_ws_hub

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
    # v2.1 新增 - 事件总线单源真相
    "UnifiedEventBus",
    "EventLog",
    "EventRecord",
    "EventStats",
    "EventHandler",
    "AsyncEventHandler",
    "get_event_bus",
    "set_event_bus",
    # v2.1 新增 - 类型化领域事件
    "DomainEvent",
    "PipelineStarted",
    "PipelineStepStarted",
    "PipelineStepCompleted",
    "PipelineCompleted",
    "TaskCreated",
    "TaskProgressUpdated",
    "TaskStatusChanged",
    "LLMTokenGenerated",
    "FFmpegExecuted",
    # v2.1 新增 - 任务系统统一
    "UnifiedTask",
    "TaskStep",
    "TaskStatus",
    "TaskSource",
    "CancelToken",
    "IllegalTransitionError",
    "can_transition",
    # v2.1 新增 - DI 容器
    "DIContainer",
    "get_app_container",
    "set_app_container",
    # v2.1 新增 - TaskStore 3 后端
    "TaskStore",
    "InMemoryTaskStore",
    "SQLiteTaskStore",
    "create_task_store",
    "get_task_store",
    "set_task_store",
    # v2.1 新增 - EventStore 持久化
    "EventStore",
    "InMemoryEventStore",
    "SQLiteEventStore",
    "create_event_store",
    "get_event_store",
    "set_event_store",
    "install_event_store_into_bus",
    # v2.1 新增 - 配置层
    "SettingsV2",
    "LLMSettings",
    "LLMProviderConfig",
    "LLMProviderName",
    "TTSSettings",
    "TTSProviderConfig",
    "TTSProviderName",
    "PipelineSettings",
    "StorageSettings",
    "SecuritySettings",
    "APISettings",
    "AppProfile",
    "TaskStoreBackend",
    "get_settings",
    "set_settings",
    "is_settings_v2_available",
    # v2.1 新增 - WebSocket Hub
    "WSHub",
    "WSConnection",
    "get_ws_hub",
    "set_ws_hub",
]
