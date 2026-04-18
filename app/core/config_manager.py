#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 配置管理器
提供统一的配置管理接口
"""

import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum

from app.core.exceptions import ConfigError


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
    """缓存配置"""
    enabled: bool = True
    max_size: int = 100
    ttl: int = 3600  # 秒

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


@dataclass
class AppConfig:
    """应用配置"""
    llm_providers: Dict[str, LLMConfig] = field(default_factory=lambda: {
        "qwen": LLMConfig(enabled=False, model="qwen-plus"),
        "kimi": LLMConfig(enabled=False, model="moonshot-v1-8k"),
        "glm5": LLMConfig(enabled=False, model="glm-5"),
        "openai": LLMConfig(enabled=False, model="gpt-4"),
    })
    cache: CacheConfig = field(default_factory=CacheConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    default_provider: str = "qwen"
    log_level: str = "INFO"

    def __post_init__(self):
        """初始化后验证"""
        if self.default_provider not in self.llm_providers:
            self.default_provider = list(self.llm_providers.keys())[0]


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化配置管理器

        Args:
            config_dir: 配置文件目录
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent / "config"

        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "app_config.yaml"
        self.llm_config_file = self.config_dir / "llm.yaml"
        self._config: Optional[AppConfig] = None
        self._extra: Dict[str, Any] = {}  # 扩展配置存储

    def get(self, key: str, default: Any = None) -> Any:
        """
        通用配置读取（支持点号路径）

        Args:
            key: 配置键，如 "editor.recent_files"
            default: 默认值
        """
        # 先查扩展存储
        if key in self._extra:
            return self._extra[key]

        # 再查 AppConfig 属性
        config = self.load_config()
        parts = key.split(".")
        obj = config
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return default
        return obj

    def set(self, key: str, value: Any) -> None:
        """设置扩展配置"""
        self._extra[key] = value
        # Persist to disk immediately so settings survive app restarts
        self.save_config()

    def get_value(self, key: str, default: Any = None) -> Any:
        """get 的别名，兼容旧代码"""
        return self.get(key, default)

    def set_value(self, key: str, value: Any) -> None:
        """set 的别名，兼容旧代码"""
        self.set(key, value)

    def load_config(self) -> AppConfig:
        """加载配置"""
        if self._config is not None:
            return self._config

        # 加载 YAML 文件
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                self._config = self._parse_config(data)
            except Exception as e:
                raise ConfigError(f"配置文件加载失败: {e}")
        else:
            # 创建默认配置
            self._config = AppConfig()
            self.save_config()

        return self._config

    def _parse_config(self, data: Dict[str, Any]) -> AppConfig:
        """解析配置数据"""
        config = AppConfig()

        # 解析 LLM 提供商配置
        if "llm_providers" in data:
            for provider_name, provider_data in data["llm_providers"].items():
                if provider_name in config.llm_providers:
                    llm_config = LLMConfig(**provider_data)
                    config.llm_providers[provider_name] = llm_config

        # 解析缓存配置
        if "cache" in data:
            config.cache = CacheConfig(**data["cache"])

        # 解析重试配置
        if "retry" in data:
            config.retry = RetryConfig(**data["retry"])

        # 解析其他配置
        if "default_provider" in data:
            config.default_provider = data["default_provider"]

        if "log_level" in data:
            config.log_level = data["log_level"]

        # Restore extra settings (project_dir, jianying_draft_dir, etc.) from saved data
        AppConfig_fields = {'llm_providers', 'cache', 'retry', 'default_provider', 'log_level'}
        for key, value in data.items():
            if key not in AppConfig_fields:
                self._extra[key] = value

        return config

    def save_config(self, config: Optional[AppConfig] = None) -> None:
        """
        保存配置

        Args:
            config: 配置对象，如果为 None 则保存当前配置
        """
        if config is None:
            config = self.load_config()

        try:
            # 转换为字典
            data = asdict(config)

            # Merge extra settings (project_dir, jianying_draft_dir, etc.) into saved data
            data.update(self._extra)

            # 保存到文件
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        except Exception as e:
            raise ConfigError(f"配置文件保存失败: {e}")

    def get_llm_config(self, provider: str) -> Optional[LLMConfig]:
        """获取 LLM 提供商配置"""
        config = self.load_config()
        return config.llm_providers.get(provider)

    def set_llm_config(self, provider: str, llm_config: LLMConfig) -> None:
        """设置 LLM 提供商配置"""
        config = self.load_config()
        config.llm_providers[provider] = llm_config
        self.save_config(config)

    def get_cache_config(self) -> CacheConfig:
        """获取缓存配置"""
        config = self.load_config()
        return config.cache

    def set_cache_config(self, cache_config: CacheConfig) -> None:
        """设置缓存配置"""
        config = self.load_config()
        config.cache = cache_config
        self.save_config(config)

    def get_retry_config(self) -> RetryConfig:
        """获取重试配置"""
        config = self.load_config()
        return config.retry

    def set_retry_config(self, retry_config: RetryConfig) -> None:
        """设置重试配置"""
        config = self.load_config()
        config.retry = retry_config
        self.save_config(config)

    def set_default_provider(self, provider: str) -> None:
        """设置默认提供商"""
        config = self.load_config()
        if provider in config.llm_providers:
            config.default_provider = provider
            self.save_config(config)
        else:
            raise ConfigError(f"未知的提供商: {provider}")

    def reset_config(self) -> None:
        """重置为默认配置"""
        self._config = AppConfig()
        self.save_config()

    def export_config(self) -> Dict[str, Any]:
        """导出配置为字典"""
        config = self.load_config()
        return asdict(config)

    def import_config(self, data: Dict[str, Any]) -> None:
        """从字典导入配置"""
        try:
            config = self._parse_config(data)
            self._config = config
            self.save_config(config)
        except Exception as e:
            raise ConfigError(f"配置导入失败: {e}")


# 全局配置管理器实例
_global_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager


def get_config() -> AppConfig:
    """快捷方法：获取应用配置"""
    return get_config_manager().load_config()
