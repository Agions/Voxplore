#!/usr/bin/env python3

"""
Qwen3.7 Vision Provider

阿里云百炼 Qwen3.7 视觉理解模型适配器
- 支持 OpenAI 兼容 API
- 支持 video_url + fps 参数
- 支持 qwen3.7-max 和 qwen3.7-plus 两种模型
- Vision Arena 全球前五、中国第一

API 文档：https://help.aliyun.com/zh/model-studio/developer-reference/qwen3-7
"""

import logging
import os
from typing import Any

from openai import OpenAI

from ..vision_base import VisionAnalysisResult, VisionProvider

logger = logging.getLogger(__name__)


class Qwen37Provider(VisionProvider):
    """
    通义千问 Qwen3.7 视觉理解 Provider

    2026年6月发布，统一多模态 Agent 模型，支持：
    - 图像理解
    - 视频理解（支持 fps 控制）
    - GUI Agent 能力
    - 事件时间戳定位

    模型选择：
    - qwen3.7-max: 推荐首选，质量最高
    - qwen3.7-plus: 轻量快速，适合高吞吐场景
    """

    # 模型配置
    MODELS = {
        "qwen3.7-max": {
            "name": "Qwen3.7 Max",
            "description": "最强多模态 Agent，Vision Arena 前五",
            "max_context": 1_000_000,  # 100万 token
        },
        "qwen3.7-plus": {
            "name": "Qwen3.7 Plus",
            "description": "轻量快速，适合批量处理",
            "max_context": 1_000_000,
        },
    }

    # 默认视频抽帧参数
    DEFAULT_FPS = 2.0
    DEFAULT_MAX_FRAMES = 256

    def __init__(
        self,
        api_key: str,
        model: str = "qwen3.7-max",
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
    ):
        """
        初始化 Qwen3.7 Provider

        Args:
            api_key: 阿里云百炼 API Key
            model: 模型名称 (qwen3.7-max / qwen3.7-plus)
            base_url: API 基础 URL
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        # 获取模型配置
        self.model_config = self.MODELS.get(model, self.MODELS["qwen3.7-max"])

        logger.info(f"Qwen3.7 Provider 初始化完成: {model}")

    def get_name(self) -> str:
        return f"Qwen3.7/{self.model}"

    def is_available(self) -> bool:
        """检查 Provider 是否可用"""
        return bool(self.api_key and not self.api_key.startswith("${"))

    def analyze_video(
        self,
        video_path: str,
        fps: float = DEFAULT_FPS,
        max_frames: int = DEFAULT_MAX_FRAMES,
        prompt: str | None = None,
    ) -> VisionAnalysisResult:
        """
        分析视频内容

        Args:
            video_path: 视频文件路径或 URL
            fps: 抽帧频率 [0.1, 10]，静态/长视频 1.0，动态 5.0
            max_frames: 最大抽帧数
            prompt: 自定义提示词

        Returns:
            VisionAnalysisResult: 视觉分析结果
        """
        if prompt is None:
            prompt = self._get_default_prompt()

        try:
            # 构建视频内容
            video_content = {
                "type": "video_url",
                "video_url": {"url": video_path, "fps": fps},
            }

            # 调用 API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {  # type: ignore[unused-ignore, misc, object]
                        "role": "user",
                        "content": [video_content, {"type": "text", "text": prompt}],
                    }
                ],
                max_tokens=4096,
            )

            # 解析响应
            result_text = response.choices[0].message.content or ""
            return self._parse_response(result_text)

        except Exception as e:
            logger.error(f"Qwen3.7 视频分析失败: {e}")
            return VisionAnalysisResult(
                description=f"分析失败: {str(e)}",
                raw_response=str(e),
            )

    def analyze_image(  # type: ignore[override]
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
            # 构建图像内容
            image_content = {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
            }

            # 调用 API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {  # type: ignore[unused-ignore, misc, object]
                        "role": "user",
                        "content": [image_content, {"type": "text", "text": prompt}],
                    }
                ],
                max_tokens=4096,
            )

            # 解析响应
            result_text = response.choices[0].message.content or ""
            return self._parse_response(result_text)

        except Exception as e:
            logger.error(f"Qwen3.7 图像分析失败: {e}")
            return VisionAnalysisResult(
                description=f"分析失败: {str(e)}",
                raw_response=str(e),
            )

    def analyze_video_with_timestamps(
        self,
        video_path: str,
        fps: float = DEFAULT_FPS,
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
            import json

            # 从响应中提取 JSON
            response_text = result.raw_response
            # 查找 JSON 块
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text

            return json.loads(json_str)  # type: ignore[no-any-return]
        except Exception as e:
            logger.warning(f"解析时间戳响应失败: {e}")
            return {
                "summary": result.description,
                "events": [],
                "key_segments": [],
            }

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
            import json

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
            result.confidence = 0.9  # Qwen3.7 置信度较高

        except Exception as e:
            logger.warning(f"解析 Qwen3.7 响应失败: {e}")
            result.description = response_text[:500]  # 截取前500字符

        return result


# 便捷函数
def create_qwen37_provider(
    api_key: str | None = None,
    model: str = "qwen3.7-max",
) -> Qwen37Provider:
    """
    创建 Qwen3.7 Provider 实例

    Args:
        api_key: API Key，默认从环境变量读取
        model: 模型名称

    Returns:
        Qwen37Provider: Provider 实例
    """
    if api_key is None:
        api_key = os.getenv("QWEN_API_KEY", "")

    return Qwen37Provider(api_key=api_key, model=model)
