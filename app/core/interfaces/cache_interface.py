"""
缓存接口定义
定义缓存的统一接口和数据结构
"""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict


class CachePolicy(Enum):
    """缓存策略"""
    LRU = "lru"    # 最近最少使用
    LFU = "lfu"    # 最不经常使用
    FIFO = "fifo"  # 先进先出


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


@dataclass
class CacheStats:
    """缓存统计"""
    total_entries: int = 0
    total_size_bytes: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    hit_rate: float = 0.0
    avg_entry_size: float = 0.0
    max_size_bytes: int = 0
    policy: str = CachePolicy.LRU


class ICache(ABC):
    """缓存接口"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None,
            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """设置缓存值"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存"""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """清空缓存"""
        pass
    
    @abstractmethod
    def get_stats(self) -> CacheStats:
        """获取缓存统计"""
        pass


def generate_cache_key(func_name: str, *args, **kwargs) -> str:
    """
    生成缓存键
    """
    key_data = {
        'func': func_name,
        'args': str(args),
        'kwargs': str(sorted(kwargs.items()))
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()
