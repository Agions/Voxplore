#!/usr/bin/env python3
"""
SceneFab 配置管理
统一管理系统配置、环境变量、参数设置
"""
import os
import yaml
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

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


@dataclass
class AppConfig:
    """应用配置"""
    name: str = "SceneFab"
    version: str = "2.0.0"
    debug: bool = False
    cache: CacheConfig = field(default_factory=CacheConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    llm_providers: dict[str, LLMConfig] = field(default_factory=dict)
    default_llm: str = "deepseek"


class ConfigManager:
    """
    配置管理器
    负责加载、验证和管理所有配置
    """

    _instance: Optional['ConfigManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._config: AppConfig | None = None
        self._config_file = Path(__file__).parent.parent / "config" / "app_config.yaml"
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        config_data = {
            "name": "SceneFab",
            "version": "2.0.0",
            "debug": os.getenv("VOXPLORE_DEBUG", "false").lower() == "true",
            "cache": {
                "enabled": True,
                "max_size": 100,
                "ttl": 3600,
                "cache_dir": os.path.expanduser(
                    os.getenv("VOXPLORE_CACHE_DIR", "~/.cache/scenefab")
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
            "llm_providers": {
                "deepseek": {
                    "enabled": bool(os.getenv("DEEPSEEK_API_KEY")),
                    "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
                    "base_url": "https://api.deepseek.com",
                    "model": "deepseek-v4",
                    "max_tokens": 16384,
                    "temperature": 0.7,
                },
                "qwen": {
                    "enabled": bool(os.getenv("DASHSCOPE_API_KEY")),
                    "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
                    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "model": "qwen-vl-plus",
                    "max_tokens": 8000,
                    "temperature": 0.7,
                },
                "openai": {
                    "enabled": bool(os.getenv("OPENAI_API_KEY")),
                    "api_key": os.getenv("OPENAI_API_KEY", ""),
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4o",
                    "max_tokens": 16384,
                    "temperature": 0.7,
                },
            },
            "default_llm": "deepseek",
        }

        # 从 YAML 文件加载（如果存在）
        if self._config_file.exists():
            try:
                with open(self._config_file, encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f) or {}
                    self._merge_config(config_data, yaml_config)
            except Exception as e:
                print(f"Warning: Failed to load config file: {e}")

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
            version=data.get("version", "2.0.0"),
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

    def get_llm_config(self, provider: str = None) -> LLMConfig | None:
        """获取指定 LLM 配置"""
        if provider is None:
            provider = self._config.default_llm
        return self._config.llm_providers.get(provider)

    def get_enabled_llm(self) -> list[LLMConfig]:
        """获取所有启用的 LLM"""
        return [
            cfg for cfg in self._config.llm_providers.values()
            if cfg.enabled
        ]

    def reload(self):
        """重新加载配置"""
        self._load_config()

    def save(self, config_file: str = None):
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

        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)


# 全局配置实例
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """获取应用配置（快捷函数）"""
    return config_manager.config


def get_llm_config(provider: str = None) -> LLMConfig | None:
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
