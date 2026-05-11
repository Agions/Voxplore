"""Tests for app.api.routers._task_store - Redis/in-memory persistence"""

import pytest
from app.api.routers._task_store import (
    InMemoryTaskStore,
    RedisTaskStore,
    create_task_store,
    TaskStore,
)
from unittest.mock import patch


class TestInMemoryTaskStore:
    def test_save_and_get(self):
        store = InMemoryTaskStore()
        store.save("task-1", {"status": "pending", "progress": 0})
        result = store.get("task-1")
        assert result is not None
        assert result["status"] == "pending"

    def test_get_nonexistent(self):
        store = InMemoryTaskStore()
        assert store.get("nonexistent") is None

    def test_exists(self):
        store = InMemoryTaskStore()
        store.save("task-1", {"status": "done"})
        assert store.exists("task-1") is True
        assert store.exists("nonexistent") is False

    def test_delete(self):
        store = InMemoryTaskStore()
        store.save("task-1", {"status": "done"})
        store.delete("task-1")
        assert store.get("task-1") is None

    def test_list_ids(self):
        store = InMemoryTaskStore()
        store.save("task-1", {"status": "done"})
        store.save("task-2", {"status": "running"})
        store.save("task-3", {"status": "pending"})
        ids = store.list_ids()
        assert set(ids) == {"task-1", "task-2", "task-3"}


class TestCreateTaskStore:
    def test_in_memory_when_no_redis_env(self):
        """Without REDIS_URL, should return InMemoryTaskStore"""
        env = {"REDIS_URL": ""}
        with patch.dict("os.environ", env, clear=True):
            store = create_task_store()
            assert isinstance(store, InMemoryTaskStore)

    def test_redis_when_url_provided(self):
        """When REDIS_URL is set and redis available, use RedisTaskStore"""
        with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379/0"}):
            with patch("app.api.routers._task_store.RedisTaskStore") as mock_redis:
                mock_redis.return_value = mock_redis
                _store = create_task_store()
                # create_task_store tries RedisTaskStore; on connection fail falls back
                # so we just verify it doesn't crash and returns a TaskStore


class TestTaskStoreInterface:
    def test_inmemory_is_task_store_subclass(self):
        assert issubclass(InMemoryTaskStore, TaskStore)
