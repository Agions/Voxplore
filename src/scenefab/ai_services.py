#!/usr/bin/env python3
"""
SceneFab AI 服务层（兼容层 - 已废弃）
请直接导入 scenefab.services.ai.*
"""
import warnings

warnings.warn(
    "scenefab.ai_services is deprecated. "
    "Use scenefab.services.ai.llm, .vision, .tts, .asr, .manager instead.",
    DeprecationWarning,
    stacklevel=2,
)

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
from scenefab.services.ai.manager import AIServiceManager, ai_service_manager, get_ai_service
from scenefab.services.ai.base import ServiceStatus, ServiceHealth

__all__ = [
    # 基础设施
    "RateLimiter",
    "CircuitBreaker",
    "LRUCache",
    "PersistentCache",
    # 服务
    "LLMService",
    "VisionService",
    "TTSService",
    "ASRService",
    # 管理器
    "AIServiceManager",
    "ai_service_manager",
    "get_ai_service",
    # 状态
    "ServiceStatus",
    "ServiceHealth",
]