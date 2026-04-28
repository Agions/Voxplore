#!/usr/bin/env python3
# -*- coding: utf-8 -*-



"""
统一配置管理
集中管理所有配置项
"""

import os
import json
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict
import logging
import threading
logger = logging.getLogger(__name__)
@dataclass
class AppConfig:
    """应用配置"""
    # 应用信息
    name: str = "Voxplore"
    version: str = "3.0.0"
    debug: bool = False

    # 路径配置
    project_dir: str = "./projects"
    cache_dir: str = "./cache"
    log_dir: str = "./logs"
    temp_dir: str = "./temp"

    # AI 配置
    default_provider: str = "openai"
    default_model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096

    # 导出配置
    default_format: str = "mp4"
    default_quality: str = "high"
    output_dir: str = "./output"

    # UI 配置
    theme: str = "dark"
    language: str = "zh-CN"
    animation_enabled: bool = True

    # 性能配置
    max_workers: int = 4
    cache_size: int = 200
    cache_ttl: int = 1800

    # 高级配置
    auto_save: bool = True
    auto_save_interval: int = 300
    backup_enabled: bool = True
    max_backups: int = 10


@dataclass
class APIKeys:
    """API 密钥配置"""
    openai: str = ""
    anthropic: str = ""
    google: str = ""
    deepseek: str = ""
    kimi: str = ""
    qwen: str = ""
    glm: str = ""
    doubao: str = ""
    hunyuan: str = ""
    local: str = ""

    # TTS
    edge_tts: str = ""
    azure_tts: str = ""
    volcengine_tts: str = ""
    tencent_tts: str = ""


class ConfigManager:
    """
    配置管理器

    统一管理应用配置和 API 密钥
    """

    def __init__(self, config_dir: str = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".narrafiilm"

        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._config: Optional[AppConfig] = None
        self._api_keys: Optional[APIKeys] = None

    @property
    def config(self) -> AppConfig:
        """获取应用配置"""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    @property
    def api_keys(self) -> APIKeys:
        """获取 API 密钥"""
        if self._api_keys is None:
            self._api_keys = self._load_api_keys()
        return self._api_keys

    def _get_config_path(self) -> Path:
        """获取配置文件路径"""
        return self.config_dir / "config.json"

    def _get_keys_path(self) -> Path:
        """获取密钥文件路径"""
        return self.config_dir / "keys.json"

    def _load_config(self) -> AppConfig:
        """加载配置"""
        path = self._get_config_path()

        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return AppConfig(**data)
            except (json.JSONDecodeError, TypeError, OSError) as e:
                logger.warning(f"Config file load failed: {e}")

        return AppConfig()

    def _load_api_keys(self) -> APIKeys:
        """加载 API 密钥"""
        path = self._get_keys_path()

        # 优先从环境变量加载
        keys = APIKeys()

        env_mappings = {
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'google': 'GOOGLE_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'kimi': 'KIMI_API_KEY',
            'qwen': 'QWEN_API_KEY',
            'glm': 'GLM_API_KEY',
            'doubao': 'DOUBAO_API_KEY',
            'hunyuan': 'HUNYUAN_API_KEY',
        }

        for attr, env_var in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                setattr(keys, attr, value)

        # 从文件加载（环境变量优先）
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for key, value in data.items():
                    if not getattr(keys, key, ""):  # 环境变量已设置的值不覆盖
                        setattr(keys, key, value)
            except (json.JSONDecodeError, TypeError, OSError) as e:
                logger.warning(f"API keys file load failed: {e}")

        return keys

    def save_config(self):
        """保存配置"""
        path = self._get_config_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.config), f, indent=2, ensure_ascii=False)

    def save_api_keys(self):
        """保存 API 密钥"""
        path = self._get_keys_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.api_keys), f, indent=2, ensure_ascii=False)

    def update(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self.save_config()

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return getattr(self.config, key, default)

    def set_key(self, name: str, value: str):
        """设置 API 密钥"""
        if hasattr(self.api_keys, name):
            setattr(self.api_keys, name, value)
            self.save_api_keys()

    def get_key(self, name: str) -> str:
        """获取 API 密钥"""
        return getattr(self.api_keys, name, "")

    def reset(self):
        """重置为默认配置"""
        self._config = AppConfig()
        self.save_config()


# 全局配置管理器
_config_manager: Optional[ConfigManager] = None
_config_lock = threading.Lock()


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器"""
    global _config_manager
    if _config_manager is None:
        with _config_lock:
            if _config_manager is None:
                _config_manager = ConfigManager()
    return _config_manager


# 便捷访问
config = get_config_manager().config
api_keys = get_config_manager().api_keys
