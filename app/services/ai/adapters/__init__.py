"""
AI Adapters Package
可插拔的 AI Provider 适配器
"""

from app.services.ai.adapters.base import (
    BaseLLMAdapter,
    ProviderConfig,
    ProviderMetadata,
    ProviderType,
    VideoAnalysisAdapter,
    ScriptLLMAdapter,
    TTSAdapter,
)
from app.services.ai.adapters.registry import (
    LLMProviderRegistry,
    get_registry,
)

__all__ = [
    "BaseLLMAdapter",
    "ProviderConfig",
    "ProviderMetadata",
    "ProviderType",
    "VideoAnalysisAdapter",
    "ScriptLLMAdapter",
    "TTSAdapter",
    "LLMProviderRegistry",
    "get_registry",
]
