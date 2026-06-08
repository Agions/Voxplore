#!/usr/bin/env python3
"""
操作审计日志 — v2.0 重构

提供结构化的操作审计能力：
- AI API 调用（LLM / Vision / TTS）
- FFmpeg 进程执行
- 文件导出
- 流水线步骤开始/结束

特性:
- SQLite 持久化
- 时间戳 + 耗时统计
- 错误信息结构化记录
- 用户可查询历史

使用示例:
    from scenefab.core.audit import AuditLogger, AuditEntry
    from datetime import datetime, timezone

    logger = AuditLogger()  # 默认 ~/.cache/scenefab/audit.db
    logger.log(AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        action="llm_api_call",
        parameters={"model": "deepseek-chat", "tokens": 1024},
        result="success",
        duration_ms=1234,
    ))
"""

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
from typing import Any, Optional

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
    def from_row(cls, row: sqlite3.Row) -> "AuditEntry":
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
# 审计记录器
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


class AuditLogger:
    """
    操作审计日志记录器

    线程安全：内部用 threading.Lock 保护
    """

    _instance: Optional["AuditLogger"] = None
    _instance_lock = threading.Lock()

    def __new__(cls, db_path: Path | None = None) -> "AuditLogger":
        """单例模式"""
        with cls._instance_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._init(
                    db_path or Path("~/.cache/scenefab/audit.db").expanduser()
                )
                cls._instance = instance
            elif db_path is not None and Path(db_path) != Path(cls._instance.db_path):
                # 允许切换 db 路径（主要用于测试）
                cls._instance._init(Path(db_path))
            return cls._instance

    def _init(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ==============================================================
    # 公共 API
    # ==============================================================

    def log(self, entry: AuditEntry) -> None:
        """记录单条审计"""
        with self._lock:
            try:
                with self._connect() as conn:
                    conn.execute(
                        """INSERT OR REPLACE INTO audit_log
                        (id, timestamp, action, parameters, result, duration_ms,
                         error_message, error_type, task_id, step_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        entry.to_row(),
                    )
                    conn.commit()
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")

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
        上下文管理器：自动捕获开始/结束/错误

        使用:
            with audit.track("llm_api_call", {"model": "deepseek"}) as ctx:
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
            # 合并 ctx["extra"] 到 parameters
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

    def query(
        self,
        action: str | None = None,
        task_id: str | None = None,
        result: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """查询审计记录"""
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
        sql = "SELECT COUNT(*) FROM audit_log"
        args: list[Any] = []
        if action:
            sql += " WHERE action = ?"
            args.append(action)
        with self._connect() as conn:
            return conn.execute(sql, args).fetchone()[0]

    def clear(self, before_timestamp: str | None = None) -> int:
        """清理旧记录（返回删除条数）"""
        if before_timestamp is None:
            # 默认清理 90 天前
            from datetime import timedelta

            cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            before_timestamp = cutoff

        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    "DELETE FROM audit_log WHERE timestamp < ?",
                    (before_timestamp,),
                )
                conn.commit()
                return cursor.rowcount


__all__ = [
    "AuditLogger",
    "AuditEntry",
]
