"""
AI 服务管理器兼容层

.. deprecated::
    本模块保留用于向后兼容，新代码请使用 scenefab.services.ai.manager
    中的 AIServiceManager V2 实现。
"""

import warnings

warnings.warn(
    "scenefab.services.ai_service_manager is deprecated, "
    "use scenefab.services.ai.manager.AIServiceManager instead",
    DeprecationWarning,
    stacklevel=2,
)


from scenefab.services.ai.base import ServiceHealth, ServiceStatus
from scenefab.services.ai.manager import AIServiceManager

# 重新导出以保持向后兼容
__all__ = [
    "ServiceStatus",
    "ServiceHealth",
    "AIServiceManager",
]


def get_ai_service_manager() -> AIServiceManager:
    """获取 AI 服务管理器实例（已废弃，请使用 scenefab.services.ai.manager）

    保留此函数仅为向后兼容，建议直接使用 scenefab.services.ai.manager 中的实现。
    """
    from scenefab.services.ai.manager import ai_service_manager

    return ai_service_manager
