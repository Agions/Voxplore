"""
服务容器

简化版的服务容器，提供基本的依赖注入功能
"""

from typing import Dict, Any, Optional, Type


class ServiceContainer:
    """简单的服务容器"""

    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._services_by_name: Dict[str, Any] = {}

    def register(self, service_type: Type, instance: Any) -> None:
        """注册服务"""
        self._services[service_type] = instance

    def register_by_name(self, name: str, instance: Any) -> None:
        """按名称注册服务"""
        self._services_by_name[name] = instance

    def get(self, service_type: Type) -> Optional[Any]:
        """获取服务"""
        return self._services.get(service_type)

    def get_by_name(self, name: str) -> Optional[Any]:
        """按名称获取服务"""
        return self._services_by_name.get(name)

    def has(self, service_type: Type) -> bool:
        """检查服务是否存在"""
        return service_type in self._services

    def has_by_name(self, name: str) -> bool:
        """按名称检查服务是否存在"""
        return name in self._services_by_name

    def remove(self, service_type: Type) -> None:
        """移除服务"""
        self._services.pop(service_type, None)

    def remove_by_name(self, name: str) -> None:
        """按名称移除服务"""
        self._services_by_name.pop(name, None)

    def clear(self) -> None:
        """清空所有服务"""
        self._services.clear()
        self._services_by_name.clear()


__all__ = ["ServiceContainer"]
