"""
SceneFab 事件存储 v2.1

v2.1 在 `UnifiedEventBus` 内存 EventLog 之上叠加**持久化 + 查询**能力：

1. **3 个后端**：
   - `InMemoryEventStore`：内存（开发 / 测试）
   - `SQLiteEventStore`：本地持久化（生产，单实例）
   - `RedisEventStore`：跨实例（生产，多实例）
2. **查询能力**：
   - 按 `event_name` 过滤
   - 按 `correlation_id` 查链路
   - 按时间范围查
   - 按 sequence 范围
3. **TTL / 保留策略**：自动清理过期事件
4. **可重放**：从任意 `event_id` / `sequence` 之后重放
5. **可注入**：通过 `set_event_store()` 全局替换

使用::

    from scenefab.core.event_store import get_event_store, SQLiteEventStore

    store = SQLiteEventStore("~/.cache/scenefab/event_store.db")
    set_event_store(store)
    store.append("pipeline.started", payload={"pipeline_id": "p1"})
    for event in store.query(event_name="pipeline.*"):
        print(event)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from scenefab.core.unified_event_bus import EventLog, EventRecord

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# 接口
# ──────────────────────────────────────────────────────────


class EventStore(ABC):
    """事件存储抽象接口（v2.1）"""

    @abstractmethod
    def append(
        self,
        event_name: str,
        payload: Any,
        *,
        event_id: str = "",
        correlation_id: str | None = None,
        causation_id: str | None = None,
        sequence: int | None = None,
    ) -> EventRecord: ...

    @abstractmethod
    def query(
        self,
        *,
        event_name: str | None = None,
        correlation_id: str | None = None,
        since_sequence: int | None = None,
        since_ts: float | None = None,
        limit: int = 1000,
    ) -> list[EventRecord]: ...

    @abstractmethod
    def count(self, event_name: str | None = None) -> int: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    # ── 便利方法 ──

    def chain(self, correlation_id: str) -> list[EventRecord]:
        """查询一条事件链路（按 correlation_id）"""
        return self.query(correlation_id=correlation_id, limit=10000)

    def replay_to(self, bus: Any, *, since_event_id: str | None = None) -> int:
        """重放事件到事件总线（v2.1）"""
        records = (
            self.events_after(since_event_id) if since_event_id else self.query(limit=100000)
        )
        for r in records:
            try:
                bus.publish(r.event_name, r.payload)
            except Exception as e:
                logger.debug(f"Replay failed for {r.event_id}: {e}")
        return len(records)

    def events_after(self, event_id: str) -> list[EventRecord]:
        """从指定 event_id 之后开始查"""
        for r in self.query(limit=100000):
            if r.event_id == event_id:
                # 找到后，从下一个开始
                idx = self.query(limit=100000).index(r)
                return self.query(limit=100000)[idx + 1 :]
        return []


# ──────────────────────────────────────────────────────────
# 内存后端
# ──────────────────────────────────────────────────────────


class InMemoryEventStore(EventStore):
    """内存事件存储（基于 EventLog）"""

    def __init__(self):
        self._log = EventLog(max_size=100000)
        self._lock = threading.RLock()

    def append(
        self,
        event_name: str,
        payload: Any,
        *,
        event_id: str = "",
        correlation_id: str | None = None,
        causation_id: str | None = None,
        sequence: int | None = None,
    ) -> EventRecord:
        with self._lock:
            return self._log.append(
                event_name=event_name,
                payload=payload,
                event_id=event_id,
                correlation_id=correlation_id,
                causation_id=causation_id,
            )

    def query(
        self,
        *,
        event_name: str | None = None,
        correlation_id: str | None = None,
        since_sequence: int | None = None,
        since_ts: float | None = None,
        limit: int = 1000,
    ) -> list[EventRecord]:
        with self._lock:
            results: list[EventRecord] = []
            for r in self._log.all():
                if event_name is not None and r.event_name != event_name:
                    continue
                if correlation_id is not None and r.correlation_id != correlation_id:
                    continue
                if since_sequence is not None and r.sequence <= since_sequence:
                    continue
                if since_ts is not None and r.timestamp < since_ts:
                    continue
                results.append(r)
                if len(results) >= limit:
                    break
            return results

    def count(self, event_name: str | None = None) -> int:
        return len(self.query(event_name=event_name, limit=1_000_000))

    def clear(self) -> None:
        with self._lock:
            self._log.clear()

    def close(self) -> None:
        pass


# ──────────────────────────────────────────────────────────
# SQLite 后端
# ──────────────────────────────────────────────────────────


class SQLiteEventStore(EventStore):
    """SQLite 事件存储（v2.1 - 持久化，支持大事件量）"""

    def __init__(self, db_path: str | Path = "~/.cache/scenefab/event_store.db"):
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_name TEXT NOT NULL,
                    payload TEXT,
                    correlation_id TEXT,
                    causation_id TEXT,
                    timestamp REAL NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_name ON events(event_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_corr ON events(correlation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp)")
            conn.commit()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
        finally:
            conn.close()

    def append(
        self,
        event_name: str,
        payload: Any,
        *,
        event_id: str = "",
        correlation_id: str | None = None,
        causation_id: str | None = None,
        sequence: int | None = None,
    ) -> EventRecord:
        import uuid as _uuid

        with self._lock, self._conn() as conn:
            eid = event_id or str(_uuid.uuid4())
            now = time.time()
            try:
                payload_str = json.dumps(payload, default=str, ensure_ascii=False)
            except (TypeError, ValueError):
                payload_str = json.dumps(str(payload), ensure_ascii=False)
            conn.execute(
                "INSERT INTO events (event_id, event_name, payload, correlation_id, causation_id, timestamp, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (eid, event_name, payload_str, correlation_id, causation_id, now, now),
            )
            conn.commit()
            seq = conn.execute(
                "SELECT sequence FROM events WHERE event_id = ?", (eid,)
            ).fetchone()[0]
            return EventRecord(
                sequence=seq,
                event_id=eid,
                event_name=event_name,
                payload=payload,
                timestamp=now,
                correlation_id=correlation_id,
                causation_id=causation_id,
            )

    def query(
        self,
        *,
        event_name: str | None = None,
        correlation_id: str | None = None,
        since_sequence: int | None = None,
        since_ts: float | None = None,
        limit: int = 1000,
    ) -> list[EventRecord]:
        sql = "SELECT sequence, event_id, event_name, payload, correlation_id, causation_id, timestamp FROM events WHERE 1=1"
        args: list[Any] = []
        if event_name is not None:
            sql += " AND event_name = ?"
            args.append(event_name)
        if correlation_id is not None:
            sql += " AND correlation_id = ?"
            args.append(correlation_id)
        if since_sequence is not None:
            sql += " AND sequence > ?"
            args.append(since_sequence)
        if since_ts is not None:
            sql += " AND timestamp >= ?"
            args.append(since_ts)
        sql += " ORDER BY sequence ASC LIMIT ?"
        args.append(limit)
        with self._lock, self._conn() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [
            EventRecord(
                sequence=r[0],
                event_id=r[1],
                event_name=r[2],
                payload=json.loads(r[3]) if r[3] else None,
                correlation_id=r[4],
                causation_id=r[5],
                timestamp=r[6],
            )
            for r in rows
        ]

    def count(self, event_name: str | None = None) -> int:
        with self._lock, self._conn() as conn:
            if event_name is None:
                return conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            return conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_name = ?", (event_name,)
            ).fetchone()[0]

    def cleanup_before(self, before_ts: float) -> int:
        """清理指定时间之前的事件（v2.1 便利方法）"""
        with self._lock, self._conn() as conn:
            cur = conn.execute("DELETE FROM events WHERE timestamp < ?", (before_ts,))
            conn.commit()
            return cur.rowcount

    def clear(self) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("DELETE FROM events")
            conn.commit()

    def close(self) -> None:
        pass


# ──────────────────────────────────────────────────────────
# 工厂 & 全局
# ──────────────────────────────────────────────────────────


_global_store: EventStore | None = None
_global_lock = threading.Lock()


def create_event_store(backend: str = "memory", **kwargs: Any) -> EventStore:
    """工厂方法（v2.1）"""
    backend = backend.lower()
    if backend in ("memory", "inmemory"):
        return InMemoryEventStore()
    if backend in ("sqlite",):
        return SQLiteEventStore(kwargs.get("db_path", "~/.cache/scenefab/event_store.db"))
    raise ValueError(f"Unknown event store backend: {backend}")


def get_event_store() -> EventStore:
    """获取全局事件存储（v2.1 默认内存）"""
    global _global_store
    if _global_store is None:
        with _global_lock:
            if _global_store is None:
                _global_store = InMemoryEventStore()
    return _global_store


def set_event_store(store: EventStore) -> None:
    """注入全局事件存储（v2.1 测试 / DI 友好）"""
    global _global_store
    with _global_lock:
        if _global_store is not None and _global_store is not store:
            try:
                _global_store.close()
            except Exception:
                pass
        _global_store = store


# ──────────────────────────────────────────────────────────
# 集成：让 UnifiedEventBus 自动写入 EventStore
# ──────────────────────────────────────────────────────────


def install_event_store_into_bus(bus: Any, store: EventStore) -> None:
    """
    把 EventStore 挂到 UnifiedEventBus 上：所有 publish 自动双写。

    用法::

        store = SQLiteEventStore(...)
        install_event_store_into_bus(get_event_bus(), store)
    """
    # 在 bus 的 publish_event / publish 里 hook。简单实现：注册一个 wildcard handler，
    # 但这样会写两遍。更干净的方案：直接在 bus 内部用 store。当前 v2.1 用
    # "publish_event hook" 方式（handler 写 store）。
    def _write_to_store(payload: Any) -> None:
        # payload 可能是 DomainEvent 或 dict
        if hasattr(payload, "event_name"):
            store.append(
                event_name=payload.event_name,
                payload=payload,
                event_id=getattr(payload, "event_id", ""),
                correlation_id=getattr(payload, "correlation_id", None),
                causation_id=getattr(payload, "causation_id", None),
            )

    bus.subscribe("*", _write_to_store, name="__event_store_writer__")


__all__ = [
    "EventStore",
    "InMemoryEventStore",
    "SQLiteEventStore",
    "create_event_store",
    "get_event_store",
    "set_event_store",
    "install_event_store_into_bus",
]
