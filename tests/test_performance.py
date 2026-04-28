#!/usr/bin/env python3
"""Test performance utilities"""

import time
from app.utils.performance import LazyLoader, MemoryCache, cached, timed


class TestLazyLoader:
    """Test LazyLoader"""

    def test_get_returns_instance(self):
        load_count = [0]

        def loader():
            load_count[0] += 1
            return {"loaded": True}

        loader_obj = LazyLoader(loader)
        result = loader_obj.get()
        assert result == {"loaded": True}
        assert load_count[0] == 1

    def test_get_caches_instance(self):
        load_count = [0]

        def loader():
            load_count[0] += 1
            return object()

        loader_obj = LazyLoader(loader)
        obj1 = loader_obj.get()
        obj2 = loader_obj.get()
        obj3 = loader_obj.get()
        assert obj1 is obj2 is obj3
        assert load_count[0] == 1

    def test_reset_clears_cache(self):
        load_count = [0]

        def loader():
            load_count[0] += 1
            return load_count[0]

        loader_obj = LazyLoader(loader)
        assert loader_obj.get() == 1
        assert loader_obj.get() == 1
        loader_obj.reset()
        assert loader_obj.get() == 2


class TestMemoryCache:
    """Test MemoryCache"""

    def test_get_set_basic(self):
        cache = MemoryCache(max_size=10, ttl=3600)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_returns_none(self):
        cache = MemoryCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        cache = MemoryCache(ttl=1)
        cache.set("key", "value")
        assert cache.get("key") == "value"
        time.sleep(1.1)
        assert cache.get("key") is None

    def test_max_size_eviction(self):
        cache = MemoryCache(max_size=3, ttl=3600)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)
        assert cache.get("a") is None
        assert cache.get("d") == 4

    def test_clear(self):
        cache = MemoryCache()
        cache.set("k1", 1)
        cache.set("k2", 2)
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_get_stats(self):
        cache = MemoryCache(max_size=10)
        cache.set("k1", 1)
        cache.set("k2", 2)
        cache.get("k1")
        cache.get("k1")
        stats = cache.get_stats()
        assert stats["size"] == 2
        assert stats["max_size"] == 10
        assert stats["total_hits"] == 2


class TestCachedDecorator:
    """Test @cached decorator"""

    def test_cached_avoids_recomputation(self):
        cache = MemoryCache()
        call_count = [0]

        @cached(cache)
        def expensive(x):
            call_count[0] += 1
            return x * 2

        assert expensive(5) == 10
        assert expensive(5) == 10
        assert expensive(5) == 10
        assert call_count[0] == 1

    def test_cached_different_args_different_cache(self):
        cache = MemoryCache()
        call_count = [0]

        @cached(cache)
        def add_one(x):
            call_count[0] += 1
            return x + 1

        assert add_one(1) == 2
        assert add_one(2) == 3
        assert add_one(1) == 2
        assert call_count[0] == 2

    def test_cached_with_key_fn(self):
        cache = MemoryCache()
        call_count = [0]

        @cached(cache, key_fn=lambda x: repr((type(x).__name__, x)))
        def double(x):
            call_count[0] += 1
            return x * 2

        assert double(5) == 10
        assert double("5") == "55"
        assert call_count[0] == 2


class TestTimed:
    """Test @timed decorator"""

    def test_timed_returns_result(self):
        @timed("test_timer")
        def do_work():
            return "done"

        result = do_work()
        assert result == "done"
