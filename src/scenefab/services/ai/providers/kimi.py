#!/usr/bin/env python3

"""
Kimi (月之暗面 Moonshot AI) 提供商
支持 moonshot-v1 系列模型 (2026.03 最新)

使用公共混入类减少重复代码
"""

from ..base_llm_provider import (
    BaseLLMProvider,
    HTTPClientMixin,
    LLMRequest,
    LLMResponse,
    ModelManagerMixin,
)


class KimiProvider(BaseLLMProvider, HTTPClientMixin, ModelManagerMixin):
    """
    Kimi 提供商

    API 文档: https://platform.moonshot.cn/docs
    """

    # 模型管理混入需要
    MODELS = {
        "moonshot-v1-128k": {
            "name": "Kimi 128K",
            "description": "超长上下文，128K tokens",
            "max_tokens": 8000,
            "context_length": 128000,
            "vision": False,
        },
        "moonshot-v1-32k": {
            "name": "Kimi 32K",
            "description": "均衡版本，32K tokens",
            "max_tokens": 8000,
            "context_length": 32000,
        },
        "moonshot-v1-8k": {
            "name": "Kimi 8K",
            "description": "标准版本，8K tokens",
            "max_tokens": 4000,
            "context_length": 8000,
        },
    }
    DEFAULT_MODEL = "moonshot-v1-128k"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.moonshot.cn/v1",
    ):
        # 调用父类初始化
        BaseLLMProvider.__init__(self, api_key, base_url)
        HTTPClientMixin.__init__(self, api_key, base_url, timeout=60.0)

        # 初始化HTTP客户端
        self._init_http_client(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

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
