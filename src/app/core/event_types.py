from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar


@dataclass
class DomainEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    correlation_id: str | None = None
    causation_id: str | None = None

    event_name: ClassVar[str] = "domain.event"


@dataclass
class PipelineStarted(DomainEvent):
    event_name: ClassVar[str] = "pipeline.started"
    pipeline_id: str = ""
    total_steps: int = 0
    inputs: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineStepCompleted(DomainEvent):
    event_name: ClassVar[str] = "pipeline.step.completed"
    pipeline_id: str = ""
    step_id: str = ""
    status: str = "success"
    duration_ms: int = 0
    result: Any = None
    error: str | None = None


@dataclass
class PipelineCompleted(DomainEvent):
    event_name: ClassVar[str] = "pipeline.completed"
    pipeline_id: str = ""
    total_duration_ms: int = 0
    success_count: int = 0
    failure_count: int = 0


@dataclass
class TaskCreated(DomainEvent):
    event_name: ClassVar[str] = "task.created"
    task_id: str = ""
    task_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskProgressUpdated(DomainEvent):
    event_name: ClassVar[str] = "task.progress.updated"
    task_id: str = ""
    progress: float = 0.0
    current_step: str = ""
    step_index: int = 0


@dataclass
class TaskStatusChanged(DomainEvent):
    event_name: ClassVar[str] = "task.status.changed"
    task_id: str = ""
    old_status: str = ""
    new_status: str = ""
    error: str | None = None
    result_path: str | None = None


@dataclass
class LLMTokenGenerated(DomainEvent):
    event_name: ClassVar[str] = "llm.token.generated"
    request_id: str = ""
    model: str = ""
    token: str = ""
    cumulative_tokens: int = 0


@dataclass
class FFmpegExecuted(DomainEvent):
    event_name: ClassVar[str] = "ffmpeg.executed"
    command_hash: str = ""
    return_code: int = 0
    duration_ms: int = 0
    error: str | None = None


@dataclass
class SystemMetricSampled(DomainEvent):
    """Published once per second by ``SystemMonitor`` (Phase 2 · Dashboard).

    Consumers — usually :py:class:`app.ui.viewmodels.dashboard_viewmodel.DashboardViewModel` —
    bind their UI charts to these events. The payload is intentionally small
    and serialisable so the event bus can also log/forward it if needed.
    """

    event_name: ClassVar[str] = "system.metric"
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    disk_percent: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0
    process_memory_mb: float = 0.0
    process_cpu_percent: float = 0.0


__all__ = [
    "DomainEvent",
    "PipelineStarted",
    "PipelineStepCompleted",
    "PipelineCompleted",
    "TaskCreated",
    "TaskProgressUpdated",
    "TaskStatusChanged",
    "LLMTokenGenerated",
    "FFmpegExecuted",
    "SystemMetricSampled",
]
