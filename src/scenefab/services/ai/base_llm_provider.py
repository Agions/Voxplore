#!/usr/bin/env python3

"""
LLM 提供商抽象基类
所有具体提供商必须实现此接口

包含:
- 混入类 (HTTPClientMixin, ModelManagerMixin)
- 基类 (BaseLLMProvider)
- 速率限制器 (RateLimiter)
- 熔断器 (CircuitBreaker)
- 重试机制 (RetryHandler)

优化:
- asyncio.gather 并发批量处理
- tenacity 重试机制
- 指数退避
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

import httpx

from scenefab.exceptions import (
    CircuitOpenError,
    ProviderError,
    RateLimitError,
)

from .provider_types import LLMRequest, LLMResponse, ProviderType
from .retry import (
    CircuitBreaker,
    RateLimiter,
    RetryHandler,
)

logger = logging.getLogger(__name__)


# ============ 公共常量 ============
DEFAULT_CACHE_TTL = 3600.0  # 默认请求缓存 TTL: 1小时（秒）
DEFAULT_LONG_CACHE_TTL = 86400.0  # 长缓存 TTL: 24小时（秒）
DEFAULT_RETRY_MAX_DELAY = 30.0  # 重试最大延迟（秒）
DEFAULT_KEEPALIVE_EXPIRY = 30.0  # HTTP keepalive 过期时间（秒）
DEFAULT_LOCAL_TIMEOUT = 300.0  # 本地 LLM 请求超时（秒，5分钟）


# ============ RequestCache ============


class RequestCache:
    """
    请求缓存 - 基于哈希的简单缓存
    减少重复 API 调用
    """

    def __init__(self, max_size: int = 1000, ttl: float = DEFAULT_CACHE_TTL) -> None:
        self.max_size = max_size
        self.ttl = ttl
        self._cache: dict[str, tuple] = {}  # key -> (value, expiry)
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, request: LLMRequest) -> str:
        """生成缓存键"""
        content = f"{request.model}:{request.prompt[:100]}:{request.temperature}"
        return hashlib.md5(content.encode()).hexdigest()

    async def get_from_key(self, key: str) -> LLMResponse | None:
        """获取缓存的响应（通过缓存键）"""
        async with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.monotonic() < expiry:
                    logger.debug(f"缓存命中: {key[:8]}...")
                    self._hits += 1
                    return value  # type: ignore[no-any-return]
                else:
                    del self._cache[key]
        self._misses += 1
        return None

    async def set_from_key(self, key: str, response: LLMResponse) -> None:
        """缓存响应（通过缓存键）"""
        async with self._lock:
            # 清理过期项
            if len(self._cache) >= self.max_size:
                self._cleanup()
            self._cache[key] = (response, time.monotonic() + self.ttl)

    def _cleanup(self) -> None:
        """清理过期缓存"""
        now = time.monotonic()
        expired = [k for k, (_, expiry) in self._cache.items() if now >= expiry]
        for k in expired:
            del self._cache[k]

        # 如果还是太多，删除最老的
        if len(self._cache) >= self.max_size:
            oldest = sorted(self._cache.items(), key=lambda x: x[1][1])[
                : len(self._cache) // 2
            ]
            for k, _ in oldest:
                del self._cache[k]

    async def clear(self) -> None:
        """清空缓存"""
        async with self._lock:
            self._cache.clear()


# ============ 混入类 (Mixins) ============


class HTTPClientMixin:
    """HTTP客户端混入类 - 提供通用的HTTP请求功能"""

    def __init__(self, api_key: str, base_url: str, timeout: float = 60.0) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.http_client: httpx.AsyncClient | None = None
        self._default_headers: dict[str, str] = {}
        # ✅ 新增：重试处理器
        self._retry_handler = RetryHandler(
            max_attempts=3, base_delay=1.0, max_delay=DEFAULT_RETRY_MAX_DELAY
        )

    def _init_http_client(self, headers: dict[str, str] | None = None) -> None:
        """初始化HTTP客户端"""
        merged_headers = {**self._default_headers}
        if headers:
            merged_headers.update(headers)

        # 安全配置：限制重定向、防超时
        self.http_client = httpx.AsyncClient(
            headers=merged_headers,
            timeout=self.timeout,
            follow_redirects=False,  # 安全：不自动重定向
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=DEFAULT_KEEPALIVE_EXPIRY,
            ),
        )

    async def _close_http_client(self) -> None:
        """关闭HTTP客户端"""
        if self.http_client:
            await self.http_client.aclose()

    def _build_messages(self, request: LLMRequest) -> list[dict[str, str]]:
        """构建消息列表"""
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        return messages

    def _parse_response(
        self, data: dict[str, Any], model: str, latency_ms: float = 0
    ) -> LLMResponse:
        """解析标准OpenAI格式的响应"""
        if "error" in data:
            raise ProviderError(data["error"]["message"])

        # 验证响应格式
        if not data.get("choices"):
            raise ProviderError("API 响应格式错误: 缺少 choices 字段")

        choice = data["choices"][0]
        if not choice.get("message"):
            raise ProviderError("API 响应格式错误: 缺少 message 字段")

        content = choice["message"].get("content", "")

        return LLMResponse(
            content=content,
            model=model,
            tokens_used=data.get("usage", {}).get("total_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
            latency_ms=latency_ms,  # ✅ 新增延迟统计
        )

    # ========== Context Manager ==========

    async def __aenter__(self) -> "HTTPClientMixin":
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        await self._close_http_client()

    # ========== HTTP Error Handling ==========

    def _handle_http_error(self, e: httpx.HTTPStatusError) -> ProviderError:
        """处理HTTP错误"""
        error_msg = f"HTTP 错误: {e.response.status_code}"
        try:
            error_data = e.response.json()
            if "error" in error_data:
                error_msg = f"{error_msg} - {error_data['error']['message']}"
            # 针对特定状态码的处理
            if e.response.status_code == 429:
                error_msg = f"速率限制: {error_msg}"
            elif e.response.status_code == 500:
                error_msg = f"服务器错误: {error_msg}"
            elif e.response.status_code == 401:
                error_msg = f"认证失败: {error_msg}"
        except Exception as e:
            logger.debug(f"Failed to parse error response: {e}")
        return ProviderError(error_msg)

    async def _call_api(
        self, method: str, endpoint: str, **kwargs
    ) -> dict[str, Any]:
        """
        通用非流式 API 调用（含统一错误包装）。

        用法::
            data = await self._call_api("POST", endpoint, json=payload)
        """
        try:
            response = await self.http_client.request(method, endpoint, **kwargs)  # type: ignore[union-attr]
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise self._handle_http_error(e) from e
        except httpx.HTTPError as e:
            # 网络/HTTP 错误 (连接超时/DNS失败/SSL错误等), 显式收口
            # 不吞 RuntimeError/TypeError 等真实编程 bug
            raise ProviderError(f"API 调用失败 (网络错误): {e}") from e
        # 响应解析错误单独 catch, 不污染网络错误路径
        try:
            return response.json()  # type: ignore[no-any-return]
        except (json.JSONDecodeError, ValueError) as e:
            raise ProviderError(f"API 调用失败 (响应解析): {e}") from e

    async def _call_api_with_retry(
        self, method: str, endpoint: str, **kwargs
    ) -> dict[str, Any]:
        """带重试的通用 API 调用。"""

        async def _call() -> dict[str, Any]:
            return await self._call_api(method, endpoint, **kwargs)

        return await self._retry_handler.execute(_call)

    def _provider_error(self, action: str, error: Exception) -> ProviderError:
        """统一 provider 业务错误文案。"""
        if isinstance(error, httpx.HTTPStatusError):
            return self._handle_http_error(error)
        if isinstance(error, ProviderError):
            return error
        return ProviderError(f"{action}失败: {str(error)}")

    def _stream_provider_error(self, error: Exception) -> ProviderError:
        """统一流式生成错误文案。"""
        return self._provider_error("流式生成", error)

    async def _generate_openai_compatible(
        self,
        request: "LLMRequest",
        model: str,
        messages: list[dict[str, str]],
        endpoint: str = "/chat/completions",
    ) -> LLMResponse:
        """
        通用 OpenAI-compatible API 生成（供 GLM/Kimi 等 Provider 使用）。

        差异仅在 endpoint 路径，已在调用处传入。
        """
        start_time = time.monotonic()
        try:
            data = await self._call_api_with_retry(
                "POST",
                f"{self.base_url}{endpoint}",
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "top_p": request.top_p,
                },
            )
            latency_ms = (time.monotonic() - start_time) * 1000
            return self._parse_response(data, model, latency_ms)
        except Exception as e:
            raise self._provider_error("生成", e)

    async def _parse_sse_stream(
        self,
        response,
        delta_key: str = "delta",
        content_key: str = "content",
    ) -> AsyncIterator[str]:
        """
        通用 SSE 流式解析（供 Doubao/Hunyuan 等 Provider 使用）。

        Args:
            response: httpx 的流式响应
            delta_key: delta 字段的键名（OpenAI 用 "delta"，混元用 "Delta"）
            content_key: content 字段的键名（OpenAI 用 "content"，混元用 "Content"）
        """
        async for data in self._iter_json_stream_payloads(response, sse=True):
            choices = data.get("choices", [])
            if choices:
                delta = choices[0].get(delta_key, {})
                if content_key in delta:
                    yield delta[content_key]

    async def _iter_json_stream_payloads(
        self,
        response,
        *,
        sse: bool,
    ) -> AsyncIterator[dict[str, Any]]:
        """从流式响应中解析 JSON payload，兼容 SSE 和裸 JSON 行。"""
        async for line in response.aiter_lines():
            line = line.strip()
            if not line or line.startswith(":"):
                continue
            if sse:
                if not line.startswith("data: "):
                    continue
                line = line[6:]
                if line == "[DONE]":
                    break
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


class ModelManagerMixin:
    """模型管理混入类 - 提供通用的模型管理功能"""

    # 子类需要定义: MODELS, DEFAULT_MODEL
    MODELS: dict[str, dict[str, Any]] = {}
    DEFAULT_MODEL: str = ""

    def _get_model_name(self, model: str) -> str:
        """获取模型实际名称"""
        if model == "default":
            return self.DEFAULT_MODEL
        if model in self.MODELS:
            return model
        raise ValueError(f"Unknown model: {model}")

    def get_available_models(self) -> list[str]:
        """获取可用模型列表"""
        return list(self.MODELS.keys())

    def get_model_info(self, model: str) -> dict[str, Any]:
        """获取模型信息"""
        return self.MODELS.get(model, {})

    def supports_vision(self, model: str) -> bool:
        """检查模型是否支持视觉"""
        model_info = self.MODELS.get(model, {})
        return model_info.get("vision", False)  # type: ignore[no-any-return]

    def is_reasoning_model(self, model: str) -> bool:
        """检查是否是推理模型"""
        model_info = self.MODELS.get(model, {})
        return model_info.get("reasoning", False)  # type: ignore[no-any-return]


# ============ 基类 ============


class BaseLLMProvider(ABC):
    """LLM 提供商抽象基类"""

    def __init__(self, api_key: str, base_url: str) -> None:
        """
        初始化提供商

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
        """
        self.api_key = api_key
        self.base_url = base_url

        # 初始化请求缓存（减少重复 API 调用，TTL=24h）
        self._cache = RequestCache(max_size=500, ttl=DEFAULT_LONG_CACHE_TTL)

    def _make_cache_key(self, request: LLMRequest) -> str:
        """生成缓存键（基于 model + prompt 前200字 + temperature）"""
        prompt_preview = request.prompt[:200] if request.prompt else ""
        content = f"{request.model}:{prompt_preview}:{request.temperature}:{request.max_tokens}"
        return hashlib.md5(content.encode()).hexdigest()

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        生成文本

        Args:
            request: LLM 请求

        Returns:
            LLM 响应

        Raises:
            ProviderError: 提供商错误
        """
        pass

    def health_check(self, timeout: float = 5.0) -> bool:
        """
        健康检查（带超时）

        默认实现：尝试用 model list API 或简单 completion 检测连通性。
        子类可覆盖自定义检查逻辑。

        Args:
            timeout: 超时时间（秒）

        Returns:
            提供商是否可用
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            # 构建最简单的请求
            request = LLMRequest(
                prompt="ping",
                model="default",
                max_tokens=1,
                temperature=0.0,
            )
            result = loop.run_until_complete(
                asyncio.wait_for(self.generate(request), timeout=timeout)
            )
            return result is not None
        except (asyncio.TimeoutError, Exception):
            return False

    async def generate_cached(self, request: LLMRequest) -> LLMResponse:
        """
        生成文本（带缓存）✅ 优化：重复 prompt 直接返回缓存结果

        缓存键 = model + prompt 前200字 + temperature + max_tokens（TTL=24h）。
        """
        key = self._make_cache_key(request)
        cached = await self._cache.get_from_key(key)
        if cached is not None:
            logger.debug(f"[Cache hit] {key[:8]}... ({self.__class__.__name__})")
            return cached
        response = await self.generate(request)
        await self._cache.set_from_key(key, response)
        return response

    async def close(self) -> None:
        """关闭连接"""
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.base_url}>"


# ============ 工具函数 ============


async def gather_with_concurrency(
    n: int, *tasks, return_exceptions: bool = True
) -> list[Any]:
    """
    控制并发数的 asyncio.gather ✅ 新增

    Args:
        n: 最大并发数
        *tasks: 异步任务
        return_exceptions: 是否返回异常

    Returns:
        结果列表
    """
    semaphore = asyncio.Semaphore(n)

    async def _run_with_semaphore(task):
        async with semaphore:
            return await task

    return await asyncio.gather(
        *[_run_with_semaphore(task) for task in tasks],
        return_exceptions=return_exceptions,
    )


__all__ = [
    # Re-exported from provider_types for backward compatibility
    "ProviderType",
    "LLMRequest",
    "LLMResponse",
    # From errors/retry
    "ProviderError",
    "RateLimitError",
    "CircuitOpenError",
    "RateLimiter",
    "CircuitBreaker",
    "RequestCache",
    "RetryHandler",
    # Mixins and base
    "HTTPClientMixin",
    "ModelManagerMixin",
    "BaseLLMProvider",
    "gather_with_concurrency",
]
