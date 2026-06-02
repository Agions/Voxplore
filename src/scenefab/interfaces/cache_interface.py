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
from typing import Any, Optional


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
    expires_at: datetime | None = None
    access_count: int = 0
    last_accessed: datetime | None = None
    size_bytes: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

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
    policy: CachePolicy = CachePolicy.LRU


class ICache(ABC):
    """缓存接口"""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None,
            metadata: dict[str, Any] | None = None) -> bool:
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


# =============================================================================
# 缓存使用指南
# =============================================================================
# SceneFab 项目中存在多套缓存实现，它们服务于不同的场景：
#
# +-----------------------------+---------------------------+------------------------+
# | 缓存类                      | 位置                     | 适用场景              |
# +-----------------------------+---------------------------+------------------------+
# | VideoFrameCache             | scenefab/video.py        | 视频关键帧 LRU 缓存    |
# |                            |                           | 内存限制 + 磁盘回退    |
# +-----------------------------+---------------------------+------------------------+
# | LRUCache                    | scenefab/ai_services.py  | AI 视觉分析结果缓存    |
# | PersistentCache            |                          | 简单 KV 缓存，无 TTL  |
# +-----------------------------+---------------------------+------------------------+
# | RequestCache               | scenefab/services/ai/    | LLM 请求级缓存        |
# |                            | base_llm_provider.py     | async + TTL 支持      |
# +-----------------------------+---------------------------+------------------------+
# | LLMMemoryCache/LLMDiskCache | scenefab/services/ai/   | AI 服务监控指标封装    |
# |                            | cache.py                  | 附带统计信息          |
# +-----------------------------+---------------------------+------------------------+
# | MemoryCache/DiskCache      | scenefab/cache_impl/     | ICache 接口标准实现    |
# | CacheManager               | scenefab/cache_manager.py | 统一管理（内存+磁盘） |
# +-----------------------------+---------------------------+------------------------+
#
# 设计决策说明：
# - VideoFrameCache 使用 numpy 数组，需要特殊内存估算，无法与其他缓存合并
# - RequestCache 使用 async/await 语义，与同步缓存在使用方式上不兼容
# - 各缓存的 TTL、容量、淘汰策略差异大，强行统一会增加不必要的复杂度
# - ICache 接口和 CacheManager 已设计好，新缓存类可选择实现 ICache 以获得统一管理
#
# 新增缓存建议：
# - 如果需要 TTL + async 支持 → 参考 RequestCache
# - 如果需要 LRU + 内存限制 → 参考 VideoFrameCache
# - 如果需要磁盘持久化 → 参考 CacheManager + DiskCache
# - 如果只需要简单 KV 缓存 → 直接用 dict 或参考 LRUCache
# =============================================================================
