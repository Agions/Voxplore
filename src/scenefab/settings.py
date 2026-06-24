#!/usr/bin/env python3
"""
SceneFab 配置管理
统一管理系统配置、环境变量、参数设置
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

from scenefab.utils.singleton import SingletonMeta
from scenefab.utils.version import get_version_string

# 加载 .env 文件
load_dotenv()


@dataclass(slots=True)
class LLMConfig:
    """LLM 提供者配置"""

    name: str
    enabled: bool = False
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    max_tokens: int = 8000
    temperature: float = 0.7
    requests_per_second: float = 10.0
    burst_size: int = 20

    def is_valid(self) -> bool:
        """检查 LLM 配置是否完整可用"""
        return self.enabled and bool(self.api_key) and bool(self.model)


@dataclass(slots=True)
class TTSConfig:
    """TTS 配音配置"""

    provider: str = "edge"  # edge, f5, openai
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: float = 1.0
    pitch: float = 0.0
    volume: float = 1.0


@dataclass(slots=True)
class VideoConfig:
    """视频处理配置"""

    min_segment_duration: float = 9.0  # 最小片段时长（秒）
    max_segment_duration: float = 60.0  # 最大片段时长（秒）
    frame_sample_interval: float = 1.0  # 帧采样间隔（秒）
    min_confidence: float = 0.6  # 最低置信度
    visual_weight: float = 0.7  # 视觉权重（分组用）
    audio_weight: float = 0.3  # 音频权重（分组用）


@dataclass(slots=True)
class CacheConfig:
    """缓存配置"""

    enabled: bool = True
    max_size: int = 100
    ttl: int = 3600
    cache_dir: str = "~/.cache/scenefab"

    def is_valid(self) -> bool:
        """检查缓存配置是否有效"""
        return self.enabled and self.max_size > 0 and self.ttl > 0


@dataclass
class AppConfig:
    """应用配置"""

    name: str = "SceneFab"
    version: str = field(default_factory=get_version_string)
    debug: bool = False
    cache: CacheConfig = field(default_factory=CacheConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    llm_providers: dict[str, LLMConfig] = field(default_factory=dict)
    default_llm: str = "deepseek"


class ConfigManager(metaclass=SingletonMeta):
    """
    配置管理器
    负责加载、验证和管理所有配置
    """

    def __init__(self):
        self._config_file = Path(__file__).parent.parent / "config" / "app_config.yaml"
        self._config: AppConfig = AppConfig()
        self._load_config()

    @staticmethod
    def _substitute_env_vars(value: str) -> str:
        """替换字符串中的 ${ENV_VAR} 为环境变量值"""
        def _replace(match: re.Match) -> str:
            var_name = match.group(1)
            return os.getenv(var_name, "")
        return re.sub(r"\$\{(\w+)\}", _replace, value)

    def _load_config(self):
        """加载配置文件（LLM 配置统一从 llm.yaml 加载）"""
        config_data = {
            "name": "SceneFab",
            "version": get_version_string(),
            "debug": os.getenv("SCENEFAB_DEBUG", "false").lower() == "true",
            "cache": {
                "enabled": True,
                "max_size": 100,
                "ttl": 3600,
                "cache_dir": os.path.expanduser(
                    os.getenv("SCENEFAB_CACHE_DIR", "~/.cache/scenefab")
                ),
            },
            "video": {
                "min_segment_duration": 9.0,
                "max_segment_duration": 60.0,
                "frame_sample_interval": 1.0,
                "min_confidence": 0.6,
                "visual_weight": 0.7,
                "audio_weight": 0.3,
            },
            "tts": {
                "provider": "edge",
                "voice": "zh-CN-XiaoxiaoNeural",
                "rate": 1.0,
                "pitch": 0.0,
                "volume": 1.0,
            },
            "llm_providers": {},
            "default_llm": "deepseek",
        }

        # 从 app_config.yaml 加载非 LLM 配置（cache、video、tts 等）
        if self._config_file.exists():
            try:
                with open(self._config_file, encoding="utf-8") as f:
                    yaml_config = yaml.safe_load(f) or {}
                    # 移除已废弃的 llm_providers 段落（LLM 配置从 llm.yaml 加载）
                    yaml_config.pop("llm_providers", None)
                    yaml_config.pop("default_llm", None)
                    self._merge_config(config_data, yaml_config)
            except Exception as e:
                print(f"Warning: Failed to load config file: {e}")

        # LLM 配置统一从 llm.yaml 加载（单一数据源）
        llm_config_path = Path(__file__).parent.parent / "config" / "llm.yaml"
        if llm_config_path.exists():
            try:
                with open(llm_config_path, encoding="utf-8") as f:
                    llm_yaml = yaml.safe_load(f) or {}
                llm_section = llm_yaml.get("LLM", {})
                default_provider = llm_section.pop("default_provider", "deepseek")
                config_data["default_llm"] = default_provider

                for name, provider_data in llm_section.items():
                    if not isinstance(provider_data, dict):
                        continue
                    # 替换 ${ENV_VAR} 为环境变量值
                    api_key = provider_data.get("api_key", "")
                    if isinstance(api_key, str) and "${" in api_key:
                        api_key = self._substitute_env_vars(api_key)
                    config_data["llm_providers"][name] = {
                        "enabled": provider_data.get("enabled", False),
                        "api_key": api_key,
                        "base_url": provider_data.get("base_url", ""),
                        "model": provider_data.get("model", ""),
                        "max_tokens": provider_data.get("max_tokens", 8000),
                        "temperature": provider_data.get("temperature", 0.7),
                    }
            except Exception as e:
                print(f"Warning: Failed to load llm.yaml: {e}")

        self._config = self._parse_config(config_data)

    def _merge_config(self, base: dict, update: dict):
        """深度合并配置"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _parse_config(self, data: dict) -> AppConfig:
        """解析配置为 dataclass"""
        cache = CacheConfig(**data.get("cache", {}))
        video = VideoConfig(**data.get("video", {}))
        tts = TTSConfig(**data.get("tts", {}))

        llm_providers = {}
        for name, llm_data in data.get("llm_providers", {}).items():
            llm_providers[name] = LLMConfig(name=name, **llm_data)

        return AppConfig(
            name=data.get("name", "SceneFab"),
            version=data.get("version", "1.0.0"),
            debug=data.get("debug", False),
            cache=cache,
            video=video,
            tts=tts,
            llm_providers=llm_providers,
            default_llm=data.get("default_llm", "deepseek"),
        )

    @property
    def config(self) -> AppConfig:
        """获取应用配置"""
        return self._config

    def get_llm_config(self, provider: str | None = None) -> LLMConfig | None:
        """获取指定 LLM 配置"""
        if provider is None:
            provider = self._config.default_llm
        return self._config.llm_providers.get(provider)

    def get_enabled_llm(self) -> list[LLMConfig]:
        """获取所有启用的 LLM"""
        return [cfg for cfg in self._config.llm_providers.values() if cfg.enabled]

    def reload(self):
        """重新加载配置"""
        self._load_config()

    def save(self, config_file: str | None = None):
        """保存配置到文件"""
        file_path = Path(config_file) if config_file else self._config_file
        file_path.parent.mkdir(parents=True, exist_ok=True)

        config_data = {
            "name": self._config.name,
            "version": self._config.version,
            "debug": self._config.debug,
            "cache": {
                "enabled": self._config.cache.enabled,
                "max_size": self._config.cache.max_size,
                "ttl": self._config.cache.ttl,
                "cache_dir": self._config.cache.cache_dir,
            },
            "video": {
                "min_segment_duration": self._config.video.min_segment_duration,
                "max_segment_duration": self._config.video.max_segment_duration,
                "frame_sample_interval": self._config.video.frame_sample_interval,
                "min_confidence": self._config.video.min_confidence,
                "visual_weight": self._config.video.visual_weight,
                "audio_weight": self._config.video.audio_weight,
            },
            "tts": {
                "provider": self._config.tts.provider,
                "voice": self._config.tts.voice,
                "rate": self._config.tts.rate,
                "pitch": self._config.tts.pitch,
                "volume": self._config.tts.volume,
            },
            "llm_providers": {
                name: {
                    "enabled": cfg.enabled,
                    "api_key": cfg.api_key,
                    "base_url": cfg.base_url,
                    "model": cfg.model,
                    "max_tokens": cfg.max_tokens,
                    "temperature": cfg.temperature,
                }
                for name, cfg in self._config.llm_providers.items()
            },
            "default_llm": self._config.default_llm,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)


# 全局配置实例
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """获取应用配置（快捷函数）"""
    return config_manager.config


def get_llm_config(provider: str | None = None) -> LLMConfig | None:
    """获取 LLM 配置（快捷函数）"""
    return config_manager.get_llm_config(provider)


__all__ = [
    "ConfigManager",
    "AppConfig",
    "LLMConfig",
    "TTSConfig",
    "VideoConfig",
    "CacheConfig",
    "config_manager",
    "get_config",
    "get_llm_config",
]
