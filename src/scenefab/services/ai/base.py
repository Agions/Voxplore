"""AI 服务状态定义。"""

from dataclasses import dataclass
from enum import Enum


class ServiceStatus(Enum):
    """服务状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    RATE_LIMITED = "rate_limited"


@dataclass(slots=True)
class ServiceHealth:
    """服务健康状态"""

    name: str
    status: ServiceStatus
    last_check: float
    response_time: float = 0.0
    error_message: str = ""


__all__ = ["ServiceStatus", "ServiceHealth"]
