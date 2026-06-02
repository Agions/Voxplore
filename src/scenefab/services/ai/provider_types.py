#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Provider 类型定义
包含枚举、数据类和常量，被所有 provider 实现共享
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, TypeVar

T = TypeVar("T")

class ProviderType(Enum):
    """LLM 提供商类型 (国产模型)"""
    QWEN = "qwen"           # 阿里通义千问
    KIMI = "kimi"           # 月之暗面 Kimi
    GLM5 = "glm5"           # 智谱 GLM
    DOUBAO = "doubao"       # 字节豆包 (新增)
    HUNYUAN = "hunyuan"     # 腾讯混元 (新增)
    DEEPSEEK = "deepseek"    # 深度求索
    CLAUDE = "claude"        # Anthropic Claude
    GEMINI = "gemini"        # Google Gemini
    OPENAI = "openai"        # OpenAI
    LOCAL = "local"          # 本地模型



# ============ 数据类 ============

@dataclass
class LLMRequest:
    """LLM 请求"""
    prompt: str                          # 提示词
    system_prompt: str = ""               # 系统提示词
    model: str = "default"                # 模型名称
    max_tokens: int = 2000               # 最大生成长度
    temperature: float = 0.7              # 温度参数
    top_p: float = 0.9                   # Top-p 参数




# ============ LLMResponse ============

@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str                         # 生成的文本
    model: str                           # 使用的模型
    tokens_used: int = 0                # 使用的 token 数量
    finish_reason: str = "stop"          # 结束原因
    raw_response: Optional[Dict] = None  # 原始响应
    latency_ms: float = 0.0              # 延迟（毫秒）✅ 新增
    usage: Optional[Dict[str, Any]] = None  # 用量详情 (prompt_tokens, completion_tokens, total_tokens)

