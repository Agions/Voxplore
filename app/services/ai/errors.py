#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Provider 异常兼容模块 ⚠️ 已废弃

此模块已废弃。所有 Provider/RateLimit/CircuitOpen 等异常
已统一迁移至 app.core.exceptions。

废弃原因:
    为统一错误层次，将这些异常合并到 app.core.exceptions 的
    VoxploreError 体系，废弃独立定义。

迁移指南:
    # 旧 (废弃)
    from app.services.ai.errors import ProviderError, RateLimitError

    # 新 (推荐)
    from app.core.exceptions import ProviderError, RateLimitError

此文件将在未来版本中移除。
"""

# 从新的统一位置重导出，避免现有代码的导入崩溃

# === 废弃迁移：统一从 app.core.exceptions 导入 ===
# 此文件历史遗留，仅作兼容层，未来版本移除
from app.core.exceptions import (
    ProviderError,
    RateLimitError,
    CircuitOpenError,
    LLMError,
    NetworkError,
    ConfigError,
    ServiceError,
    ServiceNotFoundError,
    ServiceDependencyError,
    ServiceInitializationError,
    ServiceTimeoutError,
)

__all__ = [
    "ProviderError",
    "RateLimitError",
    "CircuitOpenError",
    "LLMError",
    "NetworkError",
    "ConfigError",
    "ServiceError",
    "ServiceNotFoundError",
    "ServiceDependencyError",
    "ServiceInitializationError",
    "ServiceTimeoutError",
]
