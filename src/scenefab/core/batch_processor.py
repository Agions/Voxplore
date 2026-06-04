#!/usr/bin/env python3
"""
批量任务处理器 — v2.0 重构

支持：
- 多任务队列（短剧整季 25-50 集）
- 并行 worker（默认 2，可配）
- 自动重试（可配次数）
- 断点续传（基于 SQLite 状态）
- 失败任务隔离（不影响其他任务）
- 进度报告（通过 Qt Signal 或回调）

使用示例:
    from scenefab.core.batch_processor import (
        BatchProcessor, BatchTask, BatchConfig, TaskStatus,
    )

    tasks = [
        BatchTask(id="ep01", video_path=Path("EP01.mp4"), output_dir=Path("out/")),
        BatchTask(id="ep02", video_path=Path("EP02.mp4"), output_dir=Path("out/")),
    ]
    config = BatchConfig(tasks=tasks, parallel_count=2)
    processor = BatchProcessor(config, pipeline_factory=my_pipeline_factory)
    processor.start()
    processor.wait_until_done()
"""

import json
import logging
import queue
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from scenefab.core.audit import AuditLogger

logger = logging.getLogger(__name__)


# ============================================
# 状态 & 数据
# ============================================


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass(slots=True)
class BatchTask:
    """单个批量任务"""

    id: str
    video_path: Path
    output_dir: Path
    preset: str = "default"
    episode_number: int = 0
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    error: str = ""
    result_path: Path | None = None
    attempts: int = 0
    started_at: float = 0.0
    finished_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = uuid.uuid4().hex[:12]
        self.video_path = Path(self.video_path)
        self.output_dir = Path(self.output_dir)

    def duration_ms(self) -> int:
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at) * 1000)
        return 0


@dataclass
class BatchConfig:
    """批量处理配置"""

    tasks: list[BatchTask]
    parallel_count: int = 2
    auto_retry: bool = True
    max_retries: int = 2
    task_timeout_sec: int = 1800
    checkpoint_path: Path | None = None
    on_task_started: Callable[[BatchTask], None] | None = None
    on_task_completed: Callable[[BatchTask], None] | None = None
    on_task_failed: Callable[[BatchTask], None] | None = None
    on_batch_finished: Callable[[list[BatchTask]], None] | None = None


# ============================================
# 断点续传
# ============================================

_CHECKPOINT_SCHEMA = """
CREATE TABLE IF NOT EXISTS batch_checkpoint (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    progress REAL DEFAULT 0,
    attempts INTEGER DEFAULT 0,
    error TEXT DEFAULT '',
    result_path TEXT,
    completed_at TEXT,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_bc_status ON batch_checkpoint(status);
"""


class BatchCheckpoint:
    """批量任务断点管理器（SQLite 持久化）"""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_CHECKPOINT_SCHEMA)
            conn.commit()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def save(self, task: BatchTask) -> None:
        """保存任务状态"""
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO batch_checkpoint
                    (task_id, status, progress, attempts, error, result_path,
                     completed_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        task.id,
                        task.status.value,
                        task.progress,
                        task.attempts,
                        task.error,
                        str(task.result_path) if task.result_path else None,
                        datetime.fromtimestamp(
                            task.finished_at, timezone.utc
                        ).isoformat()
                        if task.finished_at
                        else None,
                        json.dumps(task.metadata, ensure_ascii=False),
                    ),
                )
                conn.commit()

    def load(self, task_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM batch_checkpoint WHERE task_id = ?", (task_id,)
            ).fetchone()
            if not row:
                return None
            return {
                "task_id": row["task_id"],
                "status": row["status"],
                "progress": row["progress"],
                "attempts": row["attempts"],
                "error": row["error"],
                "result_path": row["result_path"],
                "completed_at": row["completed_at"],
                "metadata": json.loads(row["metadata"] or "{}"),
            }

    def get_completed_ids(self) -> set[str]:
        """获取所有已成功完成的任务 ID"""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT task_id FROM batch_checkpoint WHERE status = ?",
                (TaskStatus.COMPLETED.value,),
            ).fetchall()
            return {r["task_id"] for r in rows}

    def clear(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM batch_checkpoint")
                conn.commit()


# ============================================
# 批量处理器
# ============================================


class BatchProcessor:
    """
    批量任务处理器

    内部使用 ThreadPoolExecutor + queue.Queue 实现生产者-消费者
    """

    def __init__(
        self,
        config: BatchConfig,
        pipeline_factory: Callable[[BatchTask], Any],
    ) -> None:
        """
        Args:
            config: 批量配置
            pipeline_factory: 工厂函数 (task) -> pipeline_object
                pipeline_object 必须有 .run(**kwargs) 方法
        """
        self.config = config
        self.pipeline_factory = pipeline_factory
        self._task_queue: queue.Queue[BatchTask] = queue.Queue()
        self._workers: list[threading.Thread] = []
        self._shutdown = threading.Event()
        self._started = False
        self._finished = False
        self._lock = threading.RLock()
        self._audit = AuditLogger()
        self.checkpoint: BatchCheckpoint | None = None
        if config.checkpoint_path:
            self.checkpoint = BatchCheckpoint(config.checkpoint_path)
            self._restore_checkpoints()

    def _restore_checkpoints(self) -> None:
        """从检查点恢复（已完成的任务标记为 COMPLETED）"""
        if not self.checkpoint:
            return
        completed_ids = self.checkpoint.get_completed_ids()
        for task in self.config.tasks:
            if task.id in completed_ids:
                task.status = TaskStatus.COMPLETED
                cp = self.checkpoint.load(task.id)
                if cp and cp.get("result_path"):
                    task.result_path = Path(cp["result_path"])
                logger.info(f"Task {task.id} restored from checkpoint (completed)")

    # ==============================================================
    # 公开 API
    # ==============================================================

    def start(self) -> None:
        """启动批量处理"""
        if self._started:
            logger.warning("BatchProcessor already started")
            return
        self._started = True
        self._finished = False

        # 入队所有 PENDING 任务
        for task in self.config.tasks:
            if task.status == TaskStatus.PENDING:
                self._task_queue.put(task)

        # 启动 worker
        actual_workers = min(self.config.parallel_count, self._task_queue.qsize() or 1)
        for i in range(actual_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"BatchWorker-{i}",
                daemon=True,
            )
            worker.start()
            self._workers.append(worker)

        self._audit.log_action(
            action="batch_start",
            parameters={
                "total_tasks": len(self.config.tasks),
                "parallel_count": actual_workers,
            },
        )
        logger.info(
            f"BatchProcessor started: {len(self.config.tasks)} tasks, "
            f"{actual_workers} workers"
        )

    def wait_until_done(self, timeout: float | None = None) -> None:
        """等待所有任务完成"""
        if not self._started:
            return
        start = time.time()
        while not self._finished:
            if timeout and (time.time() - start) > timeout:
                logger.warning("BatchProcessor wait timeout, forcing shutdown")
                self.shutdown()
                return
            time.sleep(0.5)

    def shutdown(self) -> None:
        """优雅关闭"""
        self._shutdown.set()
        for w in self._workers:
            w.join(timeout=5)
        self._finished = True
        logger.info("BatchProcessor shutdown complete")

    def summary(self) -> dict:
        """获取任务执行摘要"""
        statuses = {s: 0 for s in TaskStatus}
        for task in self.config.tasks:
            statuses[task.status] += 1
        return {
            "total": len(self.config.tasks),
            "by_status": {s.value: n for s, n in statuses.items()},
            "is_finished": self._finished,
            "active_workers": sum(1 for w in self._workers if w.is_alive()),
        }

    # ==============================================================
    # 内部
    # ==============================================================

    def _worker_loop(self) -> None:
        """Worker 主循环"""
        while not self._shutdown.is_set():
            try:
                task = self._task_queue.get(timeout=0.5)
            except queue.Empty:
                # 队列空 + 所有 worker 都闲着 = 完成
                if not any(
                    w.is_alive() and w != threading.current_thread()
                    for w in self._workers
                ):
                    with self._lock:
                        if self._task_queue.empty():
                            self._finished = True
                            self._on_batch_finished()
                            return
                continue

            self._process_task(task)
            self._task_queue.task_done()

    def _process_task(self, task: BatchTask) -> None:
        """处理单个任务（含重试）"""
        max_attempts = self.config.max_retries + 1 if self.config.auto_retry else 1

        for attempt in range(1, max_attempts + 1):
            if self._shutdown.is_set():
                task.status = TaskStatus.CANCELLED
                self._save_checkpoint(task)
                return

            task.attempts = attempt
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()

            self._audit.log_action(
                action="batch_task_start",
                parameters={
                    "task_id": task.id,
                    "video": str(task.video_path),
                    "attempt": attempt,
                },
                task_id=task.id,
            )
            logger.info(f"Task {task.id} attempt {attempt}/{max_attempts}")

            if self.config.on_task_started:
                try:
                    self.config.on_task_started(task)
                except Exception as e:
                    logger.debug(f"on_task_started callback error: {e}")

            try:
                pipeline = self.pipeline_factory(task)
                result_path = pipeline.run(
                    video_path=str(task.video_path),
                    output_dir=str(task.output_dir),
                    episode=task.episode_number,
                    preset=task.preset,
                    metadata=task.metadata,
                )
                task.result_path = Path(result_path) if result_path else None
                task.progress = 1.0
                task.status = TaskStatus.COMPLETED
                task.finished_at = time.time()
                task.error = ""

                self._audit.log_action(
                    action="batch_task_done",
                    parameters={"task_id": task.id, "result": str(task.result_path)},
                    result="success",
                    duration_ms=task.duration_ms(),
                    task_id=task.id,
                )
                self._save_checkpoint(task)

                if self.config.on_task_completed:
                    try:
                        self.config.on_task_completed(task)
                    except Exception as e:
                        logger.debug(f"on_task_completed callback error: {e}")

                logger.info(
                    f"Task {task.id} completed in {task.duration_ms()}ms "
                    f"(attempt {attempt})"
                )
                return

            except Exception as e:
                import traceback

                err_type = type(e).__name__
                err_msg = str(e)[:500]
                logger.error(f"Task {task.id} failed (attempt {attempt}): {e}")
                logger.debug(traceback.format_exc())

                task.error = f"{err_type}: {err_msg}"
                task.finished_at = time.time()

                if attempt < max_attempts:
                    # 退避重试
                    backoff_sec = min(2**attempt, 30)
                    logger.info(f"Retrying task {task.id} in {backoff_sec}s...")
                    time.sleep(backoff_sec)
                else:
                    task.status = TaskStatus.FAILED
                    self._audit.log_action(
                        action="batch_task_failed",
                        parameters={"task_id": task.id, "attempts": attempt},
                        result="failure",
                        duration_ms=task.duration_ms(),
                        error_message=err_msg,
                        error_type=err_type,
                        task_id=task.id,
                    )
                    self._save_checkpoint(task)

                    if self.config.on_task_failed:
                        try:
                            self.config.on_task_failed(task)
                        except Exception as cb_e:
                            logger.debug(f"on_task_failed callback error: {cb_e}")

    def _save_checkpoint(self, task: BatchTask) -> None:
        """保存断点"""
        if self.checkpoint:
            try:
                self.checkpoint.save(task)
            except Exception as e:
                logger.warning(f"Failed to save checkpoint for {task.id}: {e}")

    def _on_batch_finished(self) -> None:
        """批次结束回调"""
        s = self.summary()
        self._audit.log_action(
            action="batch_finished",
            parameters=s,
        )
        logger.info(f"Batch finished: {s}")
        if self.config.on_batch_finished:
            try:
                self.config.on_batch_finished(self.config.tasks)
            except Exception as e:
                logger.debug(f"on_batch_finished callback error: {e}")


__all__ = [
    "BatchProcessor",
    "BatchConfig",
    "BatchTask",
    "BatchCheckpoint",
    "TaskStatus",
]
