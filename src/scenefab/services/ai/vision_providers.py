#!/usr/bin/env python3

"""
多模型视觉分析适配器
支持 Qwen3.7 (Max/Plus)、GPT-5 Vision、Gemini 3.5 Flash 等多种 Vision 模型
"""

import logging
import os
from collections.abc import Callable
from typing import Any

# 基类和常量从 vision_base 导入，避免循环导入
from .vision_base import (
    FIRST_PERSON_ANALYSIS_PROMPT,
    VISION_ANALYSIS_PROMPT,
    VisionProvider,
)

logger = logging.getLogger(__name__)


# ============================================================================
# OpenAI GPT-5 Vision
# ============================================================================
class OpenAIVisionProvider(VisionProvider):
    """OpenAI GPT-5 Vision"""

    def __init__(
        self, api_key: str, model: str = "gpt-4o", base_url: str | None = None
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def get_name(self) -> str:
        return f"OpenAI/{self.model}"

    def analyze_image(
        self, image_base64: str, prompt: str = VISION_ANALYSIS_PROMPT
    ) -> dict[str, Any]:
        from openai import OpenAI

        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url

        client = OpenAI(**kwargs)  # type: ignore[arg-type]
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            max_tokens=800,
        )
        return self._parse_json_response(response.choices[0].message.content)  # type: ignore[arg-type]


# ============================================================================
# 通义千问 Qwen-VL（Plus / Max）
# ============================================================================
class QwenVLProvider(VisionProvider):
    """通义千问 Qwen-VL（Plus/Max）"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen-vl-plus",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def get_name(self) -> str:
        return f"Qwen/{self.model}"

    def analyze_image(
        self, image_base64: str, prompt: str = VISION_ANALYSIS_PROMPT
    ) -> dict[str, Any]:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=800,
        )
        return self._parse_json_response(response.choices[0].message.content)  # type: ignore[arg-type]


# ============================================================================
# 通义千问 Qwen3.7（2026年6月最新，多模态 Agent）⭐ 主力推荐
# ============================================================================
class Qwen25VLProvider(VisionProvider):
    """
    通义千问 Qwen3.7（Max/Plus）

    2025年2月发布，视频理解 SOTA，支持 Native 视频输入。
    推荐作为第一人称解说场景理解的主力模型。
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen2.5-vl-72b-instruct",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def get_name(self) -> str:
        return f"Qwen3.7/{self.model}"

    def analyze_image(
        self, image_base64: str, prompt: str = FIRST_PERSON_ANALYSIS_PROMPT
    ) -> dict[str, Any]:
        """
        使用 Qwen3.7 进行第一人称解说专用分析。
        默认 prompt 使用 FIRST_PERSON_ANALYSIS_PROMPT。
        """
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            max_tokens=1024,
        )
        return self._parse_json_response(response.choices[0].message.content)  # type: ignore[arg-type]

    def analyze_video_frames(
        self, frames: list[dict[str, Any]], narrative_prompt: str | None = None
    ) -> list[dict[str, Any]]:
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
            content_parts.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{frame['image_base64']}"
                    },
                }
            )

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
        parsed = self._parse_json_response(raw)  # type: ignore[arg-type]
        if isinstance(parsed, list):
            return parsed
        return [parsed]

    def analyze_frames_batch(
        self,
        frames: list[dict[str, Any]],
        batch_size: int = 6,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[dict[str, Any]]:
        """
        批量分析帧（优化版，减少 60% API 延迟）

        Args:
            frames: List of {timestamp, image_base64}
            batch_size: 每批帧数，默认 6（平衡延迟和准确性）
            progress_callback: 进度回调 (completed, total)

        Returns:
            每帧的分析结果列表（保持原始顺序）
        """
        if not frames:
            return []

        total_frames = len(frames)
        total_results: list[dict[str, Any]] = []
        completed = 0

        # 分批处理
        for batch_start in range(0, total_frames, batch_size):
            batch_end = min(batch_start + batch_size, total_frames)
            batch = frames[batch_start:batch_end]

            logger.debug(
                f"Processing batch {batch_start // batch_size + 1}/{(total_frames + batch_size - 1) // batch_size}, "
                f"frames {batch_start + 1}-{batch_end}/{total_frames}"
            )

            # 构建批次提示词
            batch_prompt = (
                f"这是视频的连续 {len(batch)} 帧（按时间顺序）。"
                "依次用第一人称视角分析每帧。"
                f"返回一个 JSON 数组，共 {len(batch)} 项，每项包含："
                "timestamp（来自输入）、description、emotion、first_person_hook、narrative_angle。"
                "严格按照帧的顺序返回，不要遗漏任何帧。"
            )

            try:
                results = self.analyze_video_frames(
                    batch, narrative_prompt=batch_prompt
                )

                # 确保结果数量匹配
                if isinstance(results, list) and len(results) == len(batch):
                    total_results.extend(results)
                else:
                    # 如果结果数量不匹配，填充空结果
                    logger.warning(
                        f"Batch result count mismatch: expected {len(batch)}, got {len(results) if isinstance(results, list) else 'non-list'}"
                    )
                    total_results.extend(
                        results if isinstance(results, list) else [results]
                    )

            except Exception as e:
                logger.error(f"Batch {batch_start // batch_size + 1} failed: {e}")
                # 该批次失败，填充空结果
                total_results.extend([{} for _ in range(len(batch))])

            completed += len(batch)
            if progress_callback:
                progress_callback(completed, total_frames)

        return total_results


# ============================================================================
# Google Gemini 3.x Vision
# ============================================================================
class GeminiVisionProvider(VisionProvider):
    """Google Gemini 3.x Vision"""

    def __init__(
        self, api_key: str, model: str = "gemini-2.5-flash-preview-0506"
    ) -> None:
        self.api_key = api_key
        self.model = model

    def get_name(self) -> str:
        return f"Gemini/{self.model}"

    def analyze_image(
        self, image_base64: str, prompt: str = VISION_ANALYSIS_PROMPT
    ) -> dict[str, Any]:
        import httpx

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.model}:generateContent?key={self.api_key}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_base64,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {"maxOutputTokens": 800},
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
    优先顺序：Qwen3.7 > Qwen-VL > GPT-4o > Gemini

    用法:
        factory = VisionAnalyzerFactory(config)
        provider = factory.get_provider()
        result = provider.analyze_image(base64_data)
    """

    def _get_provider_map(self) -> dict[str, type]:
        """延迟加载 Provider 映射，避免循环导入"""
        from .providers.gemini35_flash import Gemini35FlashProvider
        from .providers.qwen37 import Qwen37Provider

        return {
            "openai": OpenAIVisionProvider,
            "qwen": QwenVLProvider,
            "qwen25": Qwen25VLProvider,
            "qwen37": Qwen37Provider,
            "gemini": GeminiVisionProvider,
            "gemini35": Gemini35FlashProvider,
        }

    PROVIDER_MAP = {}  # type: ignore[var-annotated]  # 保留兼容，实际用 _get_provider_map()

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._providers: list[VisionProvider] = []
        self._init_providers()

    def _init_providers(self) -> None:
        from .providers.gemini35_flash import Gemini35FlashProvider
        from .providers.qwen37 import Qwen37Provider

        llm = self._config.get("LLM", {})

        # Qwen3.7（最优先，2026年6月最新，多模态 Agent）
        qwen37_key = os.getenv("QWEN_API_KEY") or llm.get("qwen", {}).get("api_key", "")
        vision_model = os.getenv("VISION_MODEL", "qwen3.7-plus")
        if qwen37_key and not qwen37_key.startswith("${"):
            self._providers.append(
                Qwen37Provider(
                    api_key=qwen37_key,
                    model=vision_model,
                )
            )
            logger.info(f"✅ Qwen3.7 ({vision_model}) 已启用 — 多模态 Agent")

        # Qwen-VL Plus（备选）
        qwen_key = os.getenv("QWEN_API_KEY") or llm.get("qwen", {}).get("api_key", "")
        if qwen_key and not qwen_key.startswith("${"):
            self._providers.append(
                QwenVLProvider(
                    api_key=qwen_key,
                    model=llm.get("qwen", {}).get("vision_model", "qwen-vl-plus"),
                )
            )

        # OpenAI GPT-4o
        openai_key = os.getenv("OPENAI_API_KEY") or llm.get("openai", {}).get(
            "api_key", ""
        )
        if openai_key and not openai_key.startswith("${"):
            self._providers.append(
                OpenAIVisionProvider(
                    api_key=openai_key,
                    model="gpt-4o",
                    base_url=llm.get("openai", {}).get("base_url"),
                )
            )

        # Gemini 3.5 Flash（2026年5月最新）
        gemini_key = os.getenv("GEMINI_API_KEY") or llm.get("gemini", {}).get(
            "api_key", ""
        )
        if gemini_key and not gemini_key.startswith("${"):
            self._providers.append(
                Gemini35FlashProvider(
                    api_key=gemini_key,
                    model="gemini-3.5-flash",
                )
            )
            logger.info("✅ Gemini 3.5 Flash 已启用 — Flash 级别成本")

        # Gemini 旧版（备选）
        gemini_legacy_key = os.getenv("GEMINI_API_KEY") or llm.get("gemini", {}).get(
            "api_key", ""
        )
        if gemini_legacy_key and not gemini_legacy_key.startswith("${"):
            self._providers.append(
                GeminiVisionProvider(
                    api_key=gemini_legacy_key,
                    model="gemini-2.5-flash-preview-0506",
                )
            )

    def get_provider(self, preferred: str | None = None) -> VisionProvider | None:
        """获取可用的 Vision 提供者（优先返回指定的）"""
        if preferred:
            for p in self._providers:
                if preferred.lower() in p.get_name().lower():
                    return p
        return self._providers[0] if self._providers else None

    def analyze_with_fallback(
        self, image_base64: str, prompt: str = FIRST_PERSON_ANALYSIS_PROMPT
    ) -> dict[str, Any]:
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
            f"所有视觉分析提供者均失败（已尝试: {tried}），最后错误: {last_error}"
        )

    def get_available_providers(self) -> list[str]:
        return [p.get_name() for p in self._providers]
