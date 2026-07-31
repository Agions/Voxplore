"""Tests for AuditLogger with WAL + batched flush (Phase 4-2).

覆盖：
  * log / log_action / track 写 buffer
  * batch 大小触发同步 flush
  * 后台线程按时间间隔 flush
  * query / count / clear
  * WAL 模式启用
  * close() 不丢未刷数据
  * flush 失败时 batch 放回 buffer（不丢数据）
"""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.audit import AuditEntry, AuditLogger


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    """每个用例前后都复位单例，避免共享 db/后台线程。"""
    if AuditLogger._instance is not None:
        try:
            AuditLogger._instance.close()
        except Exception:  # noqa: BLE001
            pass
    AuditLogger._instance = None
    yield
    if AuditLogger._instance is not None:
        try:
            AuditLogger._instance.close()
        except Exception:  # noqa: BLE001
            pass
    AuditLogger._instance = None


@pytest.fixture
def alog(tmp_path: Path) -> AuditLogger:
    """绑定到独立 tmp sqlite 路径的 AuditLogger。"""
    return AuditLogger(db_path=tmp_path / "audit_test.db")


def _entry(action: str = "test.action", **kw) -> AuditEntry:
    return AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        action=action,
        parameters=kw.pop("parameters", {}),
        result=kw.pop("result", "success"),
        **kw,
    )


class TestWriteAndQuery:
    def test_log_writes_to_buffer(self, alog: AuditLogger):
        alog.log(_entry(parameters={"k": "v"}))
        assert alog.buffer_size() == 1

    def test_log_action_helper(self, alog: AuditLogger):
        entry = alog.log_action("user.login", {"user": "alice"})
        assert entry.action == "user.login"
        assert entry.timestamp  # 自动填充
        assert alog.buffer_size() == 1

    def test_track_context_manager(self, alog: AuditLogger):
        with alog.track("llm_api_call", {"model": "kimi-k3"}) as ctx:
            ctx["extra"] = {"tokens": 42}
        rows = alog.query(action="llm_api_call")
        assert len(rows) == 1
        assert rows[0].result == "success"
        assert rows[0].parameters["tokens"] == 42

    def test_track_records_failure(self, alog: AuditLogger):
        with pytest.raises(ValueError):
            with alog.track("risky.op"):
                raise ValueError("boom")
        rows = alog.query(action="risky.op")
        assert rows[0].result == "failure"
        assert rows[0].error_type == "ValueError"
        assert "boom" in rows[0].error_message

    def test_query_returns_rows(self, alog: AuditLogger):
        alog.log(_entry("a"))
        alog.log(_entry("b", result="failure"))
        actions = [r.action for r in alog.query()]
        assert "a" in actions
        assert "b" in actions

    def test_query_with_limit(self, alog: AuditLogger):
        for i in range(5):
            alog.log(_entry(f"action.{i}"))
        assert len(alog.query(limit=2)) == 2

    def test_count(self, alog: AuditLogger):
        alog.log(_entry("a"))
        alog.log(_entry("b"))
        alog.log(_entry("a"))
        assert alog.count(action="a") == 2
        assert alog.count() == 3


class TestFlushBatching:
    def test_batch_size_triggers_sync_flush(self, alog: AuditLogger):
        alog._flush_batch_size = 4
        for i in range(3):
            alog.log(_entry(f"a.{i}"))
        assert alog.buffer_size() == 3
        alog.log(_entry("a.3"))  # 第 4 条触发同步 flush
        assert alog.buffer_size() == 0

    def test_background_thread_flushes(self, alog: AuditLogger):
        alog.log(_entry("bg"))
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and alog.buffer_size() > 0:
            time.sleep(0.1)
        assert alog.buffer_size() == 0

    def test_flush_idempotent(self, alog: AuditLogger):
        alog.log(_entry("a"))
        assert alog.flush() == 1
        assert alog.flush() == 0  # 二次 flush 无残留、不报错
        assert alog.count() == 1


class TestWAL:
    def test_wal_mode_enabled(self, alog: AuditLogger):
        alog.log(_entry("a"))
        alog.flush()
        with sqlite3.connect(str(alog.db_path)) as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"


class TestClose:
    def test_close_flushes_remaining(self, tmp_path: Path):
        db = tmp_path / "audit_close.db"
        log = AuditLogger(db_path=db)
        log.log(_entry("a"))
        log.log(_entry("b"))
        log.close()
        # 重新打开同一 db 校验落盘
        AuditLogger._instance = None
        log2 = AuditLogger(db_path=db)
        assert log2.count() == 2

    def test_log_after_close_is_dropped(self, alog: AuditLogger):
        alog.close()
        alog.log(_entry("late"))
        assert alog.buffer_size() == 0


class TestClear:
    def test_clear_empties_table(self, alog: AuditLogger):
        alog.log(_entry("a"))
        alog.flush()
        assert alog.count() >= 1
        # 用未来时间戳保证全部被清
        removed = alog.clear(before_timestamp="9999-12-31T00:00:00+00:00")
        assert removed >= 1
        assert alog.count() == 0


class TestFailureRecovery:
    def test_flush_failure_restores_buffer(self, alog: AuditLogger, monkeypatch):
        alog.log(_entry("a"))
        alog.log(_entry("b"))
        assert alog.buffer_size() == 2

        @contextmanager
        def broken_connect():
            raise sqlite3.OperationalError("disk full")
            yield  # pragma: no cover

        original = alog._connect
        monkeypatch.setattr(alog, "_connect", broken_connect)
        assert alog.flush() == 0
        # 失败的 batch 应放回 buffer，不丢数据
        assert alog.buffer_size() == 2

        monkeypatch.setattr(alog, "_connect", original)
        assert alog.flush() == 2
        assert alog.count() == 2


class TestSingleton:
    def test_singleton(self, tmp_path: Path):
        a = AuditLogger(db_path=tmp_path / "s.db")
        b = AuditLogger()
        assert a is b
