#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智谱 GLM-4 提供商
支持 GLM-4 系列模型 (2026.03 最新)

使用公共混入类减少重复代码
"""

from ..base_llm_provider import (
    BaseLLMProvider,
    HTTPClientMixin,
    LLMRequest,
    LLMResponse,
    ModelManagerMixin,
)


class GLM5Provider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """智谱 GLM-4 提供商"""

    # 模型管理混入需要
    MODELS = {
        "glm-4-flash": {
            "name": "GLM-4 Flash",
            "description": "高性价比，响应最快",
            "max_tokens": 8000,
            "context_length": 128000,
        },
        "glm-4-plus": {
            "name": "GLM-4 Plus",
            "description": "综合能力增强版",
            "max_tokens": 8000,
            "context_length": 128000,
        },
        "glm-4": {
            "name": "GLM-4",
            "description": "标准版",
            "max_tokens": 4000,
            "context_length": 128000,
        },
    }
    DEFAULT_MODEL = "glm-4-flash"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://open.bigmodel.cn/api/paas/v4/",
    ):
        # 调用父类初始化
        BaseLLMProvider.__init__(self, api_key, base_url)
        HTTPClientMixin.__init__(self, api_key, base_url, timeout=60.0)

        # 初始化HTTP客户端
        self._init_http_client({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成文本"""
        model = self._get_model_name(request.model)
        messages = self._build_messages(request)
        return await self._generate_openai_compatible(
            request=request,
            model=model,
            messages=messages,
            endpoint="/chat/completions",
        )


