"""
AI Provider Registry
Provider 注册与管理中心
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

from .base import (
    BaseLLMAdapter, ProviderConfig, ProviderMetadata,
    VideoAnalysisAdapter, ScriptLLMAdapter, TTSAdapter,
    ProviderType
)

logger = logging.getLogger("voxplore.ai")


@dataclass
class RegistryEntry:
    adapter: BaseLLMAdapter
    config: ProviderConfig
    is_default: bool = False


class LLMProviderRegistry:
    """
    LLM Provider 注册中心
    
    职责:
    - 注册/注销 Provider
    - 获取 Provider 实例
    - 负载均衡
    - 配置管理
    """

    def __init__(self):
        self._video_providers: Dict[str, RegistryEntry] = {}
        self._script_providers: Dict[str, RegistryEntry] = {}
        self._tts_providers: Dict[str, RegistryEntry] = {}
        self._initialized = False

    def register(
        self,
        adapter: BaseLLMAdapter,
        config: ProviderConfig,
        as_default: bool = False,
    ) -> None:
        """注册 Provider"""
        entry = RegistryEntry(adapter=adapter, config=config, is_default=as_default)

        if adapter.provider_type == ProviderType.VIDEO_ANALYSIS:
            self._video_providers[adapter.provider_id] = entry
        elif adapter.provider_type == ProviderType.SCRIPT_LLM:
            self._script_providers[adapter.provider_id] = entry
        elif adapter.provider_type == ProviderType.VOICE_TTS:
            self._tts_providers[adapter.provider_id] = entry

        logger.info(f"Registered provider: {adapter.provider_id} ({adapter.provider_type.value})")

    def get_video_provider(self, name: Optional[str] = None) -> Optional[VideoAnalysisAdapter]:
        """获取视频分析 Provider"""
        if name and name in self._video_providers:
            return self._video_providers[name].adapter

        # 返回默认
        for entry in self._video_providers.values():
            if entry.is_default:
                return entry.adapter
        return next(iter(self._video_providers.values())).adapter if self._video_providers else None

    def get_script_provider(self, name: Optional[str] = None) -> Optional[ScriptLLMAdapter]:
        """获取脚本生成 Provider"""
        if name and name in self._script_providers:
            return self._script_providers[name].adapter

        for entry in self._script_providers.values():
            if entry.is_default:
                return entry.adapter
        return next(iter(self._script_providers.values())).adapter if self._script_providers else None

    def get_tts_provider(self, name: Optional[str] = None) -> Optional[TTSAdapter]:
        """获取 TTS Provider"""
        if name and name in self._tts_providers:
            return self._tts_providers[name].adapter

        for entry in self._tts_providers.values():
            if entry.is_default:
                return entry.adapter
        return next(iter(self._tts_providers.values())).adapter if self._tts_providers else None

    def list_providers(
        self,
        provider_type: Optional[ProviderType] = None
    ) -> List[ProviderMetadata]:
        """列出所有 Provider"""
        result = []
        targets = {
            ProviderType.VIDEO_ANALYSIS: self._video_providers,
            ProviderType.SCRIPT_LLM: self._script_providers,
            ProviderType.VOICE_TTS: self._tts_providers,
        }

        for ptype, providers in targets.items():
            if provider_type and ptype != provider_type:
                continue
            for entry in providers.values():
                result.append(entry.adapter.metadata)

        return result

    def get_default_provider(self, provider_type: ProviderType) -> Optional[BaseLLMAdapter]:
        """获取默认 Provider"""
        if provider_type == ProviderType.VIDEO_ANALYSIS:
            return self.get_video_provider()
        elif provider_type == ProviderType.SCRIPT_LLM:
            return self.get_script_provider()
        elif provider_type == ProviderType.VOICE_TTS:
            return self.get_tts_provider()
        return None

    async def initialize_all(self) -> None:
        """初始化所有已注册的 Provider"""
        for providers in [self._video_providers, self._script_providers, self._tts_providers]:
            for entry in providers.values():
                if entry.config.enabled:
                    try:
                        await entry.adapter.initialize()
                    except Exception as e:
                        logger.error(f"Failed to initialize {entry.config.name}: {e}")

        self._initialized = True

    async def close_all(self) -> None:
        """关闭所有 Provider"""
        for providers in [self._video_providers, self._script_providers, self._tts_providers]:
            for entry in providers.values():
                try:
                    await entry.adapter.close()
                except Exception as e:
                    logger.error(f"Error closing {entry.config.name}: {e}")

        self._initialized = False

    def load_from_config(self, config_path: str) -> None:
        """从配置文件加载 Provider"""
        import yaml
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # 动态导入并注册 adapters
        # 具体实现略（见 ai_service_manager.py）
        pass

    @property
    def is_initialized(self) -> bool:
        return self._initialized


# 全局单例
_registry = LLMProviderRegistry()

def get_registry() -> LLMProviderRegistry:
    return _registry
