#!/usr/bin/env python3
"""
SceneFab 配置管理器（兼容层 - 已废弃）
请直接导入 scenefab.settings
"""
import warnings
from enum import Enum
from dataclasses import dataclass
from typing import Optional

warnings.warn(
    "scenefab.config_manager is deprecated. "
    "Use scenefab.settings.ConfigManager or scenefab.settings.config_manager.",
    DeprecationWarning,
    stacklevel=2,
)

from scenefab.settings import (
    ConfigManager as ConfigManager,
    AppConfig,
    config_manager,
    get_config,
    get_llm_config,
)


class LLMProviderType(Enum):
    """LLM 提供商类型"""
    QWEN = "qwen"
    KIMI = "kimi"
    GLM5 = "glm5"
    OPENAI = "openai"


@dataclass
class LLMConfig:
    """LLM 配置（兼容旧接口）"""
    enabled: bool = False
    api_key: str = ""
    model: str = ""
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000

    def is_valid(self) -> bool:
        """检查配置是否有效"""
        if not self.enabled:
            return False
        if not self.api_key:
            return False
        if not self.model:
            return False
        return True


@dataclass
class CacheConfig:
    """缓存配置（兼容旧接口）"""
    enabled: bool = True
    max_size: int = 100
    ttl: int = 3600

    def is_valid(self) -> bool:
        """检查配置是否有效"""
        return self.enabled and self.max_size > 0 and self.ttl > 0


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0

    def is_valid(self) -> bool:
        """检查配置是否有效"""
        return (
            self.max_retries > 0 and
            self.base_delay > 0 and
            self.max_delay > 0 and
            self.backoff_factor > 0
        )


__all__ = [
    "ConfigManager",
    "AppConfig",
    "LLMConfig",
    "CacheConfig",
    "RetryConfig",
    "LLMProviderType",
    "config_manager",
    "get_config",
    "get_llm_config",
]