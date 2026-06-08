"""
SceneFab API 适配器混入

提供与外部 AI 模型（Qwen、Gemini）交互的方法，
包括关键帧提取、API 调用、提示词构建和响应解析。
"""

import json
import logging
from typing import Any

from scenefab.services.video_understanding.models import VideoSegment

logger = logging.getLogger(__name__)


class APIAdapterMixin:
    """API 适配器混入类，提供模型调用相关方法"""

    def _extract_key_frames(
        self,
        segment: VideoSegment,
        max_frames: int,
    ) -> list[dict[str, Any]]:
        """
        提取关键帧

        Args:
            segment: 视频片段
            max_frames: 最大帧数

        Returns:
            list: 关键帧列表
        """
        try:
            import cv2
            import numpy as np

            # 打开视频
            cap = cv2.VideoCapture(segment.video_path if hasattr(segment, 'video_path') else "")
            cap.set(cv2.CAP_PROP_POS_MSEC, segment.start_time * 1000)

            key_frames = []
            frame_count = 0
            interval = segment.duration / max_frames

            while frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                timestamp = segment.start_time + frame_count * interval

                # 计算帧的特征（简化版）
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness = float(np.mean(gray))
                contrast = float(np.std(gray))

                key_frames.append({
                    "timestamp": timestamp,
                    "brightness": brightness,
                    "contrast": contrast,
                    "frame_number": frame_count,
                })

                # 跳过帧
                for _ in range(int(interval * 30)):  # 假设 30fps
                    cap.read()

                frame_count += 1

            cap.release()
            return key_frames

        except Exception as e:
            logger.warning(f"关键帧提取失败: {e}")
            return []

    def _understand_with_gemini(
        self,
        segment: VideoSegment,
        key_frames: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        使用 Gemini 理解片段

        Args:
            segment: 视频片段
            key_frames: 关键帧列表

        Returns:
            dict: 理解结果
        """
        try:
            # 构建提示词
            prompt = self._build_understanding_prompt(segment)

            # 调用 Gemini API
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro:generateContent?key={self.gemini_api_key}"

            # 构建请求（简化版，实际需要上传视频片段）
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": 4096,
                },
            }

            response = self.gemini_client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            # 解析响应
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_understanding_response(text)

        except Exception as e:
            logger.error(f"Gemini 理解失败: {e}")
            return {"summary": "", "characters": [], "emotions": [], "events": []}

    def _understand_with_qwen(
        self,
        segment: VideoSegment,
        key_frames: list[dict[str, Any]],
        model: str,
    ) -> dict[str, Any]:
        """
        使用 Qwen 理解片段

        Args:
            segment: 视频片段
            key_frames: 关键帧列表
            model: 模型名称

        Returns:
            dict: 理解结果
        """
        try:
            # 构建提示词
            prompt = self._build_understanding_prompt(segment)

            # 调用 Qwen API
            response = self.qwen_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=4096,
            )

            # 解析响应
            text = response.choices[0].message.content
            return self._parse_understanding_response(text)

        except Exception as e:
            logger.error(f"Qwen 理解失败: {e}")
            return {"summary": "", "characters": [], "emotions": [], "events": []}

    def _understand_locally(
        self,
        segment: VideoSegment,
        key_frames: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        本地理解（简化版）

        Args:
            segment: 视频片段
            key_frames: 关键帧列表

        Returns:
            dict: 理解结果
        """
        # 简化版本地理解
        return {
            "summary": f"视频片段 {segment.segment_id}，时长 {segment.duration:.1f} 秒",
            "characters": [],
            "emotions": ["neutral"],
            "events": [],
        }

    def _build_understanding_prompt(self, segment: VideoSegment) -> str:
        """
        构建理解提示词

        Args:
            segment: 视频片段

        Returns:
            str: 提示词
        """
        return f"""请分析这段视频片段（{segment.start_time:.1f}秒 - {segment.end_time:.1f}秒），并返回以下信息（JSON格式）：

{{
    "summary": "片段摘要（50-100字）",
    "characters": ["出现的人物列表"],
    "emotions": ["主要情绪标签"],
    "events": [
        {{
            "timestamp": "事件发生时间（秒）",
            "description": "事件描述",
            "importance": "重要性 1-10"
        }}
    ]
}}

请用中文回答。"""

    def _parse_understanding_response(self, text: str) -> dict[str, Any]:
        """
        解析理解响应

        Args:
            text: 响应文本

        Returns:
            dict: 解析结果
        """
        try:
            # 尝试提取 JSON
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
            else:
                json_str = text

            return json.loads(json_str)

        except Exception as e:
            logger.warning(f"解析响应失败: {e}")
            return {
                "summary": text[:200] if text else "",
                "characters": [],
                "emotions": [],
                "events": [],
            }
