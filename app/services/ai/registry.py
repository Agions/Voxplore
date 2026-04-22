#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Provider 注册表

统一管理 Vision、LLM、TTS 三类 AI Provider 的注册与获取。
支持配置文件热加载（YAML 格式）。
"""

from pathlib import Path

import yaml

from .interfaces import VisionProvider, LLMProvider, TTSProvider


class ProviderRegistry:
    """AI Provider 注册表（单例）

    用法::

        registry = ProviderRegistry.instance()

        # 注册 Provider
        registry.register_vision("qwen_vl", MyVisionProvider())
        registry.register_llm("deepseek", MyLLMProvider())
        registry.register_tts("edge_tts", MyTTSProvider())

        # 获取 Provider
        vision = registry.get_vision("qwen_vl")
        llm = registry.get_llm("deepseek")
        tts = registry.get_tts("edge_tts")

        # 获取默认 Provider
        default_vision = registry.get_default_vision()
    """

    _instance: "ProviderRegistry | None" = None

    def __init__(self):
        self._vision_providers: dict[str, VisionProvider] = {}
        self._llm_providers: dict[str, LLMProvider] = {}
        self._tts_providers: dict[str, TTSProvider] = {}
        self._config: dict | None = None
        self._default_vision: str | None = None
        self._default_llm: str | None = None
        self._default_tts: str | None = None

    @classmethod
    def instance(cls) -> "ProviderRegistry":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Vision Provider
    # -------------------------------------------------------------------------

    def register_vision(self, name: str, provider: VisionProvider) -> None:
        """注册 Vision Provider"""
        self._vision_providers[name] = provider

    def get_vision(self, name: str) -> VisionProvider:
        """获取指定名称的 Vision Provider"""
        if name not in self._vision_providers:
            raise KeyError(f"Vision provider '{name}' not found. Available: {list(self._vision_providers.keys())}")
        return self._vision_providers[name]

    def get_default_vision(self) -> VisionProvider:
        """获取默认 Vision Provider"""
        if self._default_vision is None:
            if not self._vision_providers:
                raise RuntimeError("No Vision providers registered")
            self._default_vision = next(iter(self._vision_providers))
        return self._vision_providers[self._default_vision]

    def set_default_vision(self, name: str) -> None:
        """设置默认 Vision Provider"""
        if name not in self._vision_providers:
            raise KeyError(f"Vision provider '{name}' not found")
        self._default_vision = name

    # -------------------------------------------------------------------------
    # LLM Provider
    # -------------------------------------------------------------------------

    def register_llm(self, name: str, provider: LLMProvider) -> None:
        """注册 LLM Provider"""
        self._llm_providers[name] = provider

    def get_llm(self, name: str) -> LLMProvider:
        """获取指定名称的 LLM Provider"""
        if name not in self._llm_providers:
            raise KeyError(f"LLM provider '{name}' not found. Available: {list(self._llm_providers.keys())}")
        return self._llm_providers[name]

    def get_default_llm(self) -> LLMProvider:
        """获取默认 LLM Provider"""
        if self._default_llm is None:
            if not self._llm_providers:
                raise RuntimeError("No LLM providers registered")
            self._default_llm = next(iter(self._llm_providers))
        return self._llm_providers[self._default_llm]

    def set_default_llm(self, name: str) -> None:
        """设置默认 LLM Provider"""
        if name not in self._llm_providers:
            raise KeyError(f"LLM provider '{name}' not found")
        self._default_llm = name

    # -------------------------------------------------------------------------
    # TTS Provider
    # -------------------------------------------------------------------------

    def register_tts(self, name: str, provider: TTSProvider) -> None:
        """注册 TTS Provider"""
        self._tts_providers[name] = provider

    def get_tts(self, name: str) -> TTSProvider:
        """获取指定名称的 TTS Provider"""
        if name not in self._tts_providers:
            raise KeyError(f"TTS provider '{name}' not found. Available: {list(self._tts_providers.keys())}")
        return self._tts_providers[name]

    def get_default_tts(self) -> TTSProvider:
        """获取默认 TTS Provider"""
        if self._default_tts is None:
            if not self._tts_providers:
                raise RuntimeError("No TTS providers registered")
            self._default_tts = next(iter(self._tts_providers))
        return self._tts_providers[self._default_tts]

    def set_default_tts(self, name: str) -> None:
        """设置默认 TTS Provider"""
        if name not in self._tts_providers:
            raise KeyError(f"TTS provider '{name}' not found")
        self._default_tts = name

    # -------------------------------------------------------------------------
    # Config
    # -------------------------------------------------------------------------

    def load_config(self, config_path: str | Path) -> dict:
        """从 YAML 文件加载 Provider 配置

        Args:
            config_path: 配置文件路径

        Returns:
            dict: 解析后的配置字典
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

        # 设置默认 Provider
        providers = self._config.get("providers", {})
        if "vision" in providers:
            vision_cfg = providers["vision"]
            if "default" in vision_cfg:
                self._default_vision = vision_cfg["default"]

        if "llm" in providers:
            llm_cfg = providers["llm"]
            if "default" in llm_cfg:
                self._default_llm = llm_cfg["default"]

        if "tts" in providers:
            tts_cfg = providers["tts"]
            if "default" in tts_cfg:
                self._default_tts = tts_cfg["default"]

        return self._config

    @property
    def config(self) -> dict | None:
        """获取当前配置"""
        return self._config

    # -------------------------------------------------------------------------
    # Introspection
    # -------------------------------------------------------------------------

    def list_vision_providers(self) -> list[str]:
        """列出所有已注册的 Vision Provider"""
        return list(self._vision_providers.keys())

    def list_llm_providers(self) -> list[str]:
        """列出所有已注册的 LLM Provider"""
        return list(self._llm_providers.keys())

    def list_tts_providers(self) -> list[str]:
        """列出所有已注册的 TTS Provider"""
        return list(self._tts_providers.keys())
