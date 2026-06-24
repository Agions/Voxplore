#!/usr/bin/env python3

"""
智谱 GLM-5 提供商
支持 GLM-5 系列模型
"""

from ..model_catalog import DEFAULT_MODELS, provider_models
from .openai_compat import OpenAICompatProvider


class GLM5Provider(OpenAICompatProvider):
    """智谱 GLM-5 提供商（OpenAI 兼容 API）"""

    PROVIDER_NAME = "glm5"
    DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
    MODELS = provider_models("glm5")
    DEFAULT_MODEL = DEFAULT_MODELS["glm5"]
