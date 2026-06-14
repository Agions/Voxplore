"""SceneFab 核心模块兼容导出层。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from importlib import import_module
from typing import Any


@dataclass
class ErrorInfo:
    """错误信息。"""

    error_type: str
    severity: str
    message: str
    details: str | None = None
    exception: Exception | None = None
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class EventBus:
    """v1.x 事件总线兼容类。"""

    @property
    def _backend(self):
        from scenefab.core.unified_event_bus import UnifiedEventBus

        return UnifiedEventBus.get_default()

    def subscribe(self, event_name: str, handler: Callable) -> None:
        self._backend.subscribe(event_name, handler)

    def unsubscribe(self, event_name: str, handler: Callable) -> None:
        self._backend.unsubscribe(event_name, handler)

    def publish(self, event_name: str, data: Any = None) -> None:
        self._backend.publish(event_name, data)

    def clear(self, event_name: str | None = None) -> None:
        self._backend.clear_handlers(event_name)

    def publish_event(self, event: Any) -> None:
        self._backend.publish_event(event)

    def replay_all(self) -> int:
        return self._backend.replay_all()

    def stats(self) -> dict[str, Any]:
        return self._backend.stats()


class EventEmitter:
    """事件发射器基类。"""

    def __init__(self):
        self._events = EventBus()

    def on(self, event: str, handler: Callable) -> EventEmitter:
        self._events.subscribe(event, handler)
        return self

    def off(self, event: str, handler: Callable) -> EventEmitter:
        self._events.unsubscribe(event, handler)
        return self

    def emit(self, event: str, data: Any = None) -> None:
        self._events.publish(event, data)


event_bus = EventBus()

_EXPORTS = {
    "ApplicationState": ("scenefab.application", "ApplicationState"),
    "BaseWorker": ("scenefab.core.base_worker", "BaseWorker"),
    "WorkerResult": ("scenefab.core.base_worker", "WorkerResult"),
    "AuditLogger": ("scenefab.core.audit", "AuditLogger"),
    "AuditEntry": ("scenefab.core.audit", "AuditEntry"),
    "PipelineEngine": ("scenefab.core.pipeline_engine", "PipelineEngine"),
    "PipelineStep": ("scenefab.core.pipeline_engine", "PipelineStep"),
    "PipelineConfig": ("scenefab.core.pipeline_engine", "PipelineConfig"),
    "StepStatus": ("scenefab.core.pipeline_engine", "StepStatus"),
    "StepResult": ("scenefab.core.pipeline_engine", "StepResult"),
    "SafeFFmpegCommand": ("scenefab.core.ffmpeg_safe", "SafeFFmpegCommand"),
    "FFmpegResult": ("scenefab.core.ffmpeg_safe", "FFmpegResult"),
    "FFmpegSecurityError": ("scenefab.core.ffmpeg_safe", "FFmpegSecurityError"),
    "is_safe_path": ("scenefab.core.ffmpeg_safe", "is_safe_path"),
    "BatchProcessor": ("scenefab.core.batch_processor", "BatchProcessor"),
    "BatchConfig": ("scenefab.core.batch_processor", "BatchConfig"),
    "BatchTask": ("scenefab.core.batch_processor", "BatchTask"),
    "BatchCheckpoint": ("scenefab.core.batch_processor", "BatchCheckpoint"),
    "BatchTaskStatus": ("scenefab.core.batch_processor", "TaskStatus"),
    "ShortDramaStyle": ("scenefab.core.short_drama", "ShortDramaStyle"),
    "ShortDramaPreset": ("scenefab.core.short_drama", "ShortDramaPreset"),
    "ShortDramaNarrator": ("scenefab.core.short_drama", "ShortDramaNarrator"),
    "TropeType": ("scenefab.core.short_drama", "TropeType"),
    "EpisodeInfo": ("scenefab.core.short_drama", "EpisodeInfo"),
    "SeriesContext": ("scenefab.core.short_drama", "SeriesContext"),
    "Platform": ("scenefab.core.platform_adapter", "Platform"),
    "PlatformConfig": ("scenefab.core.platform_adapter", "PlatformConfig"),
    "PLATFORM_CONFIGS": ("scenefab.core.platform_adapter", "PLATFORM_CONFIGS"),
    "CropRegion": ("scenefab.core.platform_adapter", "CropRegion"),
    "SmartCropper": ("scenefab.core.platform_adapter", "SmartCropper"),
    "CoverStyle": ("scenefab.core.platform_adapter", "CoverStyle"),
    "CoverGenerator": ("scenefab.core.platform_adapter", "CoverGenerator"),
    "MultiPlatformExporter": ("scenefab.core.platform_adapter", "MultiPlatformExporter"),
    "StreamingLLMWorker": ("scenefab.core.streaming_llm_worker", "StreamingLLMWorker"),
    "UnifiedEventBus": ("scenefab.core.unified_event_bus", "UnifiedEventBus"),
    "EventLog": ("scenefab.core.unified_event_bus", "EventLog"),
    "EventRecord": ("scenefab.core.unified_event_bus", "EventRecord"),
    "EventStats": ("scenefab.core.unified_event_bus", "EventStats"),
    "EventHandler": ("scenefab.core.unified_event_bus", "EventHandler"),
    "AsyncEventHandler": ("scenefab.core.unified_event_bus", "AsyncEventHandler"),
    "get_event_bus": ("scenefab.core.unified_event_bus", "get_event_bus"),
    "set_event_bus": ("scenefab.core.unified_event_bus", "set_event_bus"),
    "DomainEvent": ("scenefab.core.event_types", "DomainEvent"),
    "PipelineStarted": ("scenefab.core.event_types", "PipelineStarted"),
    "PipelineStepStarted": ("scenefab.core.event_types", "PipelineStepStarted"),
    "PipelineStepCompleted": ("scenefab.core.event_types", "PipelineStepCompleted"),
    "PipelineCompleted": ("scenefab.core.event_types", "PipelineCompleted"),
    "TaskCreated": ("scenefab.core.event_types", "TaskCreated"),
    "TaskProgressUpdated": ("scenefab.core.event_types", "TaskProgressUpdated"),
    "TaskStatusChanged": ("scenefab.core.event_types", "TaskStatusChanged"),
    "LLMTokenGenerated": ("scenefab.core.event_types", "LLMTokenGenerated"),
    "FFmpegExecuted": ("scenefab.core.event_types", "FFmpegExecuted"),
    "UnifiedTask": ("scenefab.core.task_model", "UnifiedTask"),
    "TaskStep": ("scenefab.core.task_model", "TaskStep"),
    "TaskStatus": ("scenefab.core.task_model", "TaskStatus"),
    "TaskSource": ("scenefab.core.task_model", "TaskSource"),
    "CancelToken": ("scenefab.core.task_model", "CancelToken"),
    "IllegalTransitionError": ("scenefab.core.task_model", "IllegalTransitionError"),
    "can_transition": ("scenefab.core.task_model", "can_transition"),
    "DIContainer": ("scenefab.core.di_container", "DIContainer"),
    "get_app_container": ("scenefab.core.di_container", "get_app_container"),
    "set_app_container": ("scenefab.core.di_container", "set_app_container"),
    "TaskStore": ("scenefab.core.task_store", "TaskStore"),
    "InMemoryTaskStore": ("scenefab.core.task_store", "InMemoryTaskStore"),
    "SQLiteTaskStore": ("scenefab.core.task_store", "SQLiteTaskStore"),
    "create_task_store": ("scenefab.core.task_store", "create_task_store"),
    "get_task_store": ("scenefab.core.task_store", "get_task_store"),
    "set_task_store": ("scenefab.core.task_store", "set_task_store"),
    "EventStore": ("scenefab.core.event_store", "EventStore"),
    "InMemoryEventStore": ("scenefab.core.event_store", "InMemoryEventStore"),
    "SQLiteEventStore": ("scenefab.core.event_store", "SQLiteEventStore"),
    "create_event_store": ("scenefab.core.event_store", "create_event_store"),
    "get_event_store": ("scenefab.core.event_store", "get_event_store"),
    "set_event_store": ("scenefab.core.event_store", "set_event_store"),
    "install_event_store_into_bus": (
        "scenefab.core.event_store",
        "install_event_store_into_bus",
    ),
    "SettingsV2": ("scenefab.core.config_v2", "SettingsV2"),
    "LLMSettings": ("scenefab.core.config_v2", "LLMSettings"),
    "LLMProviderConfig": ("scenefab.core.config_v2", "LLMProviderConfig"),
    "LLMProviderName": ("scenefab.core.config_v2", "LLMProviderName"),
    "TTSSettings": ("scenefab.core.config_v2", "TTSSettings"),
    "TTSProviderConfig": ("scenefab.core.config_v2", "TTSProviderConfig"),
    "TTSProviderName": ("scenefab.core.config_v2", "TTSProviderName"),
    "PipelineSettings": ("scenefab.core.config_v2", "PipelineSettings"),
    "StorageSettings": ("scenefab.core.config_v2", "StorageSettings"),
    "SecuritySettings": ("scenefab.core.config_v2", "SecuritySettings"),
    "APISettings": ("scenefab.core.config_v2", "APISettings"),
    "AppProfile": ("scenefab.core.config_v2", "AppProfile"),
    "TaskStoreBackend": ("scenefab.core.config_v2", "TaskStoreBackend"),
    "get_settings": ("scenefab.core.config_v2", "get_settings"),
    "set_settings": ("scenefab.core.config_v2", "set_settings"),
    "is_settings_v2_available": ("scenefab.core.config_v2", "is_settings_v2_available"),
    "WSHub": ("scenefab.core.ws_hub", "WSHub"),
    "WSConnection": ("scenefab.core.ws_hub", "WSConnection"),
    "get_ws_hub": ("scenefab.core.ws_hub", "get_ws_hub"),
    "set_ws_hub": ("scenefab.core.ws_hub", "set_ws_hub"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


__all__ = [
    "ApplicationState",
    "ErrorInfo",
    "EventBus",
    "EventEmitter",
    "event_bus",
    *_EXPORTS.keys(),
]
