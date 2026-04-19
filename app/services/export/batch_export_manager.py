"""
批量导出管理器
支持多个项目或多个片段的批量导出
"""

import os
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading
from ....core.exceptions import ExportError, ProjectError

logger = logging.getLogger(__name__)


class ExportStatus(Enum):
    """导出状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExportTask:
    """导出任务"""
    id: str
    name: str
    project_path: str
    output_path: str
    format: str = "mp4"
    quality: str = "high"
    status: ExportStatus = ExportStatus.PENDING
    progress: float = 0.0
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class BatchExportResult:
    """批量导出结果"""
    total: int
    completed: int
    failed: int
    cancelled: int
    total_time: float
    results: List[Dict[str, Any]] = field(default_factory=list)


class BatchExportManager:
    """批量导出管理器"""

    def __init__(
        self, 
        max_parallel: int = 2,
        on_progress: Optional[Callable[[str, float], None]] = None,
        on_complete: Optional[Callable[[str, bool, Optional[str]], None]] = None
    ):
        """
        初始化批量导出管理器
        
        Args:
            max_parallel: 最大并行导出数
            on_progress: 进度回调 (task_id, progress)
            on_complete: 完成回调 (task_id, success, error)
        """
        self.max_parallel = max_parallel
        self.on_progress = on_progress
        self.on_complete = on_complete
        self._tasks: Dict[str, ExportTask] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_parallel)
        self._running_tasks: Dict[str, Any] = {}
        self._cancelled: set = set()

    def add_task(
        self,
        task_id: str,
        name: str,
        project_path: str,
        output_path: str,
        format: str = "mp4",
        quality: str = "high"
    ) -> ExportTask:
        """添加导出任务"""
        task = ExportTask(
            id=task_id,
            name=name,
            project_path=project_path,
            output_path=output_path,
            format=format,
            quality=quality
        )
        self._tasks[task_id] = task
        return task

    def add_tasks_from_projects(
        self,
        projects: List[Dict[str, Any]],
        output_dir: str,
        format: str = "mp4",
        quality: str = "high"
    ) -> List[ExportTask]:
        """
        从项目列表添加批量任务
        
        Args:
            projects: 项目列表 [{id, name, path}, ...]
            output_dir: 输出目录
            format: 导出格式
            quality: 导出质量
            
        Returns:
            任务列表
        """
        tasks = []
        
        for project in projects:
            task_id = f"export_{project['id']}"
            output_path = os.path.join(
                output_dir, 
                f"{project['name']}.{format}"
            )
            
            task = self.add_task(
                task_id=task_id,
                name=project['name'],
                project_path=project['path'],
                output_path=output_path,
                format=format,
                quality=quality
            )
            tasks.append(task)
            
        return tasks

    def start(self) -> BatchExportResult:
        """开始批量导出"""
        start_time = time.time()
        
        # 准备任务
        pending_tasks = [
            task for task in self._tasks.values()
            if task.status == ExportStatus.PENDING
        ]
        
        completed = 0
        failed = 0
        cancelled = 0
        results = []

        # 提交所有任务
        futures = {}
        for task in pending_tasks:
            future = self._executor.submit(self._export_single, task)
            futures[future] = task

        # 等待完成
        for future in as_completed(futures):
            task = futures[future]
            
            if task.id in self._cancelled:
                task.status = ExportStatus.CANCELLED
                cancelled += 1
                continue
                
            try:
                success, error = future.result()
                
                if success:
                    task.status = ExportStatus.COMPLETED
                    completed += 1
                    results.append({
                        "task_id": task.id,
                        "name": task.name,
                        "output_path": task.output_path,
                        "success": True
                    })
                else:
                    task.status = ExportStatus.FAILED
                    task.error = error
                    failed += 1
                    results.append({
                        "task_id": task.id,
                        "name": task.name,
                        "success": False,
                        "error": error
                    })
                    
            except Exception as e:
                task.status = ExportStatus.FAILED
                task.error = str(e)
                failed += 1
                logger.error(f"导出任务失败: {task.name}, {e}")
                
            # 回调
            if self.on_complete:
                self.on_complete(
                    task.id,
                    task.status == ExportStatus.COMPLETED,
                    task.error
                )

        total_time = time.time() - start_time
        
        return BatchExportResult(
            total=len(pending_tasks),
            completed=completed,
            failed=failed,
            cancelled=cancelled,
            total_time=total_time,
            results=results
        )

    def _export_single(self, task: ExportTask) -> tuple[bool, Optional[str]]:
        """执行单个导出任务"""
        task.status = ExportStatus.RUNNING
        task.started_at = time.time()

        try:
            logger.info(f"开始导出: {task.name} → {task.output_path}")

            # 加载项目数据
            import json
            from pathlib import Path

            project_path = Path(task.project_path)
            if project_path.exists() and project_path.suffix == '.json':
                with open(project_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
            else:
                # 如果是目录，尝试读取 project.json
                proj_file = project_path / 'project.json'
                if proj_file.exists():
                    with open(proj_file, 'r', encoding='utf-8') as f:
                        project_data = json.load(f)
                else:
                    project_data = {"source": str(project_path)}

            # 构建导出配置
            from .export_manager import ExportManager, ExportFormat, ExportConfig

            fmt_map = {
                "mp4": ExportFormat.MP4,
                "mov": ExportFormat.MOV,
                "gif": ExportFormat.GIF,
                "jianying": ExportFormat.JIANYING,
            }
            export_fmt = fmt_map.get(task.format.lower(), ExportFormat.MP4)

            config = ExportConfig(
                format=export_fmt,
                quality=task.quality,
                output_path=task.output_path,
                progress_callback=lambda p: (
                    setattr(task, 'progress', p),
                    self.on_progress(task.id, p) if self.on_progress else None
                ) if self.on_progress else None,
            )

            # 执行实际导出
            manager = ExportManager()
            success = manager.export(project_data, config)

            if task.id in self._cancelled:
                raise ExportError("任务已取消")

            if success:
                task.progress = 100.0
                task.completed_at = time.time()
                logger.info(f"导出完成: {task.name}")
                return True, None
            else:
                raise ExportError(
                    "导出失败",
                    details={"reason": "ExportManager returned False"}
                )

        except Exception as e:
            task.error = str(e)
            task.completed_at = time.time()
            logger.error(f"导出失败: {task.name}, {e}")
            return False, str(e)

    def cancel_task(self, task_id: str) -> bool:
        """取消单个任务"""
        if task_id in self._tasks:
            self._cancelled.add(task_id)
            return True
        return False

    def cancel_all(self) -> None:
        """取消所有任务"""
        for task_id in self._tasks:
            self._cancelled.add(task_id)

    def get_task(self, task_id: str) -> Optional[ExportTask]:
        """获取任务状态"""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[ExportTask]:
        """获取所有任务"""
        return list(self._tasks.values())

    def get_progress(self) -> Dict[str, Any]:
        """获取总体进度"""
        total = len(self._tasks)
        if total == 0:
            return {"total": 0, "progress": 0}
            
        completed = sum(
            1 for t in self._tasks.values() 
            if t.status == ExportStatus.COMPLETED
        )
        failed = sum(
            1 for t in self._tasks.values() 
            if t.status == ExportStatus.FAILED
        )
        running = sum(
            1 for t in self._tasks.values() 
            if t.status == ExportStatus.RUNNING
        )
        
        # 计算平均进度
        avg_progress = sum(t.progress for t in self._tasks.values()) / total
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "progress": avg_progress
        }

    def clear(self) -> None:
        """清理已完成的任务"""
        self._tasks = {
            task_id: task 
            for task_id, task in self._tasks.items()
            if task.status in [ExportStatus.PENDING, ExportStatus.RUNNING]
        }
        self._cancelled.clear()

    def shutdown(self) -> None:
        """关闭管理器"""
        self.cancel_all()
        self._executor.shutdown(wait=True)


# 全局实例
_batch_export_manager: Optional[BatchExportManager] = None
_batch_lock = threading.Lock()


def get_batch_export_manager() -> BatchExportManager:
    """获取全局批量导出管理器"""
    global _batch_export_manager
    if _batch_export_manager is None:
        with _batch_lock:
            if _batch_export_manager is None:
                _batch_export_manager = BatchExportManager()
    return _batch_export_manager
