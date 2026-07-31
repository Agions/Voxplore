"""SceneFab 核心模块导出层（纯基础设施）。

所有导出通过 lazy import 实现，避免循环依赖。
直接导入子模块更推荐：from app.core.base_worker import BaseWorker

注意：core 层禁止导入 services / pipeline / ui / application。
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "BaseWorker": ("app.core.base_worker", "BaseWorker"),
    "WorkerResult": ("app.core.base_worker", "WorkerResult"),
    "AuditLogger": ("app.core.audit", "AuditLogger"),
    "AuditEntry": ("app.core.audit", "AuditEntry"),
    "SafeFFmpegCommand": ("app.core.ffmpeg_safe", "SafeFFmpegCommand"),
    "FFmpegResult": ("app.core.ffmpeg_safe", "FFmpegResult"),
    "FFmpegSecurityError": ("app.core.ffmpeg_safe", "FFmpegSecurityError"),
    "is_safe_path": ("app.core.ffmpeg_safe", "is_safe_path"),
    "StreamingLLMWorker": ("app.core.stream_worker", "StreamingLLMWorker"),
    "UnifiedEventBus": ("app.core.unified_event_bus", "UnifiedEventBus"),
    "EventHandler": ("app.core.unified_event_bus", "EventHandler"),
    "AsyncEventHandler": ("app.core.unified_event_bus", "AsyncEventHandler"),
    "get_event_bus": ("app.core.unified_event_bus", "get_event_bus"),
    "set_event_bus": ("app.core.unified_event_bus", "set_event_bus"),
    "DomainEvent": ("app.core.event_types", "DomainEvent"),
    "PipelineStarted": ("app.core.event_types", "PipelineStarted"),
    "PipelineStepCompleted": ("app.core.event_types", "PipelineStepCompleted"),
    "PipelineCompleted": ("app.core.event_types", "PipelineCompleted"),
    "TaskCreated": ("app.core.event_types", "TaskCreated"),
    "TaskProgressUpdated": ("app.core.event_types", "TaskProgressUpdated"),
    "TaskStatusChanged": ("app.core.event_types", "TaskStatusChanged"),
    "LLMTokenGenerated": ("app.core.event_types", "LLMTokenGenerated"),
    "FFmpegExecuted": ("app.core.event_types", "FFmpegExecuted"),
    "UnifiedTask": ("app.core.task_model", "UnifiedTask"),
    "TaskStep": ("app.core.task_model", "TaskStep"),
    "TaskStatus": ("app.core.task_model", "TaskStatus"),
    "TaskSource": ("app.core.task_model", "TaskSource"),
    "CancelToken": ("app.core.task_model", "CancelToken"),
    "IllegalTransitionError": ("app.core.task_model", "IllegalTransitionError"),
    "can_transition": ("app.core.task_model", "can_transition"),
    "DIContainer": ("app.core.di_container", "DIContainer"),
    "get_app_container": ("app.core.di_container", "get_app_container"),
    "set_app_container": ("app.core.di_container", "set_app_container"),
    "TaskStore": ("app.core.task_store", "TaskStore"),
    "InMemoryTaskStore": ("app.core.task_store", "InMemoryTaskStore"),
    "SQLiteTaskStore": ("app.core.task_store", "SQLiteTaskStore"),
    "create_task_store": ("app.core.task_store", "create_task_store"),
    "get_task_store": ("app.core.task_store", "get_task_store"),
    "set_task_store": ("app.core.task_store", "set_task_store"),
    "SecurityKey": ("app.core.security_keys", "SecurityKey"),
    "get_security_key": ("app.core.security_keys", "get_security_key"),
    "Signal": ("app.core.signals", "Signal"),
    "CoreException": ("app.core.exceptions", "CoreException"),
    "ConfigurationError": ("app.core.exceptions", "ConfigurationError"),
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
