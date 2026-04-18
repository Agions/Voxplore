#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多模型视觉分析适配器
支持 Qwen2.5-VL (72B SOTA)、GPT-5 Vision、Gemini 3 Vision 等多种 Vision 模型
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import logging
logger = logging.getLogger(__name__)


@dataclass
class VisionAnalysisResult:
    """视觉分析结果"""
    description: str = ""
    content_type: str = "unknown"
    objects: List[str] = field(default_factory=list)
    text_content: str = ""
    emotion: str = "neutral"
    color_tone: str = "neutral"
    confidence: float = 0.0
    raw_response: str = ""
    # 第一人称解说专用字段
    scene_narrative: str = ""      # 场景叙事（"我"看到什么）
    protagonist_action: str = ""    # 主角动作
    environment_mood: str = ""      # 环境氛围
    first_person_hook: str = ""     # 适合第一人称的开场钩子


# ============================================================================
# 默认提示词（通用场景理解）
# ============================================================================
VISION_ANALYSIS_PROMPT = """分析这张视频截图，返回JSON格式：
{
    "description": "详细描述画面内容（50-100字）",
    "content_type": "person/landscape/indoor/outdoor/text/product/animal/food/action",
    "objects": ["检测到的主要物体列表"],
    "text": "画面中出现的文字（如果有）",
    "emotion": "neutral/happy/sad/excited/calm/tense/romantic",
    "color_tone": "warm/cold/neutral",
    "suitable_for": {
        "commentary": 0-100,
        "monologue": 0-100,
        "mashup": 0-100
    }
}
只返回JSON，不要其他内容。"""


# ============================================================================
# 第一人称解说专用提示词（Qwen2.5-VL 增强版）
# ============================================================================
FIRST_PERSON_ANALYSIS_PROMPT = """你是一位专业的电影分镜师和第一人称叙事导演。

分析这段视频截图，用"我"（画面中主角）的视角描述所见所行。

返回JSON格式：
{
    "description": "客观描述画面内容（30-60字）",
    "content_type": "person/landscape/indoor/outdoor/product/action/scenery",
    "objects": ["画面中主要物体"],
    "emotion": "neutral/happy/sad/calm/excited/tense/wonder/awe",
    "color_tone": "warm/cold/muted/vibrant",
    "protagonist_action": "主角正在做什么（用动词，简洁）",
    "environment_mood": "环境氛围关键词（3-5个）",
    "first_person_hook": "一句适合第一人称的开场叙述（10-20字，要有画面感）",
    "narrative_angle": "这个场景适合从哪个角度切入叙事（旁观/内心独白/现场解说）"
}

注意：
- protagist_action 站在主角立场描述，而非旁观者
- first_person_hook 要有沉浸感，像主角在说话
- 只返回JSON，不要解释"""


# ============================================================================
# Provider 基类
# ============================================================================
class VisionProvider(ABC):
    """视觉分析提供者基类"""

    @abstractmethod
    def analyze_image(self, image_base64: str,
                      prompt: str = VISION_ANALYSIS_PROMPT) -> Dict[str, Any]:
        """分析图片，返回解析后的字典"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

    @staticmethod
    def _parse_json_response(content: str) -> Dict[str, Any]:
        """从可能包含 markdown 的响应中提取 JSON"""
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            return {"description": content.strip()}


# ============================================================================
# OpenAI GPT-5 Vision
# ============================================================================
class OpenAIVisionProvider(VisionProvider):
    """OpenAI GPT-5 Vision"""

    def __init__(self, api_key: str, model: str = "gpt-4o",
                 base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def get_name(self) -> str:
        return f"OpenAI/{self.model}"

    def analyze_image(self, image_base64: str,
                      prompt: str = VISION_ANALYSIS_PROMPT) -> Dict[str, Any]:
        from openai import OpenAI
        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url

        client = OpenAI(**kwargs)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}",
                        "detail": "low"
                    }}
                ]
            }],
            max_tokens=800,
        )
        return self._parse_json_response(response.choices[0].message.content)


# ============================================================================
# 通义千问 Qwen-VL（Plus / Max）
# ============================================================================
class QwenVLProvider(VisionProvider):
    """通义千问 Qwen-VL（Plus/Max）"""

    def __init__(self, api_key: str,
                 base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
                 model: str = "qwen-vl-plus"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def get_name(self) -> str:
        return f"Qwen/{self.model}"

    def analyze_image(self, image_base64: str,
                      prompt: str = VISION_ANALYSIS_PROMPT) -> Dict[str, Any]:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }}
                ]
            }],
            max_tokens=800,
        )
        return self._parse_json_response(response.choices[0].message.content)


# ============================================================================
# 通义千问 Qwen2.5-VL（2025年2月新版，72B SOTA）⭐ 主力推荐
# ============================================================================
class Qwen25VLProvider(VisionProvider):
    """
    通义千问 Qwen2.5-VL（72B）

    2025年2月发布，视频理解 SOTA，支持 Native 视频输入。
    推荐作为第一人称解说场景理解的主力模型。
    """

    def __init__(self, api_key: str,
                 base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
                 model: str = "qwen2.5-vl-72b-instruct"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def get_name(self) -> str:
        return f"Qwen2.5-VL/{self.model}"

    def analyze_image(self, image_base64: str,
                      prompt: str = FIRST_PERSON_ANALYSIS_PROMPT) -> Dict[str, Any]:
        """
        使用 Qwen2.5-VL 进行第一人称解说专用分析。
        默认 prompt 使用 FIRST_PERSON_ANALYSIS_PROMPT。
        """
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }},
                    {"type": "text", "text": prompt}
                ]
            }],
            max_tokens=1024,
        )
        return self._parse_json_response(response.choices[0].message.content)

    def analyze_video_frames(self, frames: List[Dict[str, Any]],
                            narrative_prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        分析多帧视频（支持 Native 视频输入模式）。

        Args:
            frames: List of {timestamp, image_base64}
            narrative_prompt: 可选的自定义叙事提示词

        Returns:
            每帧的分析结果列表
        """
        if not frames:
            return []

        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        # 构建多帧消息
        content_parts = []
        for frame in frames:
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{frame['image_base64']}"}
            })

        prompt = narrative_prompt or (
            "这是一个视频的连续帧（按时间顺序）。"
            "请依次分析每帧，用第一人称视角描述。"
            "返回JSON数组，每项对应一帧："
            "[{timestamp, description, emotion, first_person_hook, narrative_angle}]"
        )

        content_parts.append({"type": "text", "text": prompt})

        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content_parts}],
            max_tokens=2048,
        )

        raw = response.choices[0].message.content
        # 尝试解析 JSON 数组
        parsed = self._parse_json_response(raw)
        if isinstance(parsed, list):
            return parsed
        return [parsed]


# ============================================================================
# Google Gemini 3.x Vision
# ============================================================================
class GeminiVisionProvider(VisionProvider):
    """Google Gemini 3.x Vision"""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-preview-0506"):
        self.api_key = api_key
        self.model = model

    def get_name(self) -> str:
        return f"Gemini/{self.model}"

    def analyze_image(self, image_base64: str,
                      prompt: str = VISION_ANALYSIS_PROMPT) -> Dict[str, Any]:
        import httpx

        url = (f"https://generativelanguage.googleapis.com/v1beta/"
               f"models/{self.model}:generateContent?key={self.api_key}")

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_base64
                    }}
                ]
            }],
            "generationConfig": {"maxOutputTokens": 800}
        }

        resp = httpx.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return self._parse_json_response(text)


# ============================================================================
# 视觉分析器工厂
# ============================================================================
class VisionAnalyzerFactory:
    """
    视觉分析器工厂

    根据配置自动选择可用的 Vision 提供者，支持 fallback 降级。
    优先顺序：Qwen2.5-VL > Qwen-VL > GPT-4o > Gemini

    用法:
        factory = VisionAnalyzerFactory(config)
        provider = factory.get_provider()
        result = provider.analyze_image(base64_data)
    """

    PROVIDER_MAP = {
        "openai": OpenAIVisionProvider,
        "qwen": QwenVLProvider,
        "qwen25": Qwen25VLProvider,
        "gemini": GeminiVisionProvider,
    }

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._providers: List[VisionProvider] = []
        self._init_providers()

    def _init_providers(self):
        llm = self._config.get("LLM", {})

        # Qwen2.5-VL（最优先，2025年2月最新，视频理解 SOTA）
        qwen25_key = os.getenv("QWEN_API_KEY") or llm.get("qwen", {}).get("api_key", "")
        if qwen25_key and not qwen25_key.startswith("${"):
            self._providers.append(Qwen25VLProvider(
                api_key=qwen25_key,
                model="qwen2.5-vl-72b-instruct",
            ))
            logger.info("✅ Qwen2.5-VL (72B) 已启用 — 视频理解 SOTA")

        # Qwen-VL Plus（备选）
        qwen_key = os.getenv("QWEN_API_KEY") or llm.get("qwen", {}).get("api_key", "")
        if qwen_key and not qwen_key.startswith("${"):
            self._providers.append(QwenVLProvider(
                api_key=qwen_key,
                model=llm.get("qwen", {}).get("vision_model", "qwen-vl-plus"),
            ))

        # OpenAI GPT-4o
        openai_key = os.getenv("OPENAI_API_KEY") or llm.get("openai", {}).get("api_key", "")
        if openai_key and not openai_key.startswith("${"):
            self._providers.append(OpenAIVisionProvider(
                api_key=openai_key,
                model="gpt-4o",
                base_url=llm.get("openai", {}).get("base_url"),
            ))

        # Gemini
        gemini_key = os.getenv("GEMINI_API_KEY") or llm.get("gemini", {}).get("api_key", "")
        if gemini_key and not gemini_key.startswith("${"):
            self._providers.append(GeminiVisionProvider(
                api_key=gemini_key,
                model="gemini-2.5-flash-preview-0506",
            ))

    def get_provider(self, preferred: Optional[str] = None) -> Optional[VisionProvider]:
        """获取可用的 Vision 提供者（优先返回指定的）"""
        if preferred:
            for p in self._providers:
                if preferred.lower() in p.get_name().lower():
                    return p
        return self._providers[0] if self._providers else None

    def analyze_with_fallback(self, image_base64: str,
                               prompt: str = FIRST_PERSON_ANALYSIS_PROMPT) -> Dict[str, Any]:
        """带 fallback 的分析，自动切换提供者直到成功"""
        last_error = None
        tried = []

        for provider in self._providers:
            tried.append(provider.get_name())
            try:
                return provider.analyze_image(image_base64, prompt)
            except Exception as e:
                last_error = e
                logger.error(f"{provider.get_name()} 分析失败: {e}")
                continue

        raise RuntimeError(
            f"所有视觉分析提供者均失败（已尝试: {tried}），"
            f"最后错误: {last_error}"
        )

    def get_available_providers(self) -> List[str]:
        return [p.get_name() for p in self._providers]
