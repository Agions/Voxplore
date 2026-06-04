#!/usr/bin/env python3
"""
SceneFab 任务管理 V2
支持任务暂停、恢复、取消、断点续传
- 异步保存（不阻塞主线程）
- JSON 序列化（跨平台兼容）
- 批量操作优化
- **v2.1 增强**：发布 DomainEvent 到 UnifiedEventBus（订阅者可观察任务生命周期）
"""
import logging
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# v2.1: 桥接事件总线（DomainEvent 发布）
try:
    from scenefab.core.unified_event_bus import get_event_bus
    from scenefab.core.event_types import (
        TaskCreated as _TaskCreatedEvent,
        TaskProgressUpdated as _TaskProgressEvent,
        TaskStatusChanged as _TaskStatusEvent,
    )
    _HAS_V21_BUS = True
except ImportError:
    _HAS_V21_BUS = False

# orjson 性能比标准 json 快 5-10 倍
try:
    import orjson
    _json_loads = orjson.loads
    def _json_dumps(obj):
        return orjson.dumps(obj, option=orjson.OPT_INDENT_2)
    _use_orjson = True
except ImportError:
    import json
    _json_loads = json.load
    def _json_dumps(obj):
        return json.dumps(obj, ensure_ascii=False, indent=2)
    _use_orjson = False

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class TaskCheckpoint:
    """任务检查点"""
    task_id: str
    step: int
    step_name: str
    progress: float
    data: dict[str, Any]
    timestamp: float
    file_path: str = ""


@dataclass
class Task:
    """任务"""
    task_id: str
    name: str
    status: TaskStatus
    progress: float
    current_step: str
    steps: list[str]
    current_step_index: int
    result: Any | None
    error: str | None
    created_at: float
    updated_at: float
    checkpoints: list[TaskCheckpoint] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def progress_percent(self) -> int:
        return int(self.progress * 100)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status.value,
            "progress": self.progress,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
            "steps": self.steps,
            "current_step_index": self.current_step_index,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


class TaskManager:
    """
    任务管理器 V2
    支持任务的创建、暂停、恢复、取消、断点续传
    - 异步保存，不阻塞主线程
    - JSON 序列化替代 pickle
    - 批量操作支持
    """

    _instance: Optional['TaskManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._tasks: dict[str, Task] = {}
        self._lock = threading.RLock()  # 可重入锁
        self._executor = ThreadPoolExecutor(max_workers=2)  # 异步保存线程池
        self._task_dir = os.path.expanduser("~/.cache/scenefab/tasks")
        self._checkpoints_dir = os.path.join(self._task_dir, "checkpoints")

        os.makedirs(self._task_dir, exist_ok=True)
        os.makedirs(self._checkpoints_dir, exist_ok=True)

        # 加载已存在的任务
        self._load_tasks()

    def _load_tasks(self):
        """加载已存在的任务"""
        try:
            for file in Path(self._task_dir).glob("*.json"):
                try:
                    if _use_orjson:
                        with open(file, 'rb') as f:
                            data = orjson.loads(f.read())
                    else:
                        with open(file, encoding='utf-8') as f:
                            data = json.load(f)
                    task = self._dict_to_task(data)
                    self._tasks[task.task_id] = task
                except Exception as e:
                    logger.warning(f"Failed to load task {file}: {e}")
        except Exception as e:
            logger.warning(f"Failed to load tasks: {e}")

    def _save_task_async(self, task: Task):
        """异步保存任务到磁盘"""
        def _write():
            try:
                file_path = os.path.join(self._task_dir, f"{task.task_id}.json")
                temp_path = file_path + ".tmp"
                if _use_orjson:
                    with open(temp_path, 'wb') as f:
                        f.write(orjson.dumps(task.to_dict(), option=orjson.OPT_INDENT_2))
                else:
                    with open(temp_path, 'w', encoding='utf-8') as f:
                        json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)
                os.replace(temp_path, file_path)
            except Exception as e:
                logger.error(f"Failed to save task: {e}")

        self._executor.submit(_write)

    def _save_task(self, task: Task):
        """同步保存任务到磁盘（保留兼容性）"""
        try:
            file_path = os.path.join(self._task_dir, f"{task.task_id}.json")
            temp_path = file_path + ".tmp"
            if _use_orjson:
                with open(temp_path, 'wb') as f:
                    f.write(orjson.dumps(task.to_dict(), option=orjson.OPT_INDENT_2))
            else:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)
            os.replace(temp_path, file_path)
        except Exception as e:
            logger.error(f"Failed to save task: {e}")

    def _dict_to_task(self, data: dict) -> Task:
        """从字典创建任务"""
        checkpoints = [
            TaskCheckpoint(**cp) for cp in data.get("checkpoints", [])
        ]

        return Task(
            task_id=data["task_id"],
            name=data["name"],
            status=TaskStatus(data["status"]),
            progress=data["progress"],
            current_step=data["current_step"],
            steps=data["steps"],
            current_step_index=data["current_step_index"],
            result=data.get("result"),
            error=data.get("error"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            checkpoints=checkpoints,
            metadata=data.get("metadata", {})
        )

    def create_task(
        self,
        name: str,
        steps: list[str] = None,
        metadata: dict[str, Any] = None
    ) -> str:
        """
        创建新任务

        Args:
            name: 任务名称
            steps: 任务步骤列表
            metadata: 附加数据

        Returns:
            任务 ID
        """
        task_id = str(uuid.uuid4())[:8]

        if steps is None:
            steps = ["准备", "处理", "完成"]

        now = datetime.now().timestamp()

        task = Task(
            task_id=task_id,
            name=name,
            status=TaskStatus.PENDING,
            progress=0.0,
            current_step=steps[0] if steps else "",
            steps=steps,
            current_step_index=0,
            result=None,
            error=None,
            created_at=now,
            updated_at=now,
            metadata=metadata or {}
        )

        with self._lock:
            self._tasks[task_id] = task

        self._save_task(task)

        logger.info(f"Created task: {task_id} - {name}")

        # v2.1: 发布 TaskCreated 领域事件
        if _HAS_V21_BUS:
            try:
                get_event_bus().publish_event(
                    _TaskCreatedEvent(
                        task_id=task_id,
                        task_name=name,
                        metadata=metadata or {},
                    )
                )
            except Exception as e:
                logger.debug(f"TaskCreated event publish failed: {e}")

        return task_id

    def get_task(self, task_id: str) -> Task | None:
        """获取任务"""
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self) -> list[Task]:
        """列出所有任务"""
        with self._lock:
            return list(self._tasks.values())

    def update_progress(
        self,
        task_id: str,
        progress: float,
        step: str = None,
        step_index: int = None,
        **kwargs
    ):
        """更新任务进度"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return

            task.progress = progress
            task.updated_at = datetime.now().timestamp()

            if step is not None:
                task.current_step = step
            if step_index is not None:
                task.current_step_index = step_index

            # 保存检查点
            if progress > 0 and len(task.steps) > 0:
                checkpoint = TaskCheckpoint(
                    task_id=task_id,
                    step=step_index or task.current_step_index,
                    step_name=step or task.current_step,
                    progress=progress,
                    data=kwargs,
                    timestamp=datetime.now().timestamp()
                )
                task.checkpoints.append(checkpoint)

            self._save_task(task)

        # v2.1: 发布 TaskProgressUpdated 领域事件
        if _HAS_V21_BUS:
            try:
                get_event_bus().publish_event(
                    _TaskProgressEvent(
                        task_id=task_id,
                        progress=progress,
                        current_step=step or "",
                        step_index=step_index if step_index is not None else 0,
                    )
                )
            except Exception as e:
                logger.debug(f"TaskProgressUpdated event publish failed: {e}")

    def set_status(
        self,
        task_id: str,
        status: TaskStatus,
        error: str = None,
        result: Any = None
    ):
        """设置任务状态"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return

            old_status = task.status
            task.status = status
            task.updated_at = datetime.now().timestamp()

            if error is not None:
                task.error = error
            if result is not None:
                task.result = result

            self._save_task(task)

        # v2.1: 发布 TaskStatusChanged 领域事件
        if _HAS_V21_BUS:
            try:
                get_event_bus().publish_event(
                    _TaskStatusEvent(
                        task_id=task_id,
                        old_status=old_status.value,
                        new_status=status.value,
                        error=error,
                        result_path=str(result) if isinstance(result, str) else None,
                    )
                )
            except Exception as e:
                logger.debug(f"TaskStatusChanged event publish failed: {e}")

    def pause(self, task_id: str) -> bool:
        """暂停任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != TaskStatus.RUNNING:
                return False

            task.status = TaskStatus.PAUSED
            task.updated_at = datetime.now().timestamp()
            self._save_task(task)

            logger.info(f"Paused task: {task_id}")
            return True

    def resume(self, task_id: str) -> bool:
        """恢复任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != TaskStatus.PAUSED:
                return False

            task.status = TaskStatus.RUNNING
            task.updated_at = datetime.now().timestamp()
            self._save_task(task)

            logger.info(f"Resumed task: {task_id}")
            return True

    def cancel(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                return False

            task.status = TaskStatus.CANCELLED
            task.updated_at = datetime.now().timestamp()
            self._save_task(task)

            logger.info(f"Cancelled task: {task_id}")
            return True

    def remove(self, task_id: str) -> bool:
        """删除任务"""
        with self._lock:
            if task_id not in self._tasks:
                return False

            del self._tasks[task_id]

            # 删除磁盘文件
            task_file = os.path.join(self._task_dir, f"{task_id}.json")
            if os.path.exists(task_file):
                os.remove(task_file)

            return True

    def get_checkpoint(self, task_id: str) -> TaskCheckpoint | None:
        """获取最新检查点"""
        task = self.get_task(task_id)
        if not task or not task.checkpoints:
            return None

        return task.checkpoints[-1]

    def save_checkpoint(
        self,
        task_id: str,
        step: int,
        step_name: str,
        data: dict[str, Any]
    ):
        """保存检查点（JSON 格式）"""
        checkpoint = {
            "task_id": task_id,
            "step": step,
            "step_name": step_name,
            "progress": 0.0,
            "data": data,
            "timestamp": datetime.now().timestamp()
        }

        checkpoint_file = os.path.join(
            self._checkpoints_dir,
            f"{task_id}_checkpoint_{step}.json"
        )

        try:
            temp_path = checkpoint_file + ".tmp"
            if _use_orjson:
                with open(temp_path, 'wb') as f:
                    f.write(orjson.dumps(checkpoint, option=orjson.OPT_INDENT_2))
            else:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(checkpoint, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, checkpoint_file)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def load_checkpoint(self, task_id: str, step: int) -> TaskCheckpoint | None:
        """加载检查点"""
        checkpoint_file = os.path.join(
            self._checkpoints_dir,
            f"{task_id}_checkpoint_{step}.json"
        )

        if not os.path.exists(checkpoint_file):
            return None

        try:
            if _use_orjson:
                with open(checkpoint_file, 'rb') as f:
                    data = orjson.loads(f.read())
            else:
                with open(checkpoint_file, encoding='utf-8') as f:
                    data = json.load(f)
            return TaskCheckpoint(**data)
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None


# 全局实例
task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """获取任务管理器"""
    return task_manager


__all__ = [
    "TaskStatus",
    "TaskCheckpoint",
    "Task",
    "TaskManager",
    "task_manager",
    "get_task_manager",
]
