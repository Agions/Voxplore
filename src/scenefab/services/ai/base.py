"""
AI 服务基类
提供公共接口、重试逻辑、错误处理、统计收集
"""
import time
import logging
from typing import Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """服务状态（统一权威定义）

    涵盖所有场景：AI 服务、通用服务。
    """
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    RATE_LIMITED = "rate_limited"


@dataclass(slots=True)
class ServiceHealth:
    name: str
    status: ServiceStatus
    last_check: float
    response_time: float = 0.0
    error_message: str = ""


class BaseAIService:
    """
    AI 服务基类
    提供公共的重试、错误处理和统计逻辑
    """

    def __init__(self, name: str, config: dict[str, Any]):
        self.name = config.get("name", name)
        self.enabled = config.get("enabled", False)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "")
        self.model = config.get("model", "")
        self._stats = {
            "requests": 0,
            "errors": 0,
            "total_time": 0.0,
        }

    def _record_stats(self, response_time: float, error: bool = False):
        """记录请求统计"""
        self._stats["requests"] += 1
        if error:
            self._stats["errors"] += 1
        self._stats["total_time"] += response_time

    def _handle_error(self, error: Exception, context: str = ""):
        """统一错误处理"""
        logger.error(f"{context} failed: {error}")
        self._stats["errors"] += 1

    def _retry(
        self,
        func,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 8.0,
        *args,
        **kwargs
    ) -> Any:
        """
        带指数退避的重试装饰器
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = min(base_delay * (2 ** attempt), max_delay)
                    time.sleep(wait_time)
        raise last_error

    def get_health(self) -> ServiceHealth:
        """获取服务健康状态"""
        return ServiceHealth(
            name=self.name,
            status=ServiceStatus.ACTIVE if self.enabled else ServiceStatus.INACTIVE,
            last_check=time.time(),
            response_time=self._stats["total_time"] / max(self._stats["requests"], 1),
        )


__all__ = ["BaseAIService", "ServiceStatus", "ServiceHealth"]