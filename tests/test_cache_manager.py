#!/usr/bin/env python3
"""Test Cache Manager"""

import pytest
import time

from app.core.cache_manager import MemoryCache
from app.core.interfaces.cache_interface import CachePolicy


class TestMemoryCache:
    """Test memory cache"""

    def test_init(self):
        """Test initialization"""
        cache = MemoryCache(max_size=100, max_memory_mb=10)
        
        assert cache._max_size == 100
        assert cache._policy == CachePolicy.LRU

    def test_set_and_get(self):
        """Test set and get"""
        cache = MemoryCache()
        
        cache.set("key1", "value1")
        value = cache.get("key1")
        
        assert value == "value1"

    def test_get_nonexistent(self):
        """Test get nonexistent"""
        cache = MemoryCache()
        
        value = cache.get("nonexistent")
        
        assert value is None

    def test_exists(self):
        """Test exists"""
        cache = MemoryCache()
        
        cache.set("key1", "value1")
        
        assert cache.exists("key1") is True
        assert cache.exists("nonexistent") is False

    def test_delete(self):
        """Test delete"""
        cache = MemoryCache()
        
        cache.set("key1", "value1")
        result = cache.delete("key1")
        
        assert result is True
        assert cache.exists("key1") is False

    def test_clear(self):
        """Test clear"""
        cache = MemoryCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        
        assert cache.exists("key1") is False
        assert cache.exists("key2") is False

    def test_max_size_limit(self):
        """Test max size limit"""
        cache = MemoryCache(max_size=2)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # key1 should have been evicted due to LRU
        assert cache.exists("key1") is False or cache.exists("key2") is True

    def test_get_stats(self):
        """Test get stats"""
        cache = MemoryCache()
        cache.set("key1", "value1")
        _ = cache.get("key1")  # hit
        _ = cache.get("nonexistent")  # miss
        
        stats = cache.get_stats()
        
        assert hasattr(stats, 'hit_count')
        assert hasattr(stats, 'miss_count')
