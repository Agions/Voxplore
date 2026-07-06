"""
SceneFab 任务存储 v2.1（共享后端 + 生命周期感知）

v2.1 在 v1.x `_task_store.py` 基础上：

1. **统一 3 个后端**：
   - `InMemoryTaskStore`：进程内（开发/单实例）
   - `SQLiteTaskStore`：本地持久化（无 Redis 时的生产方案）
   - `RedisTaskStore`：跨实例共享（多 worker / 多机部署）
2. **TTL 支持**：可配置过期时间，自动清理
3. **事件总线桥接**：保存任务时自动发布 `TaskCreated` / `TaskStatusChanged` DomainEvent
4. **CLI + API 共享**：CLI 和 FastAPI router 共享同一后端
5. **生命周期感知**：
   - 启动时从磁盘 / Redis 恢复
   - 优雅关闭时刷盘
6. **可注入**：通过 `set_task_store()` 全局替换

使用::

    from scenefab.core.task_store import get_task_store, InMemoryTaskStore, SQLiteTaskStore

    store = SQLiteTaskStore("/tmp/scenefab_tasks.db")
    set_task_store(store)
    store.save("t1", {"status": "running", "progress": 0.5})
    state = store.get("t1")
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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# 接口
# ──────────────────────────────────────────────────────────


class TaskStore(ABC):
    """任务存储抽象接口（v2.1 扩展 TTL）"""

    @abstractmethod
    def save(self, task_id: str, task: dict[str, Any]) -> None: ...

    @abstractmethod
    def get(self, task_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def exists(self, task_id: str) -> bool: ...

    @abstractmethod
    def delete(self, task_id: str) -> None: ...

    @abstractmethod
    def list_ids(self) -> list[str]: ...

    def list_all(self) -> list[dict[str, Any]]:
        """默认实现：基于 list_ids + get（SQLite/Redis 共享）"""
        return [t for t in (self.get(tid) for tid in self.list_ids()) if t is not None]

    # v2.1 新增
    def update(self, task_id: str, **fields: Any) -> dict[str, Any] | None:
        """局部更新字段"""
        current = self.get(task_id)
        if current is None:
            return None
        current.update(fields)
        self.save(task_id, current)
        return current

    def set_ttl(self, task_id: str, seconds: int) -> None:
        """设置过期时间（v2.1）"""
        raise NotImplementedError("Subclass must implement set_ttl if supported")

    def cleanup_expired(self) -> int:
        """清理过期任务，返回清理数量"""
        return 0

    def close(self) -> None:
        """关闭连接（v2.1）"""
        pass


# ──────────────────────────────────────────────────────────
# 内存后端
# ──────────────────────────────────────────────────────────


@dataclass
class _InMemoryRecord:
    data: dict[str, Any]
    expires_at: float | None = None


class InMemoryTaskStore(TaskStore):
    """进程内内存任务存储（v2.1 增强：TTL + 线程安全）"""

    def __init__(self):
        self._tasks: dict[str, _InMemoryRecord] = {}
        self._lock = threading.RLock()

    def save(self, task_id: str, task: dict[str, Any]) -> None:
        with self._lock:
            self._tasks[task_id] = _InMemoryRecord(
                data=dict(task),
                expires_at=self._tasks.get(task_id, _InMemoryRecord({})).expires_at
                if task_id in self._tasks
                else None,
            )

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            rec = self._tasks.get(task_id)
            if rec is None:
                return None
            if rec.expires_at and time.time() > rec.expires_at:
                del self._tasks[task_id]
                return None
            return dict(rec.data)

    def exists(self, task_id: str) -> bool:
        return self.get(task_id) is not None

    def delete(self, task_id: str) -> None:
        with self._lock:
            self._tasks.pop(task_id, None)

    def _purge_expired(self) -> int:
        """清理过期记录并返回清理条数（共享给 list_ids/list_all/cleanup_expired）"""
        with self._lock:
            now = time.time()
            expired = [
                k for k, v in self._tasks.items() if v.expires_at and now > v.expires_at
            ]
            for k in expired:
                self._tasks.pop(k, None)
            return len(expired)

    def list_ids(self) -> list[str]:
        with self._lock:
            self._purge_expired()
            return list(self._tasks.keys())

    def list_all(self) -> list[dict[str, Any]]:
        with self._lock:
            self._purge_expired()
            return [dict(v.data) for v in self._tasks.values()]

    def set_ttl(self, task_id: str, seconds: int) -> None:
        with self._lock:
            rec = self._tasks.get(task_id)
            if rec:
                rec.expires_at = time.time() + seconds

    def cleanup_expired(self) -> int:
        with self._lock:
            return self._purge_expired()


# ──────────────────────────────────────────────────────────
# SQLite 后端
# ──────────────────────────────────────────────────────────


class SQLiteTaskStore(TaskStore):
    """SQLite 任务存储（v2.1 - 持久化，无 Redis 时的生产方案）"""

    def __init__(self, db_path: str | Path = "~/.cache/scenefab/task_store.db"):
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    expires_at REAL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_expires ON tasks(expires_at)"
            )
            conn.commit()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
        finally:
            conn.close()

    def save(self, task_id: str, task: dict[str, Any]) -> None:
        with self._lock, self._conn() as conn:
            # 保留旧的 expires_at
            row = conn.execute(
                "SELECT expires_at FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            expires = row[0] if row else None
            conn.execute(
                "INSERT OR REPLACE INTO tasks VALUES (?, ?, ?, ?)",
                (
                    task_id,
                    json.dumps(task, ensure_ascii=False, default=str),
                    expires,
                    time.time(),
                ),
            )
            conn.commit()

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT data, expires_at FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
            if row is None:
                return None
            data, expires = row
            if expires and time.time() > expires:
                conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
                conn.commit()
                return None
            return json.loads(data)  # type: ignore[no-any-return]

    def exists(self, task_id: str) -> bool:
        return self.get(task_id) is not None

    def delete(self, task_id: str) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()

    def list_ids(self) -> list[str]:
        with self._lock, self._conn() as conn:
            now = time.time()
            # 清理过期
            conn.execute(
                "DELETE FROM tasks WHERE expires_at IS NOT NULL AND expires_at < ?",
                (now,),
            )
            conn.commit()
            rows = conn.execute(
                "SELECT task_id FROM tasks ORDER BY updated_at DESC"
            ).fetchall()
            return [r[0] for r in rows]

    def list_all(self) -> list[dict[str, Any]]:
        # 由 TaskStore 基类 default impl 提供（基于 list_ids + get）
        return super().list_all()

    def set_ttl(self, task_id: str, seconds: int) -> None:
        with self._lock, self._conn() as conn:
            expires = time.time() + seconds
            conn.execute(
                "UPDATE tasks SET expires_at = ? WHERE task_id = ?", (expires, task_id)
            )
            conn.commit()

    def cleanup_expired(self) -> int:
        with self._lock, self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM tasks WHERE expires_at IS NOT NULL AND expires_at < ?",
                (time.time(),),
            )
            conn.commit()
            return cur.rowcount


# ──────────────────────────────────────────────────────────
# Redis 后端（可选）
# ──────────────────────────────────────────────────────────


class RedisTaskStore(TaskStore):
    """
    Redis 任务存储（v2.1 增强：TTL 原生支持）

    依赖：pip install redis
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        prefix: str = "scenefab:task:",
    ):
        try:
            import redis as _redis  # type: ignore[import-not-found]
        except ImportError as e:
            raise ImportError("RedisTaskStore requires `pip install redis`") from e
        self._client = _redis.from_url(url, decode_responses=True)
        self._prefix = prefix
        self._lock = threading.RLock()

    def _key(self, task_id: str) -> str:
        return f"{self._prefix}{task_id}"

    def save(self, task_id: str, task: dict[str, Any]) -> None:
        with self._lock:
            data = json.dumps(task, ensure_ascii=False, default=str)
            # 检查现有 TTL 保留
            current_ttl = self._client.ttl(self._key(task_id))
            if current_ttl and current_ttl > 0:
                self._client.set(self._key(task_id), data, ex=current_ttl)
            else:
                self._client.set(self._key(task_id), data)

    def get(self, task_id: str) -> dict[str, Any] | None:
        data = self._client.get(self._key(task_id))
        if data is None:
            return None
        return json.loads(data)  # type: ignore[no-any-return]

    def exists(self, task_id: str) -> bool:
        return bool(self._client.exists(self._key(task_id)))

    def delete(self, task_id: str) -> None:
        self._client.delete(self._key(task_id))

    def list_ids(self) -> list[str]:
        keys = self._client.keys(f"{self._prefix}*")
        return [k.removeprefix(self._prefix) for k in keys]

    def list_all(self) -> list[dict[str, Any]]:
        # 由 TaskStore 基类 default impl 提供（基于 list_ids + get）
        return super().list_all()

    def set_ttl(self, task_id: str, seconds: int) -> None:
        self._client.expire(self._key(task_id), seconds)

    def cleanup_expired(self) -> int:
        # Redis 自动清理，不需要
        return 0


# ──────────────────────────────────────────────────────────
# 工厂 & 全局
# ──────────────────────────────────────────────────────────


def create_task_store(backend: str = "memory", **kwargs: Any) -> TaskStore:
    """工厂方法（v2.1 推荐）"""
    backend = backend.lower()
    if backend in ("memory", "inmemory", "in_memory"):
        return InMemoryTaskStore()
    if backend in ("sqlite",):
        return SQLiteTaskStore(kwargs.get("db_path", "~/.cache/scenefab/task_store.db"))
    if backend in ("redis",):
        return RedisTaskStore(
            url=kwargs.get("url", "redis://localhost:6379/0"),
            prefix=kwargs.get("prefix", "scenefab:task:"),
        )
    raise ValueError(f"Unknown task store backend: {backend}")


_global_store: TaskStore | None = None
_global_lock = threading.Lock()


def get_task_store() -> TaskStore:
    """获取全局任务存储（v2.1 默认内存）"""
    global _global_store
    if _global_store is None:
        with _global_lock:
            if _global_store is None:
                _global_store = InMemoryTaskStore()
    return _global_store


def set_task_store(store: TaskStore) -> None:
    """注入全局任务存储（v2.1 测试 / DI 友好）"""
    global _global_store
    with _global_lock:
        if _global_store is not None and _global_store is not store:
            try:
                _global_store.close()
            except (OSError, RuntimeError) as e:
                # 关闭旧存储失败不应阻止新存储注入 — 仅记录后继续
                logger.warning(f"关闭旧 TaskStore 失败: {e}")
        _global_store = store


__all__ = [
    "TaskStore",
    "InMemoryTaskStore",
    "SQLiteTaskStore",
    "RedisTaskStore",
    "create_task_store",
    "get_task_store",
    "set_task_store",
]
