#!/usr/bin/env python3

"""
Gemini 3.5 Flash Vision Provider

Google Gemini 3.5 Flash 视觉理解模型适配器
- Flash 级别成本，接近 Pro 级别智能
- 4 倍输出速度
- 支持 100 万 token 上下文
- 视频上限 45 分钟（含音频）/ 1 小时（无音频）

API 文档：https://ai.google.dev/docs/gemini_api
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

from ..vision_providers import VisionProvider, VisionAnalysisResult

logger = logging.getLogger(__name__)


class Gemini35FlashProvider(VisionProvider):
    """
    Google Gemini 3.5 Flash 视觉理解 Provider

    2026年5月19日发布，核心优势：
    - Flash 级别成本，接近 Pro 级别智能
    - 输出 token 速度是其他前沿模型的 4 倍
    - Terminal-Bench 2.1: 76.2%（超越 Gemini 3.1 Pro）
    - CharXiv Reasoning: 84.2%

    视频处理能力：
    - 45 分钟（含音频）
    - 1 小时（无音频）
    """

    # API 配置
    API_BASE = "https://generativelanguage.googleapis.com/v1beta"

    # 模型配置
    MODELS = {
        "gemini-3.5-flash": {
            "name": "Gemini 3.5 Flash",
            "description": "Flash 级别成本，接近 Pro 级别智能",
            "max_context": 1_000_000,  # 100万 token
            "max_video_duration": 45 * 60,  # 45分钟（含音频）
        },
    }

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.5-flash",
    ):
        """
        初始化 Gemini 3.5 Flash Provider

        Args:
            api_key: Google AI API Key
            model: 模型名称
        """
        self.api_key = api_key
        self.model = model
        self.client = httpx.Client(timeout=300.0)

        # 获取模型配置
        self.model_config = self.MODELS.get(model, self.MODELS["gemini-3.5-flash"])

        logger.info(f"Gemini 3.5 Flash Provider 初始化完成: {model}")

    def get_name(self) -> str:
        return f"Gemini/{self.model}"

    def is_available(self) -> bool:
        """检查 Provider 是否可用"""
        return bool(self.api_key and not self.api_key.startswith("${"))

    def analyze_video(
        self,
        video_path: str,
        fps: float = 2.0,
        max_frames: int = 256,
        prompt: str | None = None,
    ) -> VisionAnalysisResult:
        """
        分析视频内容

        Args:
            video_path: 视频文件路径或 URL
            fps: 抽帧频率
            max_frames: 最大抽帧数
            prompt: 自定义提示词

        Returns:
            VisionAnalysisResult: 视觉分析结果
        """
        if prompt is None:
            prompt = self._get_default_prompt()

        try:
            # 读取视频文件
            video_path_obj = Path(video_path)
            if video_path_obj.exists():
                with open(video_path_obj, "rb") as f:
                    video_data = base64.b64encode(f.read()).decode("utf-8")
                mime_type = self._get_mime_type(video_path)
            else:
                # URL 方式
                return VisionAnalysisResult(
                    description="暂不支持 URL 方式，请使用本地文件",
                    raw_response="URL not supported",
                )

            # 构建请求
            url = f"{self.API_BASE}/models/{self.model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": video_data,
                                }
                            },
                            {"text": prompt},
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": 4096,
                },
            }

            # 调用 API
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            # 解析响应
            result_text = result["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_response(result_text)

        except Exception as e:
            logger.error(f"Gemini 3.5 Flash 视频分析失败: {e}")
            return VisionAnalysisResult(
                description=f"分析失败: {str(e)}",
                raw_response=str(e),
            )

    def analyze_image(
        self,
        image_base64: str,
        prompt: str | None = None,
    ) -> VisionAnalysisResult:
        """
        分析图像内容

        Args:
            image_base64: Base64 编码的图像数据
            prompt: 自定义提示词

        Returns:
            VisionAnalysisResult: 视觉分析结果
        """
        if prompt is None:
            prompt = self._get_default_prompt()

        try:
            # 构建请求
            url = f"{self.API_BASE}/models/{self.model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": image_base64,
                                }
                            },
                            {"text": prompt},
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": 4096,
                },
            }

            # 调用 API
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            # 解析响应
            result_text = result["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_response(result_text)

        except Exception as e:
            logger.error(f"Gemini 3.5 Flash 图像分析失败: {e}")
            return VisionAnalysisResult(
                description=f"分析失败: {str(e)}",
                raw_response=str(e),
            )

    def analyze_video_with_timestamps(
        self,
        video_path: str,
        fps: float = 2.0,
    ) -> dict[str, Any]:
        """
        分析视频并返回事件时间戳

        Args:
            video_path: 视频文件路径或 URL
            fps: 抽帧频率

        Returns:
            dict: 包含事件时间戳的分析结果
        """
        timestamp_prompt = """分析这段视频，返回 JSON 格式：
{
    "summary": "视频概要",
    "events": [
        {
            "timestamp": "HH:mm:ss",
            "description": "事件描述",
            "importance": 1-10
        }
    ],
    "key_segments": [
        {
            "start": "HH:mm:ss",
            "end": "HH:mm:ss",
            "description": "关键片段描述"
        }
    ]
}

请用中文回答。"""

        result = self.analyze_video(video_path, fps=fps, prompt=timestamp_prompt)

        # 尝试解析 JSON
        try:
            response_text = result.raw_response
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text

            return json.loads(json_str)
        except Exception as e:
            logger.warning(f"解析时间戳响应失败: {e}")
            return {
                "summary": result.description,
                "events": [],
                "key_segments": [],
            }

    def _get_mime_type(self, file_path: str) -> str:
        """获取文件 MIME 类型"""
        ext = Path(file_path).suffix.lower()
        mime_types = {
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo",
            ".mov": "video/quicktime",
            ".mkv": "video/x-matroska",
            ".webm": "video/webm",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return mime_types.get(ext, "application/octet-stream")

    def _get_default_prompt(self) -> str:
        """获取默认分析提示词"""
        return """分析这段视频/图像，返回 JSON 格式：
{
    "description": "详细描述画面内容（50-100字）",
    "content_type": "person/landscape/indoor/outdoor/text/product/animal/food/action",
    "objects": ["检测到的主要物体列表"],
    "text": "画面中出现的文字（如果有）",
    "emotion": "neutral/happy/sad/excited/calm/tense/romantic",
    "color_tone": "warm/cold/neutral",
    "scene_narrative": "场景叙事（适合第一人称解说）",
    "protagonist_action": "主角动作",
    "environment_mood": "环境氛围",
    "first_person_hook": "适合第一人称的开场钩子"
}

请用中文回答。"""

    def _parse_response(self, response_text: str) -> VisionAnalysisResult:
        """解析 API 响应"""
        result = VisionAnalysisResult(raw_response=response_text)

        try:
            # 尝试从响应中提取 JSON
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text

            data = json.loads(json_str)

            # 填充结果
            result.description = data.get("description", "")
            result.content_type = data.get("content_type", "unknown")
            result.objects = data.get("objects", [])
            result.text_content = data.get("text", "")
            result.emotion = data.get("emotion", "neutral")
            result.color_tone = data.get("color_tone", "neutral")
            result.scene_narrative = data.get("scene_narrative", "")
            result.protagonist_action = data.get("protagonist_action", "")
            result.environment_mood = data.get("environment_mood", "")
            result.first_person_hook = data.get("first_person_hook", "")
            result.confidence = 0.85  # Gemini 3.5 Flash 置信度

        except Exception as e:
            logger.warning(f"解析 Gemini 响应失败: {e}")
            result.description = response_text[:500]  # 截取前500字符

        return result


# 便捷函数
def create_gemini35_flash_provider(
    api_key: str | None = None,
    model: str = "gemini-3.5-flash",
) -> Gemini35FlashProvider:
    """
    创建 Gemini 3.5 Flash Provider 实例

    Args:
        api_key: API Key，默认从环境变量读取
        model: 模型名称

    Returns:
        Gemini35FlashProvider: Provider 实例
    """
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY", "")

    return Gemini35FlashProvider(api_key=api_key, model=model)
