#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Provider 标准化 Pydantic 模型

提供跨所有 Provider 的统一请求/响应接口，消除重复代码。
与现有 dataclass (LLMRequest/LLMResponse) 兼容，作为新一代标准化接口。

模型:
- ChatMessage    - 消息单元 (role + content)
- UsageInfo      - Token 用量统计
- ChatRequest    - 聊天请求
- ChatResponse   - 聊天响应
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """
    标准化消息单元

    统一 OpenAI/Claude/Gemini 等各 Provider 的消息格式。
    """
    role: Literal["system", "user", "assistant", "tool"] = "user"
    content: str = ""

    # 可选扩展字段
    name: Optional[str] = None           # user name (某些 API 支持)
    tool_calls: Optional[List[Dict]] = None  # function/tool calls
    tool_call_id: Optional[str] = None   # tool call response

    def to_dict(self) -> Dict[str, Any]:
        """转为字典（适配 OpenAI 格式）"""
        result = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        """从字典创建"""
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            name=data.get("name"),
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id"),
        )


class UsageInfo(BaseModel):
    """
    Token 用量统计

    统一各 Provider 的 usage 格式。
    """
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # 扩展字段（Provider 特有）
    extra: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_openai(cls, data: Dict[str, Any]) -> "UsageInfo":
        """从 OpenAI 格式 usage 创建"""
        return cls(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            extra={k: v for k, v in data.items()
                   if k not in ("prompt_tokens", "completion_tokens", "total_tokens")},
        )

    @classmethod
    def from_claude(cls, data: Dict[str, Any]) -> "UsageInfo":
        """从 Claude 格式 usage 创建"""
        return cls(
            prompt_tokens=data.get("input_tokens", 0),
            completion_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("input_tokens", 0) + data.get("output_tokens", 0),
            extra={k: v for k, v in data.items()
                   if k not in ("input_tokens", "output_tokens")},
        )

    @classmethod
    def from_gemini(cls, data: Dict[str, Any]) -> "UsageInfo":
        """从 Gemini 格式 usage 创建"""
        return cls(
            prompt_tokens=data.get("promptTokenCount", 0),
            completion_tokens=data.get("candidatesTokenCount", 0),
            total_tokens=data.get("totalTokenCount", 0),
            extra={k: v for k, v in data.items()
                   if k not in ("promptTokenCount", "candidatesTokenCount", "totalTokenCount")},
        )

    @classmethod
    def from_hunyuan(cls, data: Dict[str, Any]) -> "UsageInfo":
        """从腾讯混元格式 usage 创建"""
        return cls(
            prompt_tokens=data.get("PromptTokens", 0),
            completion_tokens=data.get("CompletionTokens", 0),
            total_tokens=data.get("TotalTokens", 0),
            extra={k: v for k, v in data.items()
                   if k not in ("PromptTokens", "CompletionTokens", "TotalTokens")},
        )

    def to_dict(self) -> Dict[str, Any]:
        """转为标准字典"""
        result = {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }
        result.update(self.extra)
        return result


class ChatRequest(BaseModel):
    """
    标准化聊天请求

    统一各 Provider 的请求格式。
    """
    messages: List[ChatMessage] = Field(default_factory=list)
    model: str = "default"
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 0.9
    streaming: bool = False
    stop: Optional[List[str]] = None       # 停止词
    tools: Optional[List[Dict]] = None      # function calling
    tool_choice: Optional[str] = None       # auto/none

    # 扩展参数
    extra: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_llm_request(cls, req: "LLMRequest") -> "ChatRequest":
        """从现有 LLMRequest (dataclass) 转换"""
        from .base_llm_provider import LLMRequest as LLMReq

        messages = []
        if req.system_prompt:
            messages.append(ChatMessage(role="system", content=req.system_prompt))
        if isinstance(req.prompt, str):
            messages.append(ChatMessage(role="user", content=req.prompt))
        elif isinstance(req.prompt, list):
            for msg in req.prompt:
                if isinstance(msg, dict):
                    messages.append(ChatMessage(
                        role=msg.get("role", "user"),
                        content=msg.get("content", ""),
                    ))

        return cls(
            messages=messages,
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            top_p=req.top_p,
        )

    def to_openai_dict(self) -> Dict[str, Any]:
        """转为 OpenAI API 格式"""
        result = {
            "model": self.model,
            "messages": [m.to_dict() for m in self.messages],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
        }
        if self.stop:
            result["stop"] = self.stop
        if self.tools:
            result["tools"] = self.tools
        if self.tool_choice:
            result["tool_choice"] = self.tool_choice
        result.update(self.extra)
        return result


class ChatResponse(BaseModel):
    """
    标准化聊天响应

    统一各 Provider 的响应格式。
    """
    content: str = ""
    model: str = ""
    usage: UsageInfo = Field(default_factory=UsageInfo)
    finish_reason: str = "stop"
    raw_response: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0

    @classmethod
    def from_llm_response(cls, resp: "LLMResponse") -> "ChatResponse":
        """从现有 LLMResponse (dataclass) 转换"""
        from .base_llm_provider import LLMResponse as LLMResp

        usage = UsageInfo()
        if resp.usage:
            usage = UsageInfo(
                prompt_tokens=resp.usage.get("prompt_tokens", 0),
                completion_tokens=resp.usage.get("completion_tokens", 0),
                total_tokens=resp.usage.get("total_tokens", resp.tokens_used or 0),
            )
        elif resp.tokens_used:
            usage = UsageInfo(total_tokens=resp.tokens_used)

        return cls(
            content=resp.content,
            model=resp.model,
            usage=usage,
            finish_reason=resp.finish_reason,
            raw_response=resp.raw_response,
            latency_ms=resp.latency_ms,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转为标准字典"""
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage.to_dict(),
            "finish_reason": self.finish_reason,
            "latency_ms": self.latency_ms,
        }
