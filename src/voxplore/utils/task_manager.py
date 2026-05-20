#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
后台任务管理器
提供异步任务处理和进度报告
"""

from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Optional, Any, Dict
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """任务信息"""
    id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    message: str = ""
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskManager:
    """
    后台任务管理器

    管理异步任务的执行、进度和取消
    """

    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, Task] = {}
        self._futures: Dict[str, Future] = {}
        self._logger = logging.getLogger(__name__)

    def submit(
        self,
        task_id: str,
        name: str,
        func: Callable,
        *args,
        **kwargs,
    ) -> Task:
        """
        提交任务

        Args:
            task_id: 任务ID
            name: 任务名称
            func: 要执行的函数
            *args, **kwargs: 函数参数

        Returns:
            Task 对象
        """
        task = Task(id=task_id, name=name)
        self._tasks[task_id] = task

        # 包装函数以跟踪进度
        def wrapped_func():
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()

            try:
                # 检查是否有进度回调参数
                progress_callback = kwargs.pop('progress_callback', None)
                if progress_callback:
                    kwargs['progress_callback'] = self._make_progress_callback(task_id, progress_callback)

                result = func(*args, **kwargs)
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.progress = 100.0
                task.completed_at = datetime.now()
                return result

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.now()
                self._logger.error(f"Task {task_id} failed: {e}")
                raise

        future = self._executor.submit(wrapped_func)
        self._futures[task_id] = future

        return task

    def _make_progress_callback(self, task_id: str, callback: Callable):
        """创建进度回调包装"""
        def wrapper(progress: float, message: str = ""):
            task = self._tasks.get(task_id)
            if task:
                task.progress = progress
                task.message = message
            callback(progress, message)
        return wrapper

    def cancel(self, task_id: str) -> bool:
        """取消任务"""
        future = self._futures.get(task_id)
        if future and not future.done():
            future.cancel()
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
            return True
        return False

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务状态"""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, Task]:
        """获取所有任务"""
        return self._tasks.copy()

    def get_active_tasks(self) -> Dict[str, Task]:
        """获取活跃任务"""
        return {
            k: v for k, v in self._tasks.items()
            if v.status in [TaskStatus.PENDING, TaskStatus.RUNNING]
        }

    def cleanup_completed(self, max_age_hours: int = 24):
        """清理已完成的任务"""
        now = datetime.now()
        to_remove = []

        for task_id, task in self._tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                if task.completed_at:
                    age = (now - task.completed_at).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(task_id)

        for task_id in to_remove:
            del self._tasks[task_id]
            if task_id in self._futures:
                del self._futures[task_id]

    def shutdown(self, wait: bool = True):
        """关闭任务管理器"""
        self._executor.shutdown(wait=wait)


# 全局实例
task_manager = TaskManager(max_workers=4)


# 便捷函数
def run_background(
    task_id: str,
    name: str,
    func: Callable,
    *args,
    **kwargs,
) -> Task:
    """提交后台任务"""
    return task_manager.submit(task_id, name, func, *args, **kwargs)


def get_task_status(task_id: str) -> Optional[Task]:
    """获取任务状态"""
    return task_manager.get_task(task_id)


def cancel_task(task_id: str) -> bool:
    """取消任务"""
    return task_manager.cancel(task_id)
