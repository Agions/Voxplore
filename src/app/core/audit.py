#!/usr/bin/env python3
"""
操作审计日志 — v2.0 重构（Phase 4 · WAL + 批量 flush）

提供结构化的操作审计能力：
- AI API 调用（LLM / Vision / TTS）
- FFmpeg 进程执行
- 文件导出
- 流水线步骤开始/结束

特性：
- SQLite 持久化（启用 WAL + synchronous=NORMAL）
- 后台 flush 线程：累积到阈值或时间到即批量写库
- 时间戳 + 耗时统计
- 错误信息结构化记录
- 用户可查询历史

使用示例：
    from app.core.audit import AuditLogger, AuditEntry
    from datetime import datetime, timezone

    logger = AuditLogger()  # 默认 ~/.cache/scenefab/audit.db
    logger.log(AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        action="llm_api_call",
        parameters={"model": "kimi-k3", "tokens": 1024},
        result="success",
        duration_ms=1234,
    ))
    logger.flush()  # 强制刷盘
    logger.close()  # 退出时调用，停止后台线程
"""

from __future__ import annotations

import atexit
import json
import logging
import sqlite3
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ============================================
# 数据模型
# ============================================


@dataclass(slots=True)
class AuditEntry:
    """单条审计记录"""

    timestamp: str
    action: str  # e.g. "llm_api_call", "ffmpeg_execute", "file_export"
    parameters: dict[str, Any]
    result: str  # "success" | "failure" | "cancelled"
    duration_ms: int = 0
    error_message: str = ""
    error_type: str = ""
    task_id: str = ""
    step_id: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])

    def to_row(self) -> tuple:
        return (
            self.id,
            self.timestamp,
            self.action,
            json.dumps(self.parameters, ensure_ascii=False),
            self.result,
            self.duration_ms,
            self.error_message,
            self.error_type,
            self.task_id,
            self.step_id,
        )

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> AuditEntry:
        return cls(
            id=row["id"],
            timestamp=row["timestamp"],
            action=row["action"],
            parameters=json.loads(row["parameters"] or "{}"),
            result=row["result"],
            duration_ms=row["duration_ms"],
            error_message=row["error_message"] or "",
            error_type=row["error_type"] or "",
            task_id=row["task_id"] or "",
            step_id=row["step_id"] or "",
        )


# ============================================
# Schema（启用 WAL）
# ============================================


_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    parameters TEXT,
    result TEXT NOT NULL,
    duration_ms INTEGER DEFAULT 0,
    error_message TEXT DEFAULT '',
    error_type TEXT DEFAULT '',
    task_id TEXT DEFAULT '',
    step_id TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_result ON audit_log(result);
CREATE INDEX IF NOT EXISTS idx_audit_task_id ON audit_log(task_id);
"""


# ============================================
# 审计记录器（WAL + 批量 flush）
# ============================================


class AuditLogger:
    """操作审计日志记录器。

    线程安全：内部 ``_buffer_lock`` 保护 in-memory buffer；``_flush_lock`` 保护
    SQLite 连接。WAL 模式下多个 reader 与一个 writer 可并发。

    写盘策略：
    - 调用方 ``log(entry)`` → entry 进入内存队列（O(1)）
    - 后台 flush 线程每 ``flush_interval_seconds`` 或累积 ``flush_batch_size``
      条时一次性 INSERT（用 executemany）
    - 应用退出时 ``atexit`` 钩子强制 ``flush()`` + ``close()``

    兼容性：所有 v1.x 公共 API（``log``、``log_action``、``track``、``query``、
    ``count``、``clear``）保持不变。
    """

    # 批量 flush 默认阈值
    DEFAULT_FLUSH_BATCH_SIZE = 32
    DEFAULT_FLUSH_INTERVAL_S = 1.0

    _instance: AuditLogger | None = None
    _instance_lock = threading.Lock()

    def __new__(cls, db_path: Path | None = None) -> AuditLogger:
        with cls._instance_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._init(
                    db_path or Path("~/.cache/scenefab/audit.db").expanduser()
                )
                cls._instance = instance
                atexit.register(instance._atexit_close)
            elif db_path is not None and Path(db_path) != Path(cls._instance.db_path):
                # 切换 db 路径（测试场景）
                cls._instance._flush_blocking()
                cls._instance._init(Path(db_path))
            return cls._instance

    def _init(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # 双锁：buffer 锁 vs flush 锁，避免 log() 和 flush() 互相阻塞
        self._buffer_lock = threading.Lock()
        self._flush_lock = threading.Lock()
        self._buffer: list[AuditEntry] = []
        self._closed = False
        self._flush_batch_size = self.DEFAULT_FLUSH_BATCH_SIZE
        self._flush_interval = self.DEFAULT_FLUSH_INTERVAL_S
        self._init_db()
        self._start_flush_thread()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            # 启用 WAL + 折中持久性（normal 而非 full）
            try:
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")
            except sqlite3.DatabaseError as e:
                logger.warning(f"Failed to enable WAL on audit db: {e}")
            conn.commit()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        # WAL 模式下需要 check_same_thread=False 以允许多线程
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
            check_same_thread=False,
            isolation_level=None,  # autocommit；我们手动 commit
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _start_flush_thread(self) -> None:
        self._flush_stop = threading.Event()
        self._flush_thread = threading.Thread(
            target=self._flush_loop, name="audit-flush", daemon=True
        )
        self._flush_thread.start()

    def _flush_loop(self) -> None:
        while not self._flush_stop.wait(self._flush_interval):
            try:
                self._flush_blocking()
            except Exception as e:  # noqa: BLE001 — 后台循环吞所有错误
                logger.error(f"Audit background flush failed: {e}")

    def _atexit_close(self) -> None:
        try:
            self.close()
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Audit atexit close failed: {e}")

    # ==============================================================
    # 公共 API（保持向后兼容）
    # ==============================================================

    def log(self, entry: AuditEntry) -> None:
        """记录单条审计（enqueue 到 buffer，后台 flush）。"""
        if self._closed:
            logger.debug("AuditLogger closed; dropping entry")
            return
        with self._buffer_lock:
            self._buffer.append(entry)
            should_flush = len(self._buffer) >= self._flush_batch_size
        if should_flush:
            self._flush_blocking()

    def log_action(
        self,
        action: str,
        parameters: dict[str, Any],
        result: str = "success",
        duration_ms: int = 0,
        error_message: str = "",
        error_type: str = "",
        task_id: str = "",
        step_id: str = "",
    ) -> AuditEntry:
        """便捷接口：记录一条审计（自动填充 timestamp）"""
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            parameters=parameters,
            result=result,
            duration_ms=duration_ms,
            error_message=error_message,
            error_type=error_type,
            task_id=task_id,
            step_id=step_id,
        )
        self.log(entry)
        return entry

    @contextmanager
    def track(
        self,
        action: str,
        parameters: dict[str, Any] | None = None,
        task_id: str = "",
        step_id: str = "",
    ) -> Iterator[dict]:
        """
        上下文管理器：自动捕获开始/结束/错误。

        使用：
            with audit.track("llm_api_call", {"model": "kimi-k3"}) as ctx:
                response = call_llm(...)
                ctx["tokens"] = len(response.content)
        """
        parameters = parameters or {}
        ctx: dict = {"extra": {}}
        start_ms = int(time.time() * 1000)
        result = "success"
        err_msg = ""
        err_type = ""
        try:
            yield ctx
        except Exception as e:
            result = "failure"
            err_msg = str(e)
            err_type = type(e).__name__
            raise
        finally:
            duration_ms = int(time.time() * 1000) - start_ms
            final_params = {**parameters, **ctx.get("extra", {})}
            self.log_action(
                action=action,
                parameters=final_params,
                result=result,
                duration_ms=duration_ms,
                error_message=err_msg,
                error_type=err_type,
                task_id=task_id,
                step_id=step_id,
            )

    def flush(self) -> int:
        """公开 flush 接口（非阻塞：buffer 取出后由 SQLite 异步 commit）。"""
        return self._flush_blocking()

    def _flush_blocking(self) -> int:
        """把 buffer 中累积的 entry 一次写入数据库。"""
        with self._buffer_lock:
            if not self._buffer:
                return 0
            batch, self._buffer = self._buffer, []

        rows = [e.to_row() for e in batch]
        with self._flush_lock:
            try:
                with self._connect() as conn:
                    conn.executemany(
                        """INSERT OR REPLACE INTO audit_log
                        (id, timestamp, action, parameters, result, duration_ms,
                         error_message, error_type, task_id, step_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        rows,
                    )
                    conn.commit()
                return len(rows)
            except Exception as e:
                logger.error(
                    f"Failed to flush audit batch ({len(rows)} entries): {e}")
                # 失败时不丢数据，把 batch 放回 buffer
                with self._buffer_lock:
                    self._buffer = batch + self._buffer
                return 0

    def query(
        self,
        action: str | None = None,
        task_id: str | None = None,
        result: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """查询审计记录（会先 flush pending buffer 以保证 read-your-writes）。"""
        self._flush_blocking()
        sql = "SELECT * FROM audit_log WHERE 1=1"
        args: list[Any] = []
        if action:
            sql += " AND action = ?"
            args.append(action)
        if task_id:
            sql += " AND task_id = ?"
            args.append(task_id)
        if result:
            sql += " AND result = ?"
            args.append(result)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        args.append(limit)

        with self._connect() as conn:
            rows = conn.execute(sql, args).fetchall()
            return [AuditEntry.from_row(row) for row in rows]

    def count(self, action: str | None = None) -> int:
        """统计记录数"""
        self._flush_blocking()
        sql = "SELECT COUNT(*) FROM audit_log"
        args: list[Any] = []
        if action:
            sql += " WHERE action = ?"
            args.append(action)
        with self._connect() as conn:

            return conn.execute(sql, args).fetchone()[0]

    def clear(self, before_timestamp: str | None = None) -> int:
        """清理旧记录（返回删除条数）"""
        self._flush_blocking()
        if before_timestamp is None:
            from datetime import timedelta

            cutoff = (datetime.now(timezone.utc) -
                      timedelta(days=90)).isoformat()
            before_timestamp = cutoff

        with self._flush_lock, self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM audit_log WHERE timestamp < ?",
                (before_timestamp,),
            )
            conn.commit()
            return cursor.rowcount

    # ==============================================================
    # 生命周期
    # ==============================================================

    def buffer_size(self) -> int:
        """当前 in-memory 缓冲条数（用于诊断面板）。"""
        with self._buffer_lock:
            return len(self._buffer)

    def close(self) -> None:
        """停止后台线程并 flush 残余条目。"""
        if self._closed:
            return
        self._closed = True
        if hasattr(self, "_flush_stop"):
            self._flush_stop.set()
        if hasattr(self, "_flush_thread"):
            self._flush_thread.join(timeout=2.0)
        self._flush_blocking()


__all__ = [
    "AuditLogger",
    "AuditEntry",
]
