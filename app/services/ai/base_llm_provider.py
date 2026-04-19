#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM 提供商抽象基类
所有具体提供商必须实现此接口

包含:
- 枚举定义 (ProviderType, etc.)
- 数据类 (LLMRequest, LLMResponse)
- 异常类 (ProviderError)
- 混入类 (HTTPClientMixin, ModelManagerMixin)
- 基类 (BaseLLMProvider)
- 速率限制器 (RateLimiter)
- 熔断器 (CircuitBreaker)
- 重试机制 (RetryHandler) ✅ 新增

优化:
- asyncio.gather 并发批量处理 ✅
- tenacity 重试机制 ✅
- 指数退避 ✅
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, TypeVar, Callable
from dataclasses import dataclass
from enum import Enum
from collections import deque
import asyncio
import httpx
import logging
import time
import hashlib

logger = logging.getLogger(__name__)


# ============ 公共常量 ============
DEFAULT_CACHE_TTL = 3600.0           # 默认请求缓存 TTL: 1小时（秒）
DEFAULT_LONG_CACHE_TTL = 86400.0    # 长缓存 TTL: 24小时（秒）
DEFAULT_RETRY_MAX_DELAY = 30.0      # 重试最大延迟（秒）
DEFAULT_KEEPALIVE_EXPIRY = 30.0     # HTTP keepalive 过期时间（秒）
DEFAULT_LOCAL_TIMEOUT = 300.0       # 本地 LLM 请求超时（秒，5分钟）


T = TypeVar("T")


# ============ 枚举定义 ============

class ProviderType(Enum):
    """LLM 提供商类型 (2026年3月最新国产模型)"""
    QWEN = "qwen"           # 阿里通义千问
    KIMI = "kimi"           # 月之暗面 Kimi
    GLM5 = "glm5"           # 智谱 GLM
    DOUBAO = "doubao"       # 字节豆包 (新增)
    HUNYUAN = "hunyuan"     # 腾讯混元 (新增)
    DEEPSEEK = "deepseek"    # 深度求索
    CLAUDE = "claude"        # Anthropic Claude
    GEMINI = "gemini"        # Google Gemini
    OPENAI = "openai"        # OpenAI
    LOCAL = "local"          # 本地模型


# ============ 数据类 ============

@dataclass
class LLMRequest:
    """LLM 请求"""
    prompt: str                          # 提示词
    system_prompt: str = ""               # 系统提示词
    model: str = "default"                # 模型名称
    max_tokens: int = 2000               # 最大生成长度
    temperature: float = 0.7              # 温度参数
    top_p: float = 0.9                   # Top-p 参数


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str                         # 生成的文本
    model: str                           # 使用的模型
    tokens_used: int = 0                # 使用的 token 数量
    finish_reason: str = "stop"          # 结束原因
    raw_response: Optional[Dict] = None  # 原始响应
    latency_ms: float = 0.0              # 延迟（毫秒）✅ 新增
    usage: Optional[Dict[str, Any]] = None  # 用量详情 (prompt_tokens, completion_tokens, total_tokens)




# ============ 导入异常和工具类 ============

from .errors import (
    ProviderError,
    RateLimitError,
    CircuitOpenError,
)
from .retry import (
    RetryHandler,
    RateLimiter,
    CircuitState,
    CircuitBreaker,
)

class RequestCache:
    """
    请求缓存 - 基于哈希的简单缓存
    减少重复 API 调用
    """
    
    def __init__(self, max_size: int = 1000, ttl: float = DEFAULT_CACHE_TTL):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry)
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, request: LLMRequest) -> str:
        """生成缓存键"""
        content = f"{request.model}:{request.prompt[:100]}:{request.temperature}"
        return hashlib.md5(content.encode()).hexdigest()
    async def get(self, request: LLMRequest) -> Optional[LLMResponse]:
        """获取缓存的响应（通过 request 对象）"""
        key = self._make_key(request)
        return await self.get_from_key(key)

    async def get_from_key(self, key: str) -> Optional[LLMResponse]:
        """获取缓存的响应（通过缓存键）"""
        async with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.monotonic() < expiry:
                    logger.debug(f"缓存命中: {key[:8]}...")
                    self._hits += 1
                    return value
                else:
                    del self._cache[key]
        self._misses += 1
        return None

    async def set(self, request: LLMRequest, response: LLMResponse):
        """缓存响应（通过 request 对象）"""
        key = self._make_key(request)
        await self.set_from_key(key, response)

    async def set_from_key(self, key: str, response: LLMResponse):
        """缓存响应（通过缓存键）"""
        async with self._lock:
            # 清理过期项
            if len(self._cache) >= self.max_size:
                self._cleanup()
            self._cache[key] = (
                response,
                time.monotonic() + self.ttl
            )

    
    def _cleanup(self):
        """清理过期缓存"""
        now = time.monotonic()
        expired = [k for k, (_, expiry) in self._cache.items() if now >= expiry]
        for k in expired:
            del self._cache[k]
        
        # 如果还是太多，删除最老的
        if len(self._cache) >= self.max_size:
            oldest = sorted(
                self._cache.items(),
                key=lambda x: x[1][1]
            )[:len(self._cache) // 2]
            for k, _ in oldest:
                del self._cache[k]
    
    async def clear(self):
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache),
            "hit_rate": f"{hit_rate:.1f}%"
        }


# ============ 混入类 (Mixins) ============

class HTTPClientMixin:
    """HTTP客户端混入类 - 提供通用的HTTP请求功能"""

    def __init__(self, api_key: str, base_url: str, timeout: float = 60.0):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.http_client: Optional[httpx.AsyncClient] = None
        self._default_headers: Dict[str, str] = {}
        # ✅ 新增：重试处理器
        self._retry_handler = RetryHandler(
            max_attempts=3,
            base_delay=1.0,
            max_delay=DEFAULT_RETRY_MAX_DELAY
        )

    def _init_http_client(self, headers: Optional[Dict[str, str]] = None):
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
                keepalive_expiry=DEFAULT_KEEPALIVE_EXPIRY
            )
        )

    async def _close_http_client(self):
        """关闭HTTP客户端"""
        if self.http_client:
            await self.http_client.aclose()

    def _build_messages(self, request: LLMRequest) -> List[Dict[str, str]]:
        """构建消息列表"""
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        return messages

    def _parse_response(self, data: Dict[str, Any], model: str, latency_ms: float = 0) -> LLMResponse:
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
        except Exception:
            logger.debug("无法解析错误响应")
        return ProviderError(error_msg)


class ModelManagerMixin:
    """模型管理混入类 - 提供通用的模型管理功能"""

    # 子类需要定义: MODELS, DEFAULT_MODEL
    MODELS: Dict[str, Dict[str, Any]] = {}
    DEFAULT_MODEL: str = ""

    def _get_model_name(self, model: str) -> str:
        """获取模型实际名称"""
        if model == "default":
            return self.DEFAULT_MODEL
        if model in self.MODELS:
            return model
        raise ValueError(f"Unknown model: {model}")

    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return list(self.MODELS.keys())

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        return self.MODELS.get(model, {})

    def supports_vision(self, model: str) -> bool:
        """检查模型是否支持视觉"""
        model_info = self.MODELS.get(model, {})
        return model_info.get("vision", False)

    def is_reasoning_model(self, model: str) -> bool:
        """检查是否是推理模型"""
        model_info = self.MODELS.get(model, {})
        return model_info.get("reasoning", False)


# ============ 基类 ============

class BaseLLMProvider(ABC):
    """LLM 提供商抽象基类"""

    def __init__(self, api_key: str, base_url: str):
        """
        初始化提供商

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
        """
        self.api_key = api_key
        self.base_url = base_url

        # 初始化安全组件
        self._rate_limiter = RateLimiter()
        self._circuit_breaker = CircuitBreaker()

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

    async def generate_batch(
        self,
        requests: List[LLMRequest],
        max_concurrency: int = 5,
        use_cache: bool = True,
        deduplicate: bool = True,
    ) -> List[LLMResponse]:
        """
        批量生成文本 ✅ 优化：asyncio.gather 并发 + 请求缓存 + 请求去重

        Args:
            requests: LLM 请求列表
            max_concurrency: 最大并发数（防止超出 API 限制）
            use_cache: 是否启用缓存（默认启用，重复 prompt 直接返回）
            deduplicate: 是否对重复请求去重（相同 prompt+model+temperature 只调用一次）

        Returns:
            响应列表（与输入顺序一致）
        """
        if deduplicate:
            # 去重：记录每个唯一请求的首次出现索引
            seen: Dict[str, int] = {}
            unique_requests: List[LLMRequest] = []
            index_map: List[int] = []  # 结果列表中的位置映射

            for req in requests:
                key = self._make_cache_key(req)
                if key not in seen:
                    seen[key] = len(unique_requests)
                    unique_requests.append(req)
                index_map.append(seen[key])

            # 对去重后的请求执行批量生成
            if use_cache:
                unique_results = await gather_with_concurrency(
                    max_concurrency,
                    *[self.generate_cached(req) for req in unique_requests]
                )
            else:
                unique_results = await gather_with_concurrency(
                    max_concurrency,
                    *[self.generate(req) for req in unique_requests]
                )

            # 将结果映射回原始顺序
            return [unique_results[idx] if idx < len(unique_results) else None for idx in index_map]

        if use_cache:
            results = await gather_with_concurrency(
                max_concurrency,
                *[self.generate_cached(req) for req in requests]
            )
        else:
            results = await gather_with_concurrency(
                max_concurrency,
                *[self.generate(req) for req in requests]
            )
        return [
            r if isinstance(r, LLMResponse) else None
            for r in results
        ]


    async def close(self):
        """关闭连接"""
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.base_url}>"


# ============ 工具函数 ============

async def gather_with_concurrency(
    n: int,
    *tasks,
    return_exceptions: bool = True
) -> List[Any]:
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
        return_exceptions=return_exceptions
    )


__all__ = [
    "ProviderType",
    "LLMRequest",
    "LLMResponse",
    "ProviderError",
    "RateLimitError",
    "CircuitOpenError",
    "RateLimiter",
    "CircuitBreaker",
    "RequestCache",
    "RetryHandler",
    "HTTPClientMixin",
    "ModelManagerMixin",
    "BaseLLMProvider",
    "gather_with_concurrency",  # ✅ 新增
]
