#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Provider 异常兼容模块 ⚠️ 已废弃

所有异常已统一迁移至 app.core.exceptions。
此文件仅作兼容层，未来版本移除。

迁移指南:
    # 旧 (废弃) → from app.services.ai.errors import ProviderError
    # 新 (推荐) → from app.core.exceptions import ProviderError
"""

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
