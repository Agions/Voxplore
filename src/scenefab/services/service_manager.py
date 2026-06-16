#!/usr/bin/env python3

"""统一服务管理器（兼容层）。

.. deprecated::
    AI 服务的权威实现位于 :mod:`scenefab.services.ai.manager`。
    本模块仅保留旧导入路径，避免应用层维护两套 AI 管理逻辑。
    新代码请直接使用 ``scenefab.services.ai.manager.get_ai_service()``。

P2 变更：移除了未被任何调用方使用的 ``ServiceManager`` 注册表与
``AIServiceManagerCompat`` 二次注册层。``get_ai_service_manager`` 现在直接
返回 :mod:`scenefab.services.ai.manager` 的全局单例。
"""

from __future__ import annotations

import warnings

# 权威 ServiceStatus / ServiceHealth
from scenefab.services.ai.base import ServiceHealth, ServiceStatus
from scenefab.services.ai.manager import AIServiceManager, get_ai_service

__all__ = [
    "ServiceStatus",
    "ServiceHealth",
    "AIServiceManager",
    "get_ai_service_manager",
]


def get_ai_service_manager() -> AIServiceManager:
    """获取全局 AI 服务管理器单例（已废弃）。

    .. deprecated::
        请改用 ``scenefab.services.ai.manager.get_ai_service()``。
    """
    warnings.warn(
        "scenefab.services.service_manager.get_ai_service_manager is deprecated, "
        "use scenefab.services.ai.manager.get_ai_service instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_ai_service()
