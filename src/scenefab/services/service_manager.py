#!/usr/bin/env python3

"""
统一服务管理器
提供全局服务访问入口

整合了:
- services/ai_service_manager.py 的 AIServiceManager 兼容接口
- ai_services.py 的 AIServiceManager V2 (LLMService, VisionService, TTSService, ASRService)
- services/service_manager.py 的 ServiceManager 架构
"""

import threading
from dataclasses import dataclass
from typing import Any, Optional

# 统一从 ai.base 导入权威 ServiceStatus/ServiceHealth
from scenefab.services.ai.base import ServiceHealth, ServiceStatus

# AI Services (split from ai_services.py)
from scenefab.services.ai.manager import AIServiceManager as AIServiceManagerV2

# AI 服务
from .ai.llm_manager import LLMManager
from .ai.scene_analyzer import SceneAnalyzer
from .ai.script_generator import ScriptGenerator
from .ai.secure_subtitle_extractor import SecureSubtitleExtractor as SubtitleExtractor
from .ai.voice_generator import VoiceGenerator

# 导出服务
from .export.export_manager import ExportManager

# 视频服务
from .video.monologue_maker import MonologueMaker


@dataclass
class ServiceInfo:
    """服务信息"""

    name: str
    service_class: type
    instance: Any | None = None


class ServiceManager:
    """
    统一服务管理器

    提供服务的注册、获取和生命周期管理
    """

    _services: dict[str, ServiceInfo] = {}
    _initialized: bool = False

    # AIServiceManager V2 实例 (委托目标)
    _ai_manager: Optional["AIServiceManagerCompat"] = None

    @classmethod
    def register(cls, name: str, service_class: type):
        """注册服务"""
        cls._services[name] = ServiceInfo(
            name=name,
            service_class=service_class,
        )

    @classmethod
    def get(cls, name: str) -> Any | None:
        """获取服务实例"""
        if name not in cls._services:
            return None

        info = cls._services[name]

        # 懒加载
        if info.instance is None:
            info.instance = info.service_class()

        return info.instance

    @classmethod
    def initialize(cls):
        """初始化所有服务"""
        if cls._initialized:
            return

        # 注册 AI 服务
        cls.register("llm", LLMManager)
        cls.register("scene_analyzer", SceneAnalyzer)
        cls.register("voice_generator", VoiceGenerator)
        cls.register("script_generator", ScriptGenerator)
        cls.register("subtitle_extractor", SubtitleExtractor)

        # 注册视频服务
        cls.register("monologue", MonologueMaker)

        # 注册导出服务
        cls.register("export", ExportManager)

        cls._initialized = True

    @classmethod
    def get_all_services(cls) -> dict[str, Any]:
        """获取所有服务"""
        cls.initialize()
        return {name: cls.get(name) for name in cls._services}

    @classmethod
    def reset(cls):
        """重置所有服务"""
        for info in cls._services.values():
            info.instance = None
        cls._initialized = False
        cls._ai_manager = None

    @classmethod
    def get_ai_manager(cls) -> "AIServiceManagerCompat":
        """获取 AI 服务管理器（兼容层）"""
        if cls._ai_manager is None:
            cls._ai_manager = AIServiceManagerCompat()
        return cls._ai_manager


class AIServiceManagerCompat:
    """
    AI 服务管理器兼容层

    整合了旧版 AIServiceManager 和 ai_services.py 的 AIServiceManager V2
    提供统一的 AI 服务管理和健康检查接口
    """

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._service_health: dict[str, ServiceHealth] = {}
        self.service_health_updated = None  # Signal placeholder
        self.stats_updated = None  # Signal placeholder

        # 委托给 AIServiceManager V2
        self._v2_manager = AIServiceManagerV2()

    def register_service(self, name: str, service: Any) -> None:
        """注册服务"""
        self._services[name] = service

    def get_service(self, name: str) -> Any | None:
        """获取服务"""
        return self._services.get(name)

    def get_all_services(self) -> dict[str, Any]:
        """获取所有服务"""
        services = self._services.copy()
        # 添加 V2 管理器的服务
        services["llm"] = self._v2_manager.get_llm()
        services["vision"] = self._v2_manager.vision
        services["tts"] = self._v2_manager.tts
        services["asr"] = self._v2_manager.asr
        return services

    def get_service_health(self, service_name: str) -> ServiceHealth | None:
        """获取服务健康状态"""
        return self._service_health.get(service_name)

    @property
    def service_health(self) -> dict[str, ServiceHealth]:
        """获取所有服务健康状态"""
        return self._service_health

    def get_usage_stats(self, service_name: str) -> dict[str, Any]:
        """获取使用统计"""
        if service_name in self._services:
            service = self._services[service_name]
            if hasattr(service, "_stats"):
                return service._stats  # type: ignore[no-any-return]
        return {
            "requests": 0,
            "errors": 0,
            "avg_response_time": 0.0,
        }

    def get_summary(self) -> dict[str, Any]:
        """获取摘要"""
        return self._v2_manager.get_summary()

    # V2 管理器方法委托
    def register_llm(self, name: str, config: dict[str, Any]) -> None:
        """注册 LLM 服务"""
        self._v2_manager.register_llm(name, config)

    def register_vision(self, config: dict[str, Any]) -> None:
        """注册视觉服务"""
        self._v2_manager.register_vision(config)

    def register_tts(self, config: dict[str, Any] | None = None) -> None:
        """注册 TTS 服务"""
        self._v2_manager.register_tts(config or {})

    def register_asr(self, config: dict[str, Any] | None = None) -> None:
        """注册 ASR 服务"""
        self._v2_manager.register_asr(config or {})

    def get_llm(self, name: str = None):  # type: ignore[assignment]
        """获取 LLM 服务"""
        return self._v2_manager.get_llm(name)

    @property
    def vision(self):
        """获取视觉服务"""
        return self._v2_manager.vision

    @property
    def tts(self):
        """获取 TTS 服务"""
        return self._v2_manager.tts

    @property
    def asr(self):
        """获取 ASR 服务"""
        return self._v2_manager.asr


# 全局实例
_service_manager: AIServiceManagerCompat | None = None
_service_lock = threading.Lock()


def get_ai_service_manager() -> AIServiceManagerCompat:
    """获取 AI 服务管理器实例"""
    global _service_manager
    if _service_manager is None:
        with _service_lock:
            if _service_manager is None:
                _service_manager = ServiceManager.get_ai_manager()
    return _service_manager


# 全局初始化
ServiceManager.initialize()


# 便捷访问
def get_service(name: str) -> Any | None:
    """获取服务"""
    return ServiceManager.get(name)


__all__ = [
    "ServiceManager",
    "ServiceInfo",
    "ServiceStatus",
    "ServiceHealth",
    "AIServiceManagerCompat",
    "get_service",
    "get_ai_service_manager",
]
