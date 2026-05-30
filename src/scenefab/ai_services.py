"""
AI 服务模块（兼容层）

已迁移至 scenefab.services.ai
"""
from scenefab.services.ai.infra import (
    RateLimiter,
    CircuitBreaker,
    LRUCache,
    PersistentCache,
)
from scenefab.services.ai.llm import LLMService
from scenefab.services.ai.vision import VisionService
from scenefab.services.ai.tts import TTSService
from scenefab.services.ai.asr import ASRService
from scenefab.services.ai.manager import (
    AIServiceManager,
    ai_service_manager,
    get_ai_service,
)
from scenefab.services.ai.base import ServiceStatus, ServiceHealth

__all__ = [
    "RateLimiter",
    "CircuitBreaker",
    "LRUCache",
    "PersistentCache",
    "LLMService",
    "VisionService",
    "TTSService",
    "ASRService",
    "AIServiceManager",
    "ai_service_manager",
    "get_ai_service",
    "ServiceStatus",
    "ServiceHealth",
]