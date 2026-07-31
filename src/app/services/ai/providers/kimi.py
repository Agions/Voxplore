#!/usr/bin/env python3

"""
Kimi (月之暗面 Moonshot AI) 提供商
支持 moonshot-v1 系列模型
"""

from ..model_catalog import DEFAULT_MODELS, provider_models
from .openai_compat import OpenAICompatProvider


class KimiProvider(OpenAICompatProvider):
    """Kimi 提供商（OpenAI 兼容 API）"""

    PROVIDER_NAME = "kimi"
    DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"
    MODELS = provider_models("kimi")
    DEFAULT_MODEL = DEFAULT_MODELS["kimi"]
