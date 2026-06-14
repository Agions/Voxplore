"""v1 服务容器兼容层。

权威实现位于 :mod:`scenefab.core.di_container`。本模块保留旧导入路径，
避免应用层和第三方代码同时维护两套 DI 逻辑。
"""

from __future__ import annotations

from scenefab.core.di_container import DIContainer, ServiceLifetime


class ServiceContainer(DIContainer):
    """兼容旧 API 的 DIContainer 包装。"""

    def __init__(self):
        super().__init__(name="legacy")
        self._services_by_name = self._by_name


service_container = ServiceContainer()

__all__ = ["ServiceContainer", "ServiceLifetime", "service_container"]
