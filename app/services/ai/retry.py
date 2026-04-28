#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM 请求重试机制

提供重试处理、速率限制和熔断器功能。
"""

import asyncio
import logging
import random
from typing import Any, Callable, Optional
from datetime import datetime
from enum import Enum

from .errors import CircuitOpenError


logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略"""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"


class RetryHandler:
    """
    重试处理器

    支持指数退避、线性退避和恒定延迟策略。
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        jitter: bool = True,
    ):
        """
        初始化重试处理器

        Args:
            max_attempts: 最大尝试次数
            base_delay: 基础延迟（秒）
            max_delay: 最大延迟（秒）
            strategy: 重试策略
            jitter: 是否添加随机抖动
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.jitter = jitter

    def _calculate_delay(self, attempt: int) -> float:
        """计算延迟时间"""
        if self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (2 ** (attempt - 1))
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * attempt
        else:  # CONSTANT
            delay = self.base_delay

        delay = min(delay, self.max_delay)

        if self.jitter:
            delay *= 0.5 + random.random() * 0.5

        return delay

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行带重试的函数

        Args:
            func: 要执行的异步函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            函数返回值

        Raises:
            最后一次失败的异常
        """
        last_exception = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt}/{self.max_attempts} failed: {e}")

                if attempt < self.max_attempts:
                    delay = self._calculate_delay(attempt)
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_attempts} attempts failed")

        raise last_exception


class RateLimiter:
    """
    速率限制器

    实现令牌桶算法的异步速率限制。
    """

    def __init__(self, rate: float, capacity: int):
        """
        初始化速率限制器

        Args:
            rate: 每秒生成的令牌数
            capacity: 令牌桶容量
        """
        self.rate = rate
        self.capacity = capacity
        self._tokens = capacity
        self._last_update = datetime.now()
        self._lock = asyncio.Lock()

    async def acquire(self, timeout: float = 30.0) -> bool:
        """
        获取令牌

        Args:
            timeout: 超时时间（秒）

        Returns:
            是否成功获取令牌

        Raises:
            asyncio.TimeoutError: 获取令牌超时
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            async with self._lock:
                now = datetime.now()
                elapsed = (now - self._last_update).total_seconds()
                self._tokens = min(
                    self.capacity,
                    self._tokens + elapsed * self.rate
                )
                self._last_update = now

                if self._tokens >= 1:
                    self._tokens -= 1
                    return True

            elapsed = asyncio.get_event_loop().time() - start_time
            wait_time = (1 - self._tokens) / self.rate
            if elapsed + wait_time > timeout:
                raise asyncio.TimeoutError("Rate limiter acquisition timeout")

            await asyncio.sleep(wait_time)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态，请求正常通过
    OPEN = "open"          # 熔断状态，请求被拒绝
    HALF_OPEN = "half_open"  # 半开状态，允许部分请求通过


class CircuitBreaker:
    """
    熔断器

    防止级联故障的熔断器实现。
    当失败率达到阈值时打开熔断器，拒绝后续请求。
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        """
        初始化熔断器

        Args:
            failure_threshold: 打开熔断器的连续失败次数
            recovery_timeout: 尝试恢复的时间（秒）
            success_threshold: 半开状态下恢复需要的成功次数
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        return self._state

    async def call(self, func, *args, **kwargs):
        """
        通过熔断器执行函数

        Args:
            func: 要执行的异步函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            函数返回值

        Raises:
            CircuitOpenError: 熔断器处于打开状态
        """
        async with self._lock:
            await self._check_state_transition()

            if self._state == CircuitState.OPEN:
                raise CircuitOpenError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception:
            await self._on_failure()
            raise

    async def _check_state_transition(self) -> None:
        """检查状态转换"""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0

    async def _on_success(self) -> None:
        """处理成功调用"""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    logger.info("Circuit breaker transitioning to CLOSED")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def _on_failure(self) -> None:
        """处理失败调用"""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()

            if self._state == CircuitState.HALF_OPEN or self._failure_count >= self.failure_threshold:
                logger.warning("Circuit breaker transitioning to OPEN")
                self._state = CircuitState.OPEN


__all__ = [
    "RetryStrategy",
    "RetryHandler",
    "RateLimiter",
    "CircuitState",
    "CircuitBreaker",
]
