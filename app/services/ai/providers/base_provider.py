#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Provider Mixins
通用混入类，提供 HTTP/批量/重试等功能

这些 Mixin 可被各 Provider 选择性使用，
以减少重复代码。所有 Mixin 与 BaseLLMProvider 完全兼容。
"""

import httpx
import asyncio
from typing import List, Dict, Any, AsyncGenerator


class HTTPProviderMixin:
    """HTTP Provider 混入 - 通用 HTTP 请求逻辑"""

    async def _post(
        self,
        endpoint: str,
        json_data: Dict,
        stream: bool = False,
    ) -> httpx.Response:
        """发送 POST 请求"""
        url = f"{self.base_url}{endpoint}"

        if stream:
            return await self.client.post(url, json=json_data, stream=True)
        return await self.client.post(url, json=json_data)

    async def _get(self, endpoint: str, params: Dict = None) -> httpx.Response:
        """发送 GET 请求"""
        url = f"{self.base_url}{endpoint}"
        return await self.client.get(url, params=params)


class BatchProviderMixin:
    """批量处理混入 - 提供默认批量生成实现"""

    async def batch_generate(
        self,
        prompts: List[str],
        model: str = None,
        **kwargs,
    ) -> List[Any]:
        """
        批量生成（默认实现）

        子类可覆盖以使用提供商特有优化（如并发控制）。
        """
        from ..base_llm_provider import LLMRequest, gather_with_concurrency

        requests = [
            LLMRequest(prompt=prompt, model=model or self.DEFAULT_MODEL, **kwargs)
            for prompt in prompts
        ]

        # 使用 gather_with_concurrency 控制并发
        results = await gather_with_concurrency(
            5,  # 默认最大并发
            *[self.generate(req) for req in requests]
        )

        # 过滤错误，返回有效响应
        from ..base_llm_provider import LLMResponse
        return [
            r if isinstance(r, LLMResponse) else None
            for r in results
        ]


class RetryProviderMixin:
    """重试逻辑混入 - 指数退避重试"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        exponential_base: float = 2.0,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.exponential_base = exponential_base

    async def _retry_generate(self, request: "LLMRequest") -> "LLMResponse":
        """带重试的生成（指数退避）"""
        from ..base_llm_provider import LLMResponse, ProviderError

        last_error = None

        for attempt in range(self.max_retries):
            try:
                return await self.generate(request)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (self.exponential_base ** attempt)
                    await asyncio.sleep(delay)

        raise last_error
