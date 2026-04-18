# Core interfaces
from .cache_interface import (
    ICache,
    CacheEntry,
    CacheStats,
    CachePolicy,
    generate_cache_key,
)

__all__ = [
    'ICache',
    'CacheEntry',
    'CacheStats',
    'CachePolicy',
    'generate_cache_key',
]
