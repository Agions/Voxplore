"""
AI 服务管理器
统一管理 LLM、Vision、TTS、ASR 服务
"""
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AIServiceManager:
    """AI 服务管理器"""

    _instance: Optional['AIServiceManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._llm_services: dict[str, Any] = {}
        self._vision_service: Optional[Any] = None
        self._tts_service: Optional[Any] = None
        self._asr_service: Optional[Any] = None

    def register_llm(self, name: str, config: dict[str, Any]) -> None:
        from scenefab.services.ai.llm import LLMService
        service = LLMService(config)
        self._llm_services[name] = service
        logger.info(f"Registered LLM service: {name}")

    def register_vision(self, config: dict[str, Any]) -> None:
        from scenefab.services.ai.vision import VisionService
        self._vision_service = VisionService(config)
        logger.info(f"Registered vision service: {config.get('name', 'unknown')}")

    def register_tts(self, config: dict[str, Any] = None) -> None:
        from scenefab.services.ai.tts import TTSService
        self._tts_service = TTSService(config)
        logger.info(f"Registered TTS service: {config.get('provider', 'edge') if config else 'edge'}")

    def register_asr(self, config: dict[str, Any] = None) -> None:
        from scenefab.services.ai.asr import ASRService
        self._asr_service = ASRService(config)
        logger.info(f"Registered ASR service: {config.get('provider', 'faster-whisper') if config else 'faster-whisper'}")

    def get_llm(self, name: str = None) -> Optional[Any]:
        if name:
            return self._llm_services.get(name)
        for service in self._llm_services.values():
            if service.enabled:
                return service
        return None

    @property
    def vision(self) -> Optional[Any]:
        return self._vision_service

    @property
    def tts(self) -> Optional[Any]:
        return self._tts_service

    @property
    def asr(self) -> Optional[Any]:
        return self._asr_service

    def get_summary(self) -> dict[str, Any]:
        return {
            "llm_services": {
                name: {
                    "enabled": svc.enabled,
                    "requests": svc._stats["requests"],
                    "errors": svc._stats["errors"],
                }
                for name, svc in self._llm_services.items()
            },
            "vision_enabled": self._vision_service is not None and self._vision_service.enabled,
            "vision_cache_hits": self._vision_service._stats.get("cache_hits", 0) if self._vision_service else 0,
            "tts_provider": self._tts_service.provider if self._tts_service else None,
            "asr_provider": self._asr_service.provider if self._asr_service else None,
        }


# 全局实例
ai_service_manager = AIServiceManager()


def get_ai_service() -> AIServiceManager:
    return ai_service_manager


__all__ = [
    "AIServiceManager",
    "ai_service_manager",
    "get_ai_service",
]