"""
AI 服务基础设施 — 缓存组件

提供 LRU 内存缓存和持久化磁盘缓存。
"""

import hashlib
import logging
import os
import threading
import time
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)


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
        try:
            import orjson

            self._json = orjson
            self._use_orjson = True
        except ImportError:
            import json

            self._json = json  # type: ignore[misc]
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
                        data = self._json.load(f)  # type: ignore[attr-defined]
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
                    self._json.dump(cache_data, f)  # type: ignore[attr-defined]
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")


__all__ = [
    "LRUCache",
    "PersistentCache",
]
