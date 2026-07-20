"""
统一重试工具

提供异步/同步重试装饰器，使用指数退避 + 抖动。
LLM Provider 使用的 RetryHandler/RateLimiter/CircuitBreaker 保留在 services/ai/retry.py。
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def compute_delay_with_jitter(
    attempt: int, base_delay: float, backoff: float, max_delay: float | None = None
) -> float:
    """计算带抖动的指数退避延迟"""
    delay = base_delay * (backoff**attempt)
    if max_delay is not None:
        delay = min(delay, max_delay)
    return delay * (0.5 + random.random() * 0.5)


async def retry_async(
    func: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """
    异步重试（指数退避 + 抖动）。

    Args:
        func: 异步函数（无参数，调用方用 lambda 包装）
        max_attempts: 最大尝试次数
        delay: 初始延迟秒数
        backoff: 退避倍数
        exceptions: 触发重试的异常类型

    Returns:
        函数返回值

    Raises:
        最后一次尝试的异常
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return await func()
        except exceptions as e:
            if attempt == max_attempts:
                logger.error(f"Retry failed after {max_attempts} attempts: {e}")
                raise
            wait = compute_delay_with_jitter(attempt - 1, delay, backoff)
            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed: {e}, retrying in {wait:.1f}s"
            )
            await asyncio.sleep(wait)
    raise RuntimeError("unreachable")  # pragma: no cover


def retry_sync(
    func: Callable[..., T],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    *args,
    **kwargs,
) -> T:
    """
    同步重试（指数退避 + 抖动）。

    Args:
        func: 同步函数
        max_attempts: 最大尝试次数
        delay: 初始延迟秒数
        backoff: 退避倍数
        exceptions: 触发重试的异常类型

    Returns:
        函数返回值
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            if attempt == max_attempts:
                logger.error(f"Retry failed after {max_attempts} attempts: {e}")
                raise
            wait = compute_delay_with_jitter(attempt - 1, delay, backoff)
            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed: {e}, retrying in {wait:.1f}s"
            )
            time.sleep(wait)
    raise RuntimeError("unreachable")  # pragma: no cover


def async_retry_decorator(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: tuple = (Exception,),
):
    """异步重试装饰器（用于函数定义处）"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    if attempt < max_attempts - 1:
                        delay = compute_delay_with_jitter(attempt, base_delay, 2.0)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                            f"{delay:.1f}s later retry..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} finally failed: {e}")
                        raise

        return wrapper

    return decorator


__all__ = [
    "retry_async",
    "retry_sync",
    "async_retry_decorator",
    "compute_delay_with_jitter",
]
