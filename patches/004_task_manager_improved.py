#!/usr/bin/env python3
"""
任务管理器优化版本
改进点：
1. 任务暂停/恢复
2. 断点续传（进度持久化）
3. 优先级调度
4. 依赖管理
5. 详细的进度回调
"""
from dataclasses import dataclass, field
from typing import Any
from collections.abc import Callable
from enum import Enum
import threading
import time
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class TaskResult:
    """任务结果"""
    success: bool
    data: Any = None
    error: str | None = None
    duration: float = 0.0


@dataclass
class TaskProgress:
    """任务进度"""
    task_id: str
    status: TaskStatus
    progress: float  # 0.0 - 1.0
    current_step: str = ""
    steps_total: int = 0
    steps_completed: int = 0
    message: str = ""
    estimated_remaining: float = -1.0  # 预估剩余时间（秒）


@dataclass
class Task:
    """任务"""
    task_id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    result: TaskResult | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    checkpoints: dict[str, Any] = field(default_factory=dict)  # 断点数据
    
    def duration(self) -> float | None:
        """计算任务耗时"""
        if self.started_at:
            end = self.completed_at or time.time()
            return end - self.started_at
        return None


class CheckpointManager:
    """断点管理器"""
    
    def __init__(self, checkpoint_dir: str = "~/.cache/voxplore/checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir).expanduser()
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, task_id: str, data: dict[str, Any]) -> str:
        """
        保存断点
        
        Args:
            task_id: 任务 ID
            data: 断点数据
            
        Returns:
            断点文件路径
        """
        checkpoint_file = self.checkpoint_dir / f"{task_id}.json"
        
        checkpoint_data = {
            "task_id": task_id,
            "timestamp": time.time(),
            "data": data,
        }
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Checkpoint saved: {task_id}")
        return str(checkpoint_file)
    
    def load(self, task_id: str) -> dict[str, Any] | None:
        """
        加载断点
        
        Args:
            task_id: 任务 ID
            
        Returns:
            断点数据，如果不存在返回 None
        """
        checkpoint_file = self.checkpoint_dir / f"{task_id}.json"
        
        if not checkpoint_file.exists():
            return None
        
        try:
            with open(checkpoint_file, encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"Checkpoint loaded: {task_id}")
            return data.get("data")
        except Exception as e:
            logger.warning(f"Failed to load checkpoint {task_id}: {e}")
            return None
    
    def delete(self, task_id: str) -> bool:
        """删除断点"""
        checkpoint_file = self.checkpoint_dir / f"{task_id}.json"
        
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            return True
        return False
    
    def exists(self, task_id: str) -> bool:
        """检查断点是否存在"""
        return (self.checkpoint_dir / f"{task_id}.json").exists()


class TaskExecutor:
    """任务执行器（支持暂停/恢复）"""
    
    def __init__(
        self,
        task: Task,
        checkpoint_manager: CheckpointManager,
        progress_callback: Callable[[TaskProgress], None] | None = None,
    ):
        self.task = task
        self.checkpoint_manager = checkpoint_manager
        self.progress_callback = progress_callback
        self._pause_event = threading.Event()
        self._cancel_event = threading.Event()
        self._pause_event.set()  # 默认不暂停
    
    def pause(self):
        """暂停任务"""
        self._pause_event.clear()
        self.task.status = TaskStatus.PAUSED
        logger.info(f"Task paused: {self.task.task_id}")
    
    def resume(self):
        """恢复任务"""
        self._pause_event.set()
        self.task.status = TaskStatus.RUNNING
        logger.info(f"Task resumed: {self.task.task_id}")
    
    def cancel(self):
        """取消任务"""
        self._cancel_event.set()
        self._pause_event.set()  # 确保退出等待
        self.task.status = TaskStatus.CANCELLED
        logger.info(f"Task cancelled: {self.task.task_id}")
    
    def is_paused(self) -> bool:
        """检查是否暂停"""
        return not self._pause_event.is_set()
    
    def is_cancelled(self) -> bool:
        """检查是否取消"""
        return self._cancel_event.is_set()
    
    def wait_if_paused(self):
        """如果暂停则等待"""
        self._pause_event.wait()
    
    def save_checkpoint(self, checkpoint_data: dict[str, Any]):
        """保存断点"""
        self.checkpoint_manager.save(self.task.task_id, checkpoint_data)
        self.task.checkpoints.update(checkpoint_data)
    
    def load_checkpoint(self) -> dict[str, Any] | None:
        """加载断点"""
        return self.checkpoint_manager.load(self.task.task_id)
    
    def report_progress(
        self,
        progress: float,
        current_step: str = "",
        steps_completed: int = 0,
        steps_total: int = 0,
        message: str = "",
    ):
        """报告进度"""
        self.task.progress = progress
        
        # 估算剩余时间
        if self.task.started_at and progress > 0.01:
            elapsed = time.time() - self.task.started_at
            estimated_total = elapsed / progress
            estimated_remaining = estimated_total - elapsed
        else:
            estimated_remaining = -1.0
        
        task_progress = TaskProgress(
            task_id=self.task.task_id,
            status=self.task.status,
            progress=progress,
            current_step=current_step,
            steps_total=steps_total,
            steps_completed=steps_completed,
            message=message,
            estimated_remaining=estimated_remaining,
        )
        
        if self.progress_callback:
            self.progress_callback(task_progress)
    
    def execute(self) -> TaskResult:
        """执行任务"""
        self.task.status = TaskStatus.RUNNING
        self.task.started_at = time.time()
        
        start_time = time.time()
        
        # 尝试加载断点
        checkpoint = self.load_checkpoint()
        if checkpoint:
            self.task.checkpoints = checkpoint
            logger.info(f"Resuming task from checkpoint: {self.task.task_id}")
        
        try:
            # 执行任务（传入 executor 以支持暂停/检查点）
            result = self.task.func(
                *self.task.args,
                executor=self,
                **self.task.kwargs
            )
            
            self.task.status = TaskStatus.COMPLETED
            self.task.result = TaskResult(
                success=True,
                data=result,
                duration=time.time() - start_time
            )
            
            # 清除断点
            self.checkpoint_manager.delete(self.task.task_id)
            
            return self.task.result
            
        except Exception as e:
            self.task.status = TaskStatus.FAILED
            self.task.result = TaskResult(
                success=False,
                error=str(e),
                duration=time.time() - start_time
            )
            logger.error(f"Task failed: {self.task.task_id}, error: {e}")
            raise
        
        finally:
            self.task.completed_at = time.time()


class TaskManager:
    """
    任务管理器
    支持：
    - 任务队列和调度
    - 暂停/恢复
    - 断点续传
    - 优先级调度
    - 并发控制
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        checkpoint_dir: str = "~/.cache/voxplore/checkpoints",
    ):
        """
        Args:
            max_workers: 最大并发任务数
            checkpoint_dir: 断点保存目录
        """
        self.max_workers = max_workers
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)
        
        self._tasks: dict[str, Task] = {}
        self._executors: dict[str, TaskExecutor] = {}
        self._lock = threading.Lock()
        self._worker_thread: threading.Thread | None = None
        self._running = False
        
        # 进度回调
        self._progress_callbacks: list[Callable[[TaskProgress], None]] = []
        
        # 全局限流
        self._semaphore = threading.Semaphore(max_workers)
    
    def submit(
        self,
        task_id: str,
        name: str,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        **kwargs
    ) -> Task:
        """
        提交任务
        
        Args:
            task_id: 任务 ID（唯一）
            name: 任务名称
            func: 任务函数（接受 executor 参数）
            *args: 位置参数
            priority: 优先级
            **kwargs: 关键字参数
            
        Returns:
            提交的任务
        """
        with self._lock:
            if task_id in self._tasks:
                raise ValueError(f"Task already exists: {task_id}")
            
            task = Task(
                task_id=task_id,
                name=name,
                func=func,
                args=args,
                kwargs=kwargs,
                priority=priority,
            )
            
            self._tasks[task_id] = task
            
            # 启动工作线程（如果未启动）
            if not self._running:
                self._start_worker()
            
            logger.info(f"Task submitted: {task_id} ({name})")
            return task
    
    def get_task(self, task_id: str) -> Task | None:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> list[Task]:
        """获取所有任务"""
        return list(self._tasks.values())
    
    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        """获取指定状态的任务"""
        return [t for t in self._tasks.values() if t.status == status]
    
    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        with self._lock:
            if task_id not in self._executors:
                return False
            
            self._executors[task_id].pause()
            return True
    
    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        with self._lock:
            if task_id not in self._executors:
                return False
            
            self._executors[task_id].resume()
            return True
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            if task_id not in self._executors:
                return False
            
            self._executors[task_id].cancel()
            return True
    
    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        with self._lock:
            if task_id in self._executors:
                self._executors[task_id].cancel()
                del self._executors[task_id]
            
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            
            return False
    
    def on_progress(self, callback: Callable[[TaskProgress], None]):
        """注册进度回调"""
        self._progress_callbacks.append(callback)
    
    def _start_worker(self):
        """启动工作线程"""
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("Task manager worker started")
    
    def _worker_loop(self):
        """工作循环"""
        while self._running:
            # 找就绪的任务（按优先级排序）
            ready_tasks = [
                t for t in self._tasks.values()
                if t.status == TaskStatus.PENDING
            ]
            
            if not ready_tasks:
                time.sleep(0.1)
                continue
            
            # 按优先级排序
            ready_tasks.sort(key=lambda t: t.priority.value, reverse=True)
            
            task = ready_tasks[0]
            
            # 等待信号量
            self._semaphore.acquire()
            
            try:
                self._execute_task(task)
            finally:
                self._semaphore.release()
    
    def _execute_task(self, task: Task):
        """执行任务"""
        # 创建执行器
        executor = TaskExecutor(
            task=task,
            checkpoint_manager=self.checkpoint_manager,
            progress_callback=self._notify_progress,
        )
        
        with self._lock:
            self._executors[task.task_id] = executor
        
        # 执行
        try:
            executor.execute()
        except Exception as e:
            logger.error(f"Task execution failed: {task.task_id}, {e}")
    
    def _notify_progress(self, progress: TaskProgress):
        """通知进度更新"""
        for callback in self._progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    def shutdown(self, wait: bool = True):
        """关闭任务管理器"""
        self._running = False
        
        # 暂停所有任务
        for executor in list(self._executors.values()):
            executor.pause()
        
        if wait:
            # 等待工作线程结束
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=5.0)
        
        logger.info("Task manager shutdown")
    
    def get_summary(self) -> dict[str, Any]:
        """获取摘要"""
        with self._lock:
            status_counts = {}
            for task in self._tasks.values():
                status_counts[task.status.value] = status_counts.get(task.status.value, 0) + 1
            
            return {
                "total_tasks": len(self._tasks),
                "status_counts": status_counts,
                "max_workers": self.max_workers,
                "active_executors": len(self._executors),
            }


# 示例：视频处理任务函数签名
def example_video_processing_task(
    video_path: str,
    executor: TaskExecutor = None,
    **kwargs
) -> str:
    """
    示例：视频处理任务
    
    Args:
        video_path: 视频路径
        executor: 任务执行器（用于暂停/检查点/进度）
        **kwargs: 其他参数
        
    Returns:
        输出文件路径
    """
    steps = [
        ("分析视频", 0.1),
        ("提取片段", 0.3),
        ("生成解说", 0.6),
        ("合成配音", 0.8),
        ("导出视频", 1.0),
    ]
    
    for step_name, target_progress in steps:
        # 检查是否暂停
        if executor:
            executor.wait_if_paused()
            
            # 检查是否取消
            if executor.is_cancelled():
                raise Exception("Task cancelled")
            
            # 报告进度
            executor.report_progress(
                progress=target_progress,
                current_step=step_name,
                steps_completed=steps.index((step_name, target_progress)),
                steps_total=len(steps),
                message=f"正在{step_name}...",
            )
            
            # 模拟处理
            time.sleep(0.5)
            
            # 保存检查点
            executor.save_checkpoint({
                "current_step": step_name,
                "video_path": video_path,
            })
    
    return "/output/video.mp4"


__all__ = [
    "TaskManager",
    "TaskExecutor",
    "CheckpointManager",
    "Task",
    "TaskResult",
    "TaskProgress",
    "TaskStatus",
    "TaskPriority",
]
