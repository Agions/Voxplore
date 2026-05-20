#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Service Manager 优化版本
改进点：
1. 真实健康检查机制
2. 连接池和请求限流
3. 自动重试与退避
4. 统计和监控
5. 多 Provider 智能路由
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any, List
from enum import Enum
import threading
import time
import logging
from collections import deque
from functools import wraps

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """服务状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    MAINTENANCE = "maintenance"


class RateLimitExceeded(Exception):
    """超过速率限制"""
    def __init__(self, provider: str, retry_after: float):
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded for {provider}, retry after {retry_after}s")


@dataclass
class ServiceHealth:
    """服务健康状态"""
    service_name: str
    status: ServiceStatus
    last_check: float
    response_time: float = 0.0
    error_message: str = ""
    request_count: int = 0
    error_count: int = 0
    success_count: int = 0


@dataclass
class UsageStats:
    """使用统计"""
    provider: str
    requests: int = 0
    errors: int = 0
    total_response_time: float = 0.0
    rate_limit_hits: int = 0
    
    @property
    def avg_response_time(self) -> float:
        return self.total_response_time / max(1, self.requests)
    
    @property
    def error_rate(self) -> float:
        return self.errors / max(1, self.requests)


class RateLimiter:
    """令牌桶限流器"""
    
    def __init__(self, requests_per_second: float = 10.0, burst_size: int = 20):
        """
        Args:
            requests_per_second: 每秒请求数
            burst_size: 突发容量
        """
        self.rate = requests_per_second
        self.burst = burst_size
        self.tokens = burst_size
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def acquire(self, timeout: float = 30.0) -> bool:
        """
        获取令牌
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            是否获取成功
        """
        start = time.time()
        
        while True:
            with self.lock:
                now = time.time()
                # 补充令牌
                elapsed = now - self.last_update
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
                self.last_update = now
                
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return True
            
            if time.time() - start >= timeout:
                return False
            
            time.sleep(0.01)  # 避免忙等待


class CircuitBreaker:
    """
    断路器模式
    防止连续失败导致的服务雪崩
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_requests: int = 3,
    ):
        """
        Args:
            failure_threshold: 失败次数阈值（触发断路）
            recovery_timeout: 恢复超时（秒）
            half_open_requests: 半开状态下允许的测试请求数
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open
        self.half_open_allowed = 0
        self.lock = threading.Lock()
    
    def can_execute(self) -> bool:
        """检查是否可以执行请求"""
        with self.lock:
            if self.state == "closed":
                return True
            
            if self.state == "open":
                # 检查是否超时恢复
                if (self.last_failure_time and 
                    time.time() - self.last_failure_time >= self.recovery_timeout):
                    self.state = "half_open"
                    self.half_open_allowed = self.half_open_requests
                    logger.info("Circuit breaker: open -> half_open")
                    return True
                return False
            
            if self.state == "half_open":
                if self.half_open_allowed > 0:
                    self.half_open_allowed -= 1
                    return True
                return False
            
            return False
    
    def record_success(self):
        """记录成功"""
        with self.lock:
            self.failure_count = 0
            self.state = "closed"
    
    def record_failure(self):
        """记录失败"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"Circuit breaker: failure_count={self.failure_count}, opening")


class RetryPolicy:
    """重试策略"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        retryable_errors: tuple = (ConnectionError, TimeoutError),
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.retryable_errors = retryable_errors
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """执行带重试的函数"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            
            except self.retryable_errors as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = min(
                        self.base_delay * (self.backoff_factor ** attempt),
                        self.max_delay
                    )
                    logger.warning(
                        f"Retry {attempt + 1}/{self.max_retries} after {delay:.1f}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All retries exhausted: {e}")
        
        raise last_exception


@dataclass
class ProviderConfig:
    """Provider 配置"""
    name: str
    enabled: bool = True
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    max_tokens: int = 8000
    temperature: float = 0.7
    requests_per_second: float = 10.0
    burst_size: int = 20
    health_check_interval: float = 60.0
    health_check_url: str = ""


class AIServiceManager:
    """
    优化后的 AI 服务管理器
    特性：
    - 真实健康检查
    - 速率限制
    - 断路器保护
    - 自动重试
    - 统计监控
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._providers: Dict[str, ProviderConfig] = {}
        self._service_health: Dict[str, ServiceHealth] = {}
        self._usage_stats: Dict[str, UsageStats] = {}
        self._rate_limiters: Dict[str, RateLimiter] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._retry_policies: Dict[str, RetryPolicy] = {}
        
        self._health_check_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        
        # 信号（占位符）
        self.service_health_updated = None
        self.stats_updated = None
    
    def register_provider(self, config: ProviderConfig) -> None:
        """注册 Provider"""
        with self._lock:
            self._providers[config.name] = config
            self._rate_limiters[config.name] = RateLimiter(
                requests_per_second=config.requests_per_second,
                burst_size=config.burst_size
            )
            self._circuit_breakers[config.name] = CircuitBreaker()
            self._retry_policies[config.name] = RetryPolicy()
            self._usage_stats[config.name] = UsageStats(provider=config.name)
            
            self._service_health[config.name] = ServiceHealth(
                service_name=config.name,
                status=ServiceStatus.INACTIVE,
                last_check=0.0
            )
            
            logger.info(f"Registered provider: {config.name}")
    
    def register_service(self, name: str, service: Any) -> None:
        """注册服务"""
        self._services[name] = service
    
    def get_service(self, name: str) -> Optional[Any]:
        """获取服务"""
        return self._services.get(name)
    
    def get_all_services(self) -> Dict[str, Any]:
        """获取所有服务"""
        return self._services.copy()
    
    def get_service_health(self, service_name: str) -> Optional[ServiceHealth]:
        """获取服务健康状态"""
        return self._service_health.get(service_name)
    
    def get_usage_stats(self, service_name: str) -> UsageStats:
        """获取使用统计"""
        return self._usage_stats.get(
            service_name, 
            UsageStats(provider=service_name)
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """获取摘要"""
        with self._lock:
            active = sum(
                1 for h in self._service_health.values()
                if h.status == ServiceStatus.ACTIVE
            )
            
            total_requests = sum(s.requests for s in self._usage_stats.values())
            total_errors = sum(s.errors for s in self._usage_stats.values())
            
            return {
                "total_providers": len(self._providers),
                "active_providers": active,
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": total_errors / max(1, total_requests),
                "providers": {
                    name: {
                        "status": h.status.value,
                        "response_time": h.response_time,
                        "requests": stats.requests,
                        "error_rate": stats.error_rate,
                    }
                    for name, (h, stats) in self._iter_provider_data()
                }
            }
    
    def _iter_provider_data(self):
        """迭代 provider 数据"""
        for name in self._providers:
            health = self._service_health.get(name)
            stats = self._usage_stats.get(name)
            if health and stats:
                yield name, (health, stats)
    
    def call_with_protection(
        self,
        provider_name: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        带保护地调用 Provider（限流 + 断路器 + 重试）
        
        Args:
            provider_name: Provider 名称
            func: 要执行的函数
            *args, **kwargs: 函数参数
            
        Returns:
            函数返回值
            
        Raises:
            RateLimitExceeded: 超过速率限制
            Exception: 其他错误
        """
        if provider_name not in self._providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        config = self._providers[provider_name]
        if not config.enabled:
            raise ValueError(f"Provider disabled: {provider_name}")
        
        # 1. 限流
        limiter = self._rate_limiters[provider_name]
        if not limiter.acquire(timeout=30.0):
            raise RateLimitExceeded(provider_name, retry_after=1.0 / config.requests_per_second)
        
        # 2. 断路器检查
        breaker = self._circuit_breakers[provider_name]
        if not breaker.can_execute():
            raise Exception(f"Circuit breaker open for {provider_name}")
        
        # 3. 执行（带统计）
        start_time = time.time()
        stats = self._usage_stats[provider_name]
        
        try:
            retry_policy = self._retry_policies[provider_name]
            result = retry_policy.execute(func, *args, **kwargs)
            
            # 记录成功
            breaker.record_success()
            stats.requests += 1
            stats.success_count += 1
            stats.total_response_time += time.time() - start_time
            
            self._update_health(provider_name, ServiceStatus.ACTIVE, time.time() - start_time)
            
            return result
            
        except RateLimitExceeded:
            stats.rate_limit_hits += 1
            raise
            
        except Exception as e:
            # 记录失败
            breaker.record_failure()
            stats.errors += 1
            stats.error_count += 1
            stats.total_response_time += time.time() - start_time
            
            self._update_health(
                provider_name, 
                ServiceStatus.ERROR, 
                time.time() - start_time,
                error_message=str(e)
            )
            
            raise
    
    def _update_health(
        self,
        provider_name: str,
        status: ServiceStatus,
        response_time: float,
        error_message: str = ""
    ):
        """更新健康状态"""
        if provider_name in self._service_health:
            health = self._service_health[provider_name]
            health.status = status
            health.last_check = time.time()
            health.response_time = response_time
            health.error_message = error_message
            health.request_count += 1
        
        if self.service_health_updated:
            self.service_health_updated(provider_name, status)
    
    def start_health_checker(self, interval: float = 60.0):
        """启动健康检查线程"""
        if self._running:
            return
        
        self._running = True
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            args=(interval,),
            daemon=True
        )
        self._health_check_thread.start()
        logger.info("Health checker started")
    
    def stop_health_checker(self):
        """停止健康检查线程"""
        self._running = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5.0)
        logger.info("Health checker stopped")
    
    def _health_check_loop(self, interval: float):
        """健康检查循环"""
        while self._running:
            try:
                self._check_all_providers()
            except Exception as e:
                logger.warning(f"Health check failed: {e}")
            
            time.sleep(interval)
    
    def _check_all_providers(self):
        """检查所有 Provider"""
        for name, config in self._providers.items():
            if not config.enabled:
                continue
            
            try:
                self._health_check_provider(name, config)
            except Exception as e:
                logger.warning(f"Health check failed for {name}: {e}")
                self._update_health(name, ServiceStatus.ERROR, 0.0, str(e))
    
    def _health_check_provider(self, name: str, config: ProviderConfig):
        """检查单个 Provider"""
        import requests
        
        start = time.time()
        
        try:
            # 使用配置的 health_check_url 或 base_url
            check_url = config.health_check_url or config.base_url
            
            response = requests.get(
                check_url + "/health" if not check_url.endswith("/") else check_url + "health",
                timeout=5.0,
                headers={"Authorization": f"Bearer {config.api_key}"} if config.api_key else {}
            )
            
            elapsed = time.time() - start
            
            if response.status_code == 200:
                self._update_health(name, ServiceStatus.ACTIVE, elapsed)
            else:
                self._update_health(name, ServiceStatus.ERROR, elapsed, f"HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            self._update_health(name, ServiceStatus.RATE_LIMITED, time.time() - start, "Timeout")
        except requests.exceptions.ConnectionError:
            self._update_health(name, ServiceStatus.ERROR, time.time() - start, "Connection error")
        except Exception as e:
            self._update_health(name, ServiceStatus.ERROR, time.time() - start, str(e))
    
    def get_best_provider(self, capability: str = "chat") -> Optional[str]:
        """
        获取最佳 Provider（基于健康状态和响应时间）
        
        Args:
            capability: 所需能力（如 "chat", "vision"）
            
        Returns:
            最佳 provider 名称
        """
        candidates = []
        
        for name, health in self._service_health.items():
            if health.status == ServiceStatus.ACTIVE:
                stats = self._usage_stats.get(name)
                if stats:
                    # 综合评分：响应时间快 + 错误率低
                    score = (
                        1.0 / (stats.avg_response_time + 0.1) * 0.7 +
                        (1.0 - stats.error_rate) * 0.3
                    )
                    candidates.append((name, score))
        
        if not candidates:
            return None
        
        # 返回评分最高的
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]


# 全局实例
_service_manager: Optional[AIServiceManager] = None
_manager_lock = threading.Lock()


def get_ai_service_manager() -> AIServiceManager:
    """获取 AI 服务管理器实例"""
    global _service_manager
    
    if _service_manager is None:
        with _manager_lock:
            if _service_manager is None:
                _service_manager = AIServiceManager()
    
    return _service_manager


__all__ = [
    "AIServiceManager",
    "ServiceStatus",
    "ServiceHealth",
    "UsageStats",
    "RateLimiter",
    "CircuitBreaker",
    "RetryPolicy",
    "ProviderConfig",
    "RateLimitExceeded",
    "get_ai_service_manager",
]
