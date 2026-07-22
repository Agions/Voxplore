"""SceneFab 核心模块导出层（纯基础设施）。

所有导出通过 lazy import 实现，避免循环依赖。
直接导入子模块更推荐：from scenefab.core.base_worker import BaseWorker

注意：core 层禁止导入 services / pipeline / ui / application。
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "BaseWorker": ("scenefab.core.base_worker", "BaseWorker"),
    "WorkerResult": ("scenefab.core.base_worker", "WorkerResult"),
    "AuditLogger": ("scenefab.core.audit", "AuditLogger"),
    "AuditEntry": ("scenefab.core.audit", "AuditEntry"),
    "SafeFFmpegCommand": ("scenefab.core.ffmpeg_safe", "SafeFFmpegCommand"),
    "FFmpegResult": ("scenefab.core.ffmpeg_safe", "FFmpegResult"),
    "FFmpegSecurityError": ("scenefab.core.ffmpeg_safe", "FFmpegSecurityError"),
    "is_safe_path": ("scenefab.core.ffmpeg_safe", "is_safe_path"),
    "StreamingLLMWorker": ("scenefab.core.stream_worker", "StreamingLLMWorker"),
    "UnifiedEventBus": ("scenefab.core.unified_event_bus", "UnifiedEventBus"),
    "EventHandler": ("scenefab.core.unified_event_bus", "EventHandler"),
    "AsyncEventHandler": ("scenefab.core.unified_event_bus", "AsyncEventHandler"),
    "get_event_bus": ("scenefab.core.unified_event_bus", "get_event_bus"),
    "set_event_bus": ("scenefab.core.unified_event_bus", "set_event_bus"),
    "DomainEvent": ("scenefab.core.event_types", "DomainEvent"),
    "PipelineStarted": ("scenefab.core.event_types", "PipelineStarted"),
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
}


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


__all__ = [*_EXPORTS.keys()]
