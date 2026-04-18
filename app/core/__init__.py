"""
Voxplore 核心模块

核心功能：
- application: 应用入口和管理 (需要 Qt)
- config_manager: 配置管理
- cache_manager: 缓存管理
- event_bus: 事件总线
- exceptions: 异常定义
- logger: 日志
- project_manager: 项目管理
- service_registry: 服务注册表
- secure_key_manager: 密钥管理
"""

# 注意：Application 需要 Qt 环境，单独导入
# from app.core import Application

from .config_manager import ConfigManager, AppConfig
from .cache_manager import CacheManager, MemoryCache, DiskCache
from .event_bus import EventBus
from .exceptions import (
    VoxploreError,
    LLMError,
    ConfigError,
    FileError,
    VideoError,
    TTSError,
    NetworkError,
    ErrorCode,
)
from .logger import setup_logging, get_logger
from .project_manager import ProjectManager
from .service_registry import ServiceRegistry
from .service_container import ServiceContainer
from .secure_key_manager import SecureKeyManager

__all__ = [
    # Config
    "ConfigManager",
    "AppConfig",

    # Cache
    "CacheManager",
    "MemoryCache",
    "DiskCache",

    # Event
    "EventBus",

    # Exceptions
    "VoxploreError",
    "LLMError",
    "ConfigError",
    "FileError",
    "VideoError",
    "TTSError",
    "NetworkError",
    "ErrorCode",

    # Logger
    "setup_logging",
    "get_logger",


    # Project
    "ProjectManager",

    # Service
    "ServiceRegistry",
    "ServiceContainer",

    # Security
    "SecureKeyManager",
]
