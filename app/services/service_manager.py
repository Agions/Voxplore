#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一服务管理器
提供全局服务访问入口
"""

from typing import Dict, Type, Optional, Any
from dataclasses import dataclass

# AI 服务
from .ai.llm_manager import LLMManager
from .ai.scene_analyzer import SceneAnalyzer
from .ai.voice_generator import VoiceGenerator
from .ai.script_generator import ScriptGenerator
from .ai.secure_subtitle_extractor import SecureSubtitleExtractor as SubtitleExtractor

# 视频服务
from .video.monologue_maker import MonologueMaker

# 导出服务
from .export.export_manager import ExportManager


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    service_class: Type
    instance: Optional[Any] = None


class ServiceManager:
    """
    统一服务管理器
    
    提供服务的注册、获取和生命周期管理
    """
    
    _services: Dict[str, ServiceInfo] = {}
    _initialized: bool = False
    
    @classmethod
    def register(cls, name: str, service_class: Type):
        """注册服务"""
        cls._services[name] = ServiceInfo(
            name=name,
            service_class=service_class,
        )
    
    @classmethod
    def get(cls, name: str) -> Optional[Any]:
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
    def get_all_services(cls) -> Dict[str, Any]:
        """获取所有服务"""
        cls.initialize()
        return {
            name: cls.get(name)
            for name in cls._services.keys()
        }
    
    @classmethod
    def reset(cls):
        """重置所有服务"""
        for info in cls._services.values():
            info.instance = None
        cls._initialized = False


# 全局初始化
ServiceManager.initialize()


# 便捷访问
def get_service(name: str) -> Optional[Any]:
    """获取服务"""
    return ServiceManager.get(name)


__all__ = [
    "ServiceManager",
    "ServiceInfo",
    "get_service",
]
