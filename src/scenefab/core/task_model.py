"""
SceneFab 统一任务模型 v2.1

目标：让 TaskManager + BatchProcessor + PipelineEngine 共享同一份任务状态机。
v2.1 新增：
- 标准状态机：PENDING → RUNNING → (PAUSED ↔ RUNNING) → (COMPLETED | FAILED | CANCELLED)
- 任务来源标识：batch / pipeline / api / cli 四种来源
- 进度细粒度：0.0-1.0 → 派生 overall / per-step
- 取消令牌（CancelToken）支持协作式取消
- 状态转换由 `_transition_to()` 统一管理，禁止非法跳转
- 状态变更发布为 DomainEvent（订阅者可以观察所有任务生命周期）
"""

from __future__ import annotations

import enum
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from scenefab.core.event_types import (
    TaskCreated,
    TaskProgressUpdated,
    TaskStatusChanged,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# 状态机
# ──────────────────────────────────────────────────────────


class TaskStatus(str, enum.Enum):
    """任务状态（v2.1 统一枚举）"""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """是否为终止状态（不可再变更）"""
        return self in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    @property
    def is_active(self) -> bool:
        """是否活跃中（占用资源）"""
        return self in (TaskStatus.RUNNING, TaskStatus.PAUSED)


# 合法状态转换图
ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.FAILED},
    TaskStatus.RUNNING: {
        TaskStatus.PAUSED,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.PAUSED: {TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.FAILED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


class IllegalTransitionError(RuntimeError):
    """非法状态转换异常"""


# ──────────────────────────────────────────────────────────
# 任务来源
# ──────────────────────────────────────────────────────────


class TaskSource(str, enum.Enum):
    """任务来源（v2.1）"""

    BATCH = "batch"          # 批量处理器
    PIPELINE = "pipeline"    # PipelineEngine
    API = "api"              # FastAPI endpoint
    CLI = "cli"              # CLI 命令
    MANUAL = "manual"        # 直接调用


# ──────────────────────────────────────────────────────────
# 取消令牌
# ──────────────────────────────────────────────────────────


class CancelToken:
    """协作式取消令牌（v2.1）

    用法::

        token = CancelToken()
        # 在 worker 循环里：
        if token.cancelled:
            return
    """

    def __init__(self):
        self._cancelled = False
        self._reason: str | None = None
        self._cancelled_at: float | None = None

    def cancel(self, reason: str = "user_cancelled") -> None:
        if not self._cancelled:
            self._cancelled = True
            self._reason = reason
            self._cancelled_at = time.time()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def reason(self) -> str | None:
        return self._reason

    def __bool__(self) -> bool:
        return not self._cancelled


# ──────────────────────────────────────────────────────────
# 统一任务模型
# ──────────────────────────────────────────────────────────


@dataclass
class TaskStep:
    """单个任务步骤（v2.1 细粒度进度）"""

    step_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    started_at: float | None = None
    completed_at: float | None = None
    error: str | None = None
    result: Any = None

    def duration_ms(self) -> int:
        if self.started_at is None:
            return 0
        end = self.completed_at or time.time()
        return int((end - self.started_at) * 1000)


@dataclass
class UnifiedTask:
    """
    统一任务模型 v2.1

    取代 v1.x 的 TaskManager.Task（保持字段基本兼容）。
    新增：source / cancel_token / step 列表 / 领域事件发布
    """

    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    source: TaskSource = TaskSource.MANUAL
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    steps: list[TaskStep] = field(default_factory=list)
    current_step_index: int = 0
    cancel_token: CancelToken = field(default_factory=CancelToken)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    error: str | None = None
    result: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    # v2.1：事件发布回调（可注入 event_bus）
    on_event: Callable[[Any], None] | None = None

    def progress_percent(self) -> int:
        return int(self.progress * 100)

    def duration_ms(self) -> int:
        if self.started_at is None:
            return 0
        end = self.completed_at or time.time()
        return int((end - self.started_at) * 1000)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "source": self.source.value,
            "status": self.status.value,
            "progress": self.progress,
            "current_step_index": self.current_step_index,
            "current_step": (
                self.steps[self.current_step_index].name
                if self.steps and 0 <= self.current_step_index < len(self.steps)
                else ""
            ),
            "total_steps": len(self.steps),
            "steps": [
                {
                    "step_id": s.step_id,
                    "name": s.name,
                    "status": s.status.value,
                    "progress": s.progress,
                    "duration_ms": s.duration_ms(),
                    "error": s.error,
                }
                for s in self.steps
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms(),
            "error": self.error,
            "result": self.result if self.result is None or _is_jsonable(self.result) else str(self.result),
            "metadata": self.metadata,
            "cancelled": self.cancel_token.cancelled,
            "cancel_reason": self.cancel_token.reason,
        }

    # ── 状态转换（统一入口）──

    def _transition_to(self, new_status: TaskStatus) -> None:
        """统一状态转换（带合法性校验 + 事件发布）"""
        old = self.status
        if old == new_status:
            return
        allowed = ALLOWED_TRANSITIONS.get(old, set())
        if new_status not in allowed:
            raise IllegalTransitionError(
                f"Illegal transition for task {self.task_id}: {old.value} → {new_status.value}"
            )
        self.status = new_status
        self.updated_at = time.time()
        if new_status == TaskStatus.RUNNING and self.started_at is None:
            self.started_at = self.updated_at
        if new_status.is_terminal:
            self.completed_at = self.updated_at
        # 状态转换事件
        if self.on_event is not None:
            try:
                self.on_event(
                    TaskStatusChanged(
                        task_id=self.task_id,
                        old_status=old.value,
                        new_status=new_status.value,
                        error=self.error,
                        result_path=str(self.result) if isinstance(self.result, str) else None,
                    )
                )
            except Exception as e:
                logger.debug(f"TaskStatusChanged event publish failed: {e}")

    def mark_running(self) -> None:
        self._transition_to(TaskStatus.RUNNING)

    def mark_paused(self) -> None:
        self._transition_to(TaskStatus.PAUSED)

    def mark_completed(self, result: Any = None) -> None:
        if result is not None:
            self.result = result
        self.progress = 1.0
        self._transition_to(TaskStatus.COMPLETED)

    def mark_failed(self, error: str) -> None:
        self.error = error
        self._transition_to(TaskStatus.FAILED)

    def mark_cancelled(self, reason: str = "user_cancelled") -> None:
        self.cancel_token.cancel(reason)
        self._transition_to(TaskStatus.CANCELLED)

    def update_progress(
        self,
        progress: float,
        *,
        current_step_name: str | None = None,
        current_step_index: int | None = None,
        step_progress: float | None = None,
    ) -> None:
        """更新进度（细粒度）"""
        progress = max(0.0, min(1.0, progress))
        self.progress = progress
        self.updated_at = time.time()
        if current_step_index is not None:
            self.current_step_index = current_step_index
        if current_step_name and self.steps and 0 <= self.current_step_index < len(self.steps):
            self.steps[self.current_step_index].name = current_step_name
        if step_progress is not None and self.steps and 0 <= self.current_step_index < len(self.steps):
            self.steps[self.current_step_index].progress = max(
                0.0, min(1.0, step_progress)
            )
        if self.on_event is not None:
            try:
                self.on_event(
                    TaskProgressUpdated(
                        task_id=self.task_id,
                        progress=progress,
                        current_step=current_step_name or "",
                        step_index=self.current_step_index,
                    )
                )
            except Exception as e:
                logger.debug(f"TaskProgressUpdated event publish failed: {e}")


def _is_jsonable(obj: Any) -> bool:
    """轻量 JSON 可序列化检查"""
    try:
        import json

        json.dumps(obj)
        return True
    except (TypeError, ValueError):
        return False


# ──────────────────────────────────────────────────────────
# 状态机工具
# ──────────────────────────────────────────────────────────


def can_transition(old: TaskStatus, new: TaskStatus) -> bool:
    """检查状态转换是否合法"""
    return new in ALLOWED_TRANSITIONS.get(old, set())


__all__ = [
    "TaskStatus",
    "TaskSource",
    "CancelToken",
    "TaskStep",
    "UnifiedTask",
    "IllegalTransitionError",
    "ALLOWED_TRANSITIONS",
    "can_transition",
]
