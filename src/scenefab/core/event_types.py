"""
SceneFab 事件类型定义 v2.1

统一的领域事件 schema：
- 强类型 payload (Pydantic BaseModel)
- 继承 DomainEvent 基类，自带 event_id / timestamp / correlation_id
- 类型化事件 vs 字符串事件兼容（v1.x 字符串事件保持工作）

v2.1 目标：让事件总线具备"可观测 + 可重放 + 类型安全"三种能力
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar

try:
    from pydantic import BaseModel, Field

    _HAS_PYDANTIC = True
except ImportError:  # 兼容未装 pydantic
    _HAS_PYDANTIC = False
    BaseModel = object  # type: ignore[assignment,misc]

    def Field(*args, **kwargs):
        return None


# ──────────────────────────────────────────────────────────
# 事件基类
# ──────────────────────────────────────────────────────────


@dataclass
class DomainEvent:
    """
    领域事件基类（dataclass 实现，零依赖）

    所有 v2.1 类型化事件必须继承此类。
    event_name 必须全局唯一（推荐格式："<domain>.<action>"）
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    correlation_id: str | None = None
    causation_id: str | None = None  # 上一个事件 ID（事件溯源链）

    # 子类必须设置
    event_name: ClassVar[str] = "domain.event"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "payload": self._payload_dict(),
        }

    def _payload_dict(self) -> dict[str, Any]:
        """子类重写以暴露业务字段"""
        return {}


# ──────────────────────────────────────────────────────────
# Pydantic 强类型事件（可选）
# ──────────────────────────────────────────────────────────


if _HAS_PYDANTIC:

    class _EventModel(BaseModel):
        """Pydantic 风格强类型事件基类"""

        event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
        timestamp: str = Field(
            default_factory=lambda: datetime.now(timezone.utc).isoformat()
        )
        correlation_id: str | None = None
        causation_id: str | None = None

        model_config = {"frozen": False, "extra": "allow"}


# ──────────────────────────────────────────────────────────
# 预定义事件类型（Pipeline 业务流）
# ──────────────────────────────────────────────────────────


@dataclass
class PipelineStarted(DomainEvent):
    event_name: ClassVar[str] = "pipeline.started"
    pipeline_id: str = ""
    total_steps: int = 0
    inputs: dict[str, Any] = field(default_factory=dict)

    def _payload_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "total_steps": self.total_steps,
            "inputs": self.inputs,
        }


@dataclass
class PipelineStepStarted(DomainEvent):
    event_name: ClassVar[str] = "pipeline.step.started"
    pipeline_id: str = ""
    step_id: str = ""
    step_name: str = ""
    parallel_group: str | None = None

    def _payload_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "step_id": self.step_id,
            "step_name": self.step_name,
            "parallel_group": self.parallel_group,
        }


@dataclass
class PipelineStepCompleted(DomainEvent):
    event_name: ClassVar[str] = "pipeline.step.completed"
    pipeline_id: str = ""
    step_id: str = ""
    status: str = "success"  # success | failed | skipped
    duration_ms: int = 0
    result: Any = None
    error: str | None = None

    def _payload_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "step_id": self.step_id,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


@dataclass
class PipelineCompleted(DomainEvent):
    event_name: ClassVar[str] = "pipeline.completed"
    pipeline_id: str = ""
    total_duration_ms: int = 0
    success_count: int = 0
    failure_count: int = 0

    def _payload_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "total_duration_ms": self.total_duration_ms,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }


@dataclass
class TaskCreated(DomainEvent):
    event_name: ClassVar[str] = "task.created"
    task_id: str = ""
    task_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def _payload_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "metadata": self.metadata,
        }


@dataclass
class TaskProgressUpdated(DomainEvent):
    event_name: ClassVar[str] = "task.progress.updated"
    task_id: str = ""
    progress: float = 0.0
    current_step: str = ""
    step_index: int = 0

    def _payload_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "progress": self.progress,
            "current_step": self.current_step,
            "step_index": self.step_index,
        }


@dataclass
class TaskStatusChanged(DomainEvent):
    event_name: ClassVar[str] = "task.status.changed"
    task_id: str = ""
    old_status: str = ""
    new_status: str = ""
    error: str | None = None
    result_path: str | None = None

    def _payload_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "error": self.error,
            "result_path": self.result_path,
        }


@dataclass
class LLMTokenGenerated(DomainEvent):
    event_name: ClassVar[str] = "llm.token.generated"
    request_id: str = ""
    model: str = ""
    token: str = ""
    cumulative_tokens: int = 0

    def _payload_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "model": self.model,
            "token": self.token,
            "cumulative_tokens": self.cumulative_tokens,
        }


@dataclass
class FFmpegExecuted(DomainEvent):
    event_name: ClassVar[str] = "ffmpeg.executed"
    command_hash: str = ""
    return_code: int = 0
    duration_ms: int = 0
    error: str | None = None

    def _payload_dict(self) -> dict[str, Any]:
        return {
            "command_hash": self.command_hash,
            "return_code": self.return_code,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


# 导出所有事件类名
__all__ = [
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
]
