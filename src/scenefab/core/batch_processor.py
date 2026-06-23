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
        BatchProcessor, BatchTask, BatchConfig, BatchBatchTaskStatus,
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
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, wait
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from scenefab.core.audit import AuditLogger

logger = logging.getLogger(__name__)


# ============================================
# 状态 & 数据
# ============================================


class BatchTaskStatus(str, Enum):
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
    status: BatchTaskStatus = BatchTaskStatus.PENDING
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
        with self._lock, self._connect() as conn:
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
                    datetime.fromtimestamp(task.finished_at, timezone.utc).isoformat()
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
                (BatchTaskStatus.COMPLETED.value,),
            ).fetchall()
            return {r["task_id"] for r in rows}

    def clear(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM batch_checkpoint")
            conn.commit()


# ============================================
# 批量处理器
# ============================================


class BatchProcessor:
    """
    批量任务处理器

    内部使用 ThreadPoolExecutor + Future 实现并发调度：
    - 每个 PENDING 任务提交为一个 future
    - 单次尝试通过嵌套 future + result(timeout) 实施真超时
    - 退避重试用 shutdown.wait(backoff) 实现可取消等待
    - wait_until_done 阻塞在 futures 上，不再 busy-poll
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
        self._executor: ThreadPoolExecutor | None = None
        self._futures: list[Future] = []
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
                task.status = BatchTaskStatus.COMPLETED
                cp = self.checkpoint.load(task.id)
                if cp and cp.get("result_path"):
                    task.result_path = Path(cp["result_path"])
                logger.info(f"Task {task.id} restored from checkpoint (completed)")

    # ==============================================================
    # 公开 API
    # ==============================================================

    def start(self) -> None:
        """启动批量处理（提交所有 PENDING 任务到线程池）"""
        if self._started:
            logger.warning("BatchProcessor already started")
            return
        self._started = True
        self._finished = False

        pending = [t for t in self.config.tasks if t.status == BatchTaskStatus.PENDING]
        actual_workers = max(1, min(self.config.parallel_count, len(pending) or 1))

        self._executor = ThreadPoolExecutor(
            max_workers=actual_workers,
            thread_name_prefix="BatchWorker",
        )
        self._futures = [
            self._executor.submit(self._process_task, task) for task in pending
        ]

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
        """阻塞等待所有任务完成（不再 busy-poll）。

        超时则强制关闭。
        """
        if not self._started:
            return
        if not self._futures:
            self._mark_batch_finished()
            return

        done, not_done = wait(self._futures, timeout=timeout)
        if not_done:
            logger.warning("BatchProcessor wait timeout, forcing shutdown")
            self.shutdown()
            return
        self._mark_batch_finished()

    def shutdown(self) -> None:
        """优雅关闭：置取消标志、取消未开始的 future、释放线程池"""
        self._shutdown.set()
        if self._executor is not None:
            # 取消尚未开始的 future；已运行的由 _shutdown 标志协作退出
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None
        self._finished = True
        logger.info("BatchProcessor shutdown complete")

    def _mark_batch_finished(self) -> None:
        """标记批次完成、释放线程池、触发 on_batch_finished（幂等）。"""
        with self._lock:
            if self._finished:
                return
            self._finished = True
        if self._executor is not None:
            self._executor.shutdown(wait=False)
            self._executor = None
        self._on_batch_finished()

    def summary(self) -> dict:
        """获取任务执行摘要"""
        statuses = dict.fromkeys(BatchTaskStatus, 0)
        for task in self.config.tasks:
            statuses[task.status] += 1
        active = sum(1 for f in self._futures if f.running())
        return {
            "total": len(self.config.tasks),
            "by_status": {s.value: n for s, n in statuses.items()},
            "is_finished": self._finished,
            "active_workers": active,
        }

    # ==============================================================
    # 内部
    # ==============================================================

    def _process_task(self, task: BatchTask) -> None:
        """处理单个任务（含重试）

        编排重试循环；具体逻辑委托给以下辅助方法：
        - _prepare_attempt: 标记 RUNNING、写审计、触发 on_task_started
        - _execute_attempt: 调用 pipeline 并标记 COMPLETED
        - _handle_attempt_failure: 记录错误、退避或标记 FAILED
        """
        max_attempts = self.config.max_retries + 1 if self.config.auto_retry else 1

        for attempt in range(1, max_attempts + 1):
            if self._shutdown.is_set():
                task.status = BatchTaskStatus.CANCELLED
                self._save_checkpoint(task)
                return

            self._prepare_attempt(task, attempt, max_attempts)

            try:
                self._execute_attempt(task, attempt)
                return
            except Exception as e:
                self._handle_attempt_failure(task, attempt, max_attempts, e)

    def _prepare_attempt(
        self, task: BatchTask, attempt: int, max_attempts: int
    ) -> None:
        """标记任务进入 RUNNING、记录审计日志、触发 on_task_started 回调"""
        task.attempts = attempt
        task.status = BatchTaskStatus.RUNNING
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

    def _execute_attempt(self, task: BatchTask, attempt: int) -> None:
        """构造 pipeline、执行一次（带超时）、成功则标记 COMPLETED 并写审计/回调。

        超时通过嵌套单发线程 + result(timeout) 实施：超时抛 TimeoutError 由
        上层重试逻辑捕获。注意底层 pipeline.run 不可强制中断，超时后仍会在后台
        运行至自然结束（守护线程），但任务本身已按超时失败处理。
        """
        pipeline = self.pipeline_factory(task)

        def _run() -> Any:
            return pipeline.run(
                video_path=str(task.video_path),
                output_dir=str(task.output_dir),
                episode=task.episode_number,
                preset=task.preset,
                metadata=task.metadata,
            )

        timeout = self.config.task_timeout_sec
        if timeout and timeout > 0:
            runner = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix=f"BatchTask-{task.id}"
            )
            try:
                result_path = runner.submit(_run).result(timeout=timeout)
            finally:
                # 不等待后台线程（pipeline.run 不可中断），避免阻塞 worker
                runner.shutdown(wait=False)
        else:
            result_path = _run()

        task.result_path = Path(result_path) if result_path else None
        task.progress = 1.0
        task.status = BatchTaskStatus.COMPLETED
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

    def _handle_attempt_failure(
        self, task: BatchTask, attempt: int, max_attempts: int, exc: Exception
    ) -> None:
        """单次尝试失败后的处理：记日志、按指数退避重试或标记 FAILED + 写审计"""
        import traceback

        err_type = type(exc).__name__
        err_msg = str(exc)[:500]
        logger.error(f"Task {task.id} failed (attempt {attempt}): {exc}")
        logger.debug(traceback.format_exc())

        task.error = f"{err_type}: {err_msg}"
        task.finished_at = time.time()

        if attempt < max_attempts:
            # 指数退避重试；用 shutdown.wait 实现可取消等待（关闭时立即返回）
            backoff_sec = min(2**attempt, 30)
            logger.info(f"Retrying task {task.id} in {backoff_sec}s...")
            self._shutdown.wait(backoff_sec)
            return

        task.status = BatchTaskStatus.FAILED
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
    "BatchTaskStatus",  # 注意：已从 TaskStatus 重命名，消除与 core.task_model 的命名冲突
]
