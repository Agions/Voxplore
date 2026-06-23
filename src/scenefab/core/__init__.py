"""SceneFab 核心模块导出层。

所有导出通过 lazy import 实现，避免循环依赖。
直接导入子模块更推荐：from scenefab.core.pipeline_engine import PipelineEngine
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

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
    "BatchTaskStatus": ("scenefab.core.batch_processor", "BatchTaskStatus"),
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
    *_EXPORTS.keys(),
]
