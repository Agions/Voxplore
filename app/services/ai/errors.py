#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM 提供商异常定义

定义 LLM 服务相关的自定义异常类型。
"""


class ProviderError(Exception):
    """LLM 提供商错误基类"""
    pass


class RateLimitError(ProviderError):
    """速率限制错误 - API 调用频率超出限制"""
    pass


class CircuitOpenError(ProviderError):
    """熔断器开启错误 - 服务暂时不可用"""
    pass


class AuthenticationError(ProviderError):
    """认证错误 - API 密钥无效或已过期"""
    pass


class ValidationError(ProviderError):
    """验证错误 - 请求参数无效"""
    pass


class TimeoutError(ProviderError):
    """超时错误 - 请求响应超时"""
    pass


class ModelNotFoundError(ProviderError):
    """模型未找到错误 - 请求的模型不存在"""
    pass


class QuotaExceededError(ProviderError):
    """配额超出错误 - API 使用配额已用尽"""
    pass


__all__ = [
    "ProviderError",
    "RateLimitError",
    "CircuitOpenError",
    "AuthenticationError",
    "ValidationError",
    "TimeoutError",
    "ModelNotFoundError",
    "QuotaExceededError",
]
