"""
AI 服务管理器兼容层

此模块提供与旧 ai_service_manager 的兼容性接口
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class ServiceStatus(Enum):
    """服务状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class ServiceHealth:
    """服务健康状态"""
    service_name: str
    status: ServiceStatus
    last_check: float
    response_time: float = 0.0
    error_message: str = ""


class AIServiceManager:
    """
    AI 服务管理器

    提供统一的 AI 服务管理和健康检查接口
    """

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._service_health: Dict[str, ServiceHealth] = {}
        self.service_health_updated = None  # Signal placeholder
        self.stats_updated = None  # Signal placeholder

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

    def get_usage_stats(self, service_name: str) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            "requests": 0,
            "errors": 0,
            "avg_response_time": 0.0,
        }

    def get_summary(self) -> Dict[str, Any]:
        """获取摘要"""
        return {
            "total_services": len(self._services),
            "active_services": sum(
                1 for h in self._service_health.values()
                if h.status == ServiceStatus.ACTIVE
            ),
        }


# 创建全局实例
_service_manager: Optional[AIServiceManager] = None


def get_ai_service_manager() -> AIServiceManager:
    """获取 AI 服务管理器实例"""
    global _service_manager
    if _service_manager is None:
        _service_manager = AIServiceManager()
    return _service_manager
