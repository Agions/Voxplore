"""
AI 服务基础设施
包含限流器、断路器、LRU缓存、持久化缓存等公共组件
"""

import hashlib
import logging
import os
import threading
import time
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    改进版限流器 - 使用信号量避免空转
    """

    def __init__(self, rate: float = 10.0, burst: int = 20):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_update = time.time()
        self.lock = threading.Lock()
        self.semaphore = threading.Semaphore(0)
        self._thread = None
        self._running = False

    def start(self):
        """启动后台补充线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._replenisher, daemon=True)
        self._thread.start()

    def _replenisher(self):
        """后台令牌补充线程"""
        while self._running:
            with self.lock:
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
                self.last_update = now

                # 释放信号量
                while self.semaphore._value < self.burst and self.tokens >= 1.0:
                    self.semaphore.release()
                    self.tokens -= 1.0

            time.sleep(0.05)  # 50ms 刷新间隔

    def acquire(self, timeout: float = 30.0) -> bool:
        """获取令牌（阻塞）"""
        if not self._running:
            self.start()

        # 先快速检查
        with self.lock:
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True

        # 等待信号量
        return self.semaphore.acquire(timeout=timeout)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)  # type: ignore[unreachable]


class CircuitBreaker:
    """断路器"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"
        self.lock = threading.Lock()

    def can_execute(self) -> bool:
        with self.lock:
            if self.state == "closed":
                return True

            if self.state == "open":
                if (
                    self.last_failure_time
                    and time.time() - self.last_failure_time >= self.recovery_timeout
                ):
                    self.state = "half_open"
                    return True
                return False

            return True  # half_open

    def record_success(self):
        with self.lock:
            self.failure_count = 0
            self.state = "closed"

    def record_failure(self):
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"


class LRUCache:
    """LRU 缓存"""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
        return None

    def set(self, key: str, value: Any):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.max_size:
                    self.cache.popitem(last=False)
                self.cache[key] = value

    def clear(self):
        with self.lock:
            self.cache.clear()


class PersistentCache:
    """持久化缓存（orjson 加速）"""

    def __init__(self, cache_dir: str = "~/.cache/scenefab"):
        self.cache_dir = os.path.expanduser(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        # orjson 性能比标准 json 快 5-10 倍
        try:
            import orjson

            self._json = orjson
            self._use_orjson = True
        except ImportError:
            import json

            self._json = json
            self._use_orjson = False

    def _get_path(self, key: str) -> str:
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_key}.json")

    def get(self, key: str) -> Any | None:
        path = self._get_path(key)
        if os.path.exists(path):
            try:
                with open(path, "rb" if self._use_orjson else "r") as f:
                    if self._use_orjson:
                        data = self._json.loads(f.read())
                    else:
                        data = self._json.load(f)
                    if data.get("expires", float("inf")) < time.time():
                        os.remove(path)
                        return None
                    return data.get("value")
            except Exception:
                return None
        return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        path = self._get_path(key)
        try:
            cache_data = {"value": value, "expires": time.time() + ttl}
            if self._use_orjson:
                with open(path, "wb") as f:
                    f.write(self._json.dumps(cache_data))
            else:
                with open(path, "w") as f:
                    self._json.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")


__all__ = [
    "RateLimiter",
    "CircuitBreaker",
    "LRUCache",
    "PersistentCache",
]
