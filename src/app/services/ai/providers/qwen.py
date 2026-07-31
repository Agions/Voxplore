#!/usr/bin/env python3

"""通义千问 Qwen 提供商。"""

from ..model_catalog import DEFAULT_MODELS, provider_models
from .openai_compat import OpenAICompatProvider


class QwenProvider(OpenAICompatProvider):
    """通义千问提供商（OpenAI 兼容 API）。"""

    PROVIDER_NAME = "qwen"
    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    MODELS = provider_models("qwen")
    DEFAULT_MODEL = DEFAULT_MODELS["qwen"]
