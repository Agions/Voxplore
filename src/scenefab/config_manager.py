"""
配置管理器（兼容层）

已迁移至 scenefab.settings
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional

from scenefab.settings import (
    ConfigManager,
    AppConfig,
    config_manager,
    get_config,
    get_llm_config,
)
from scenefab.settings import LLMConfig as _LLMConfig, CacheConfig as _CacheConfig


class LLMProviderType(Enum):
    """LLM 提供商类型"""
    QWEN = "qwen"
    KIMI = "kimi"
    GLM5 = "glm5"
    OPENAI = "openai"


@dataclass
class LLMConfig:
    """LLM 配置"""
    enabled: bool = False
    api_key: str = ""
    model: str = ""
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000

    def is_valid(self) -> bool:
        return self.enabled and bool(self.api_key) and bool(self.model)


@dataclass
class CacheConfig:
    """缓存配置"""
    enabled: bool = True
    max_size: int = 100
    ttl: int = 3600

    def is_valid(self) -> bool:
        return self.enabled and self.max_size > 0 and self.ttl > 0


__all__ = [
    "ConfigManager",
    "AppConfig",
    "config_manager",
    "get_config",
    "get_llm_config",
    "LLMProviderType",
    "LLMConfig",
    "CacheConfig",
]