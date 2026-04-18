#!/usr/bin/env python3
"""Test LLM Cache and Retry Policy"""

import pytest
import time

from app.services.ai.cache import (
    LLMMemoryCache,
    LLMRetryPolicy,
    with_retry,
    LLMPerformanceMonitor,
    get_global_cache,
    get_global_monitor,
)


class TestLLMMemoryCache:
    """Test LLM memory cache"""

    def test_init(self):
        """Test initialization"""
        cache = LLMMemoryCache(max_size=50, ttl=600)
        
        assert cache.max_size == 50
        assert cache.ttl == 600
        assert len(cache.cache) == 0

    def test_set_and_get(self):
        """Test basic set and get"""
        cache = LLMMemoryCache()
        messages = [{"role": "user", "content": "hello"}]
        
        cache.set(messages, "gpt-4", "Hello! How can I help?")
        result = cache.get(messages, "gpt-4")
        
        assert result == "Hello! How can I help?"

    def test_get_nonexistent(self):
        """Test get nonexistent key"""
        cache = LLMMemoryCache()
        
        result = cache.get([{"role": "user", "content": "hello"}], "gpt-4")
        
        assert result is None

    def test_different_models(self):
        """Test different models have separate caches"""
        cache = LLMMemoryCache()
        messages = [{"role": "user", "content": "hello"}]
        
        cache.set(messages, "gpt-4", "GPT-4 response")
        cache.set(messages, "claude", "Claude response")
        
        assert cache.get(messages, "gpt-4") == "GPT-4 response"
        assert cache.get(messages, "claude") == "Claude response"

    def test_max_size_eviction(self):
        """Test LRU eviction when max size reached"""
        cache = LLMMemoryCache(max_size=2)
        
        cache.set([{"role": "user", "content": "msg1"}], "model", "response1")
        cache.set([{"role": "user", "content": "msg2"}], "model", "response2")
        cache.set([{"role": "user", "content": "msg3"}], "model", "response3")
        
        # First message should be evicted
        assert cache.get([{"role": "user", "content": "msg1"}], "model") is None
        assert cache.get([{"role": "user", "content": "msg2"}], "model") == "response2"
        assert cache.get([{"role": "user", "content": "msg3"}], "model") == "response3"

    def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = LLMMemoryCache(ttl=1)  # 1 second TTL
        
        cache.set([{"role": "user", "content": "hello"}], "model", "response")
        
        # Should be available immediately
        assert cache.get([{"role": "user", "content": "hello"}], "model") == "response"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get([{"role": "user", "content": "hello"}], "model") is None

    def test_clear(self):
        """Test clear cache"""
        cache = LLMMemoryCache()
        
        cache.set([{"role": "user", "content": "hello"}], "model", "response")
        cache.clear()
        
        assert len(cache.cache) == 0
        assert cache.get([{"role": "user", "content": "hello"}], "model") is None

    def test_get_stats(self):
        """Test get stats"""
        cache = LLMMemoryCache(max_size=100, ttl=3600)
        
        cache.set([{"role": "user", "content": "hello"}], "model", "response")
        stats = cache.get_stats()
        
        assert stats["size"] == 1
        assert stats["max_size"] == 100
        assert stats["ttl"] == 3600


class TestLLMRetryPolicy:
    """Test LLM retry policy"""

    def test_init(self):
        """Test initialization"""
        policy = LLMRetryPolicy()
        
        assert policy.max_retries == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.backoff_factor == 2.0

    def test_custom_init(self):
        """Test custom initialization"""
        policy = LLMRetryPolicy(max_retries=5, base_delay=2.0, max_delay=120.0, backoff_factor=3.0)
        
        assert policy.max_retries == 5
        assert policy.base_delay == 2.0
        assert policy.max_delay == 120.0
        assert policy.backoff_factor == 3.0

    def test_exponential_backoff(self):
        """Test exponential backoff calculation"""
        policy = LLMRetryPolicy(base_delay=1.0, backoff_factor=2.0, max_delay=100.0)
        
        # Attempt 0: 1.0 * 2^0 = 1.0
        assert policy.get_delay(0) == 1.0
        # Attempt 1: 1.0 * 2^1 = 2.0
        assert policy.get_delay(1) == 2.0
        # Attempt 2: 1.0 * 2^2 = 4.0
        assert policy.get_delay(2) == 4.0
        # Attempt 3: 1.0 * 2^3 = 8.0
        assert policy.get_delay(3) == 8.0

    def test_max_delay_cap(self):
        """Test max delay cap"""
        policy = LLMRetryPolicy(base_delay=10.0, max_delay=50.0, backoff_factor=2.0)
        
        # 10.0 * 2^3 = 80, but capped at 50
        assert policy.get_delay(3) == 50.0


class TestWithRetryDecorator:
    """Test retry decorator"""

    def test_success_first_try(self):
        """Test successful call on first try"""
        call_count = 0
        
        @with_retry()
        def succeed():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = succeed()
        assert result == "success"
        assert call_count == 1

    def test_retry_then_success(self):
        """Test retry on failure then success"""
        call_count = 0
        policy = LLMRetryPolicy(max_retries=3)
        
        @with_retry(policy=policy, exceptions=(ValueError,))
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary error")
            return "success"
        
        result = fail_twice()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self):
        """Test all retries exhausted"""
        call_count = 0
        policy = LLMRetryPolicy(max_retries=2)
        
        @with_retry(policy=policy, exceptions=(ValueError,))
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("permanent error")
        
        with pytest.raises(ValueError, match="permanent error"):
            always_fail()
        
        assert call_count == 3  # Initial + 2 retries


class TestLLMPerformanceMonitor:
    """Test LLM performance monitor"""

    def test_init(self):
        """Test initialization"""
        monitor = LLMPerformanceMonitor()
        
        assert monitor.metrics["total_requests"] == 0
        assert monitor.metrics["successful_requests"] == 0
        assert monitor.metrics["failed_requests"] == 0

    def test_record_successful_request(self):
        """Test record successful request"""
        monitor = LLMPerformanceMonitor()
        
        monitor.record_request(success=True, tokens=100, time_taken=1.5)
        
        assert monitor.metrics["total_requests"] == 1
        assert monitor.metrics["successful_requests"] == 1
        assert monitor.metrics["total_tokens"] == 100
        assert monitor.metrics["total_time"] == 1.5

    def test_record_failed_request(self):
        """Test record failed request"""
        monitor = LLMPerformanceMonitor()
        
        monitor.record_request(success=False)
        
        assert monitor.metrics["total_requests"] == 1
        assert monitor.metrics["failed_requests"] == 1

    def test_record_cache_hit(self):
        """Test record cache hit"""
        monitor = LLMPerformanceMonitor()
        
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_miss()
        
        assert monitor.metrics["cache_hits"] == 2
        assert monitor.metrics["cache_misses"] == 1

    def test_get_stats(self):
        """Test get stats with calculated metrics"""
        monitor = LLMPerformanceMonitor()
        
        monitor.record_request(success=True, tokens=100, time_taken=1.0)
        monitor.record_request(success=True, tokens=200, time_taken=2.0)
        monitor.record_request(success=False)
        monitor.record_cache_hit()
        monitor.record_cache_miss()
        
        stats = monitor.get_stats()
        
        assert stats["total_requests"] == 3
        assert stats["successful_requests"] == 2
        assert stats["failed_requests"] == 1
        assert stats["success_rate"] == 2/3
        assert stats["avg_response_time"] == 1.5
        assert stats["cache_hit_rate"] == 0.5

    def test_reset(self):
        """Test reset metrics"""
        monitor = LLMPerformanceMonitor()
        
        monitor.record_request(success=True, tokens=100)
        monitor.record_cache_hit()
        monitor.reset()
        
        assert monitor.metrics["total_requests"] == 0
        assert monitor.metrics["cache_hits"] == 0


class TestGlobalInstances:
    """Test global cache and monitor instances"""

    def test_get_global_cache(self):
        """Test global cache instance"""
        cache = get_global_cache()
        
        assert isinstance(cache, LLMMemoryCache)

    def test_get_global_monitor(self):
        """Test global monitor instance"""
        monitor = get_global_monitor()
        
        assert isinstance(monitor, LLMPerformanceMonitor)
