"""
任务存储抽象层

支持两种后端：
  - InMemoryTaskStore：进程内 dict（开发/无 Redis 环境）
  - RedisTaskStore：Redis 后端（生产环境，重启不丢任务）

使用方式：
    store = RedisTaskStore() if redis_available else InMemoryTaskStore()
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class TaskStore(ABC):
    """任务存储抽象接口"""

    @abstractmethod
    def save(self, task_id: str, task: Dict[str, Any]) -> None:
        """保存任务"""
        ...

    @abstractmethod
    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务"""
        ...

    @abstractmethod
    def exists(self, task_id: str) -> bool:
        """检查任务是否存在"""
        ...

    @abstractmethod
    def delete(self, task_id: str) -> None:
        """删除任务"""
        ...

    @abstractmethod
    def list_ids(self) -> list[str]:
        """列出所有任务ID"""
        ...


class InMemoryTaskStore(TaskStore):
    """进程内内存任务存储（开发用）"""

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def save(self, task_id: str, task: Dict[str, Any]) -> None:
        self._tasks[task_id] = task

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)

    def exists(self, task_id: str) -> bool:
        return task_id in self._tasks

    def delete(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)

    def list_ids(self) -> list[str]:
        return list(self._tasks.keys())


# ─── Redis 后端（可选依赖）──────────────────────────────────


class RedisTaskStore(TaskStore):
    """
    Redis 任务存储（生产用）

    依赖：pip install redis
    """

    def __init__(self, url: str = "redis://localhost:6379/0", prefix: str = "scenefab:task:"):
        import redis
        self._client = redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        self._prefix = prefix
        self._ttl = 7 * 24 * 3600  # 7天过期

    def _key(self, task_id: str) -> str:
        return f"{self._prefix}{task_id}"

    def save(self, task_id: str, task: Dict[str, Any]) -> None:
        key = self._key(task_id)
        self._client.setex(key, self._ttl, json.dumps(task))

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        key = self._key(task_id)
        data = self._client.get(key)
        if data is None:
            return None
        return json.loads(data)

    def exists(self, task_id: str) -> bool:
        return bool(self._client.exists(self._key(task_id)))

    def delete(self, task_id: str) -> None:
        self._client.delete(self._key(task_id))

    def list_ids(self) -> list[str]:
        pattern = f"{self._prefix}*"
        keys = self._client.keys(pattern)
        prefix_len = len(self._prefix)
        return [k[prefix_len:] for k in keys]


def create_task_store(redis_url: Optional[str] = None) -> TaskStore:
    """
    工厂函数：根据环境创建合适的 TaskStore

    若 REDIS_URL 环境变量存在且可用，自动使用 RedisTaskStore
    """
    if redis_url is None:
        import os
        redis_url = os.getenv("REDIS_URL")

    if redis_url:
        try:
            return RedisTaskStore(url=redis_url)
        except Exception:
            pass

    return InMemoryTaskStore()


__all__ = [
    "TaskStore",
    "InMemoryTaskStore",
    "RedisTaskStore",
    "create_task_store",
]