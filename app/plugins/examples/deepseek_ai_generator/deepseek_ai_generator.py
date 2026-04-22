"""
DeepSeek AI Generator Plugin
DeepSeek AI 生成器插件 - 提供场景分析和脚本生成功能
"""

import uuid
import json
from typing import Dict, Any, List, Optional, AsyncIterator

from app.plugins.interfaces.base import PluginManifest
from app.plugins.interfaces.ai_generator import (
    BaseAIGeneratorPlugin,
    SceneAnalysis,
    ScriptGeneration,
)


class DeepSeekAIGeneratorPlugin(BaseAIGeneratorPlugin):
    """
    DeepSeek AI 生成器插件

    提供以下功能:
    - 场景分析: 分析视频画面内容，提取场景类型、氛围、主体等
    - 脚本生成: 基于场景上下文生成解说脚本
    - 流式生成: 支持实时预览的流式脚本生成
    """

    def __init__(self, manifest: PluginManifest):
        super().__init__(manifest)
        self._api_key: Optional[str] = None
        self._base_url: str = "https://api.deepseek.com"
        self._model: str = "deepseek-chat"
        self._client = None

    def _on_enable(self) -> None:
        """启用时的回调"""
        self.log_info("DeepSeek AI Generator plugin enabled")

    def _on_disable(self) -> None:
        """禁用时的回调"""
        self.log_info("DeepSeek AI Generator plugin disabled")

    def get_provider_name(self) -> str:
        """获取 AI Provider 名称"""
        return "DeepSeek"

    def get_capabilities(self) -> Dict[str, bool]:
        """
        获取插件能力
        """
        return {
            "scene_analysis": True,
            "script_generation": True,
            "streaming": True,
            "voice_synthesis": False,
        }

    async def analyze_scene(
        self,
        video_path: str,
        frame_timestamps: List[float],
    ) -> List[SceneAnalysis]:
        """
        分析视频场景

        Args:
            video_path: 视频文件路径
            frame_timestamps: 要分析的帧时间戳

        Returns:
            场景分析结果列表
        """
        # 调用 DeepSeek API 进行场景分析
        prompt = self._build_scene_analysis_prompt(video_path, frame_timestamps)

        try:
            response = await self._call_deepseek_api(prompt)
            scenes = self._parse_scene_analysis_response(response, frame_timestamps)
            return scenes
        except Exception as e:
            self.log_error(f"Scene analysis failed: {e}")
            # 返回空列表或可以返回部分结果
            return []

    def _build_scene_analysis_prompt(
        self, video_path: str, frame_timestamps: List[float]
    ) -> str:
        """构建场景分析提示词"""
        timestamps_str = ", ".join(f"{t:.2f}s" for t in frame_timestamps)
        return f"""请分析以下视频的场景信息:

视频路径: {video_path}
分析时间点: {timestamps_str}

请为每个时间点分析并返回JSON格式的场景信息，包含:
- scene_id: 场景唯一ID
- scene_type: 场景类型 (indoor/outdoor/transition)
- location: 地点描述
- atmosphere: 氛围描述
- subjects: 场景主体列表，每个包含类型和描述
- key_objects: 关键物体列表
- importance: 叙事重要性 (0-1)

请以JSON数组格式返回结果。"""

    def _parse_scene_analysis_response(
        self, response: str, frame_timestamps: List[float]
    ) -> List[SceneAnalysis]:
        """解析场景分析响应"""
        scenes = []

        try:
            # 尝试提取 JSON
            json_str = self._extract_json(response)
            if json_str:
                data = json.loads(json_str)
                if isinstance(data, list):
                    for item in data:
                        scene = SceneAnalysis(
                            scene_id=item.get("scene_id", str(uuid.uuid4())),
                            scene_type=item.get("scene_type", "unknown"),
                            location=item.get("location", ""),
                            atmosphere=item.get("atmosphere", ""),
                            subjects=item.get("subjects", []),
                            key_objects=item.get("key_objects", []),
                            importance=item.get("importance", 0.5),
                        )
                        scenes.append(scene)
        except Exception as e:
            self.log_error(f"Failed to parse scene analysis response: {e}")

        # 如果解析失败，生成默认场景
        if not scenes:
            for i, timestamp in enumerate(frame_timestamps):
                scenes.append(
                    SceneAnalysis(
                        scene_id=str(uuid.uuid4()),
                        scene_type="unknown",
                        location="待分析",
                        atmosphere="待分析",
                        subjects=[],
                        key_objects=[],
                        importance=0.5,
                    )
                )

        return scenes

    async def generate_script(
        self,
        scene_context: str,
        emotion: str,
        style: str,
        max_duration: Optional[float] = None,
    ) -> ScriptGeneration:
        """
        生成解说脚本

        Args:
            scene_context: 场景上下文描述
            emotion: 目标情感风格
            style: 解说风格
            max_duration: 最大时长（秒）

        Returns:
            生成的脚本
        """
        prompt = self._build_script_generation_prompt(
            scene_context, emotion, style, max_duration
        )

        try:
            response = await self._call_deepseek_api(prompt)
            return self._parse_script_generation_response(response)
        except Exception as e:
            self.log_error(f"Script generation failed: {e}")
            return ScriptGeneration(
                script_id=str(uuid.uuid4()),
                text="脚本生成失败，请稍后重试。",
                emotion=emotion,
                estimated_duration=5.0,
                style_tags=[style],
            )

    def _build_script_generation_prompt(
        self,
        scene_context: str,
        emotion: str,
        style: str,
        max_duration: Optional[float] = None,
    ) -> str:
        """构建脚本生成提示词"""
        duration_hint = f"建议时长: {max_duration:.1f}秒" if max_duration else ""

        return f"""请为以下场景生成解说脚本:

场景描述: {scene_context}
情感风格: {emotion}
解说风格: {style}
{duration_hint}

请返回JSON格式的脚本信息:
- script_id: 脚本唯一ID
- text: 生成的解说文本
- emotion: 情感分析
- estimated_duration: 预估时长（秒）
- style_tags: 风格标签列表"""

    def _parse_script_generation_response(self, response: str) -> ScriptGeneration:
        """解析脚本生成响应"""
        try:
            json_str = self._extract_json(response)
            if json_str:
                data = json.loads(json_str)
                return ScriptGeneration(
                    script_id=data.get("script_id", str(uuid.uuid4())),
                    text=data.get("text", ""),
                    emotion=data.get("emotion", "neutral"),
                    estimated_duration=data.get("estimated_duration", 5.0),
                    style_tags=data.get("style_tags", []),
                )
        except Exception as e:
            self.log_error(f"Failed to parse script generation response: {e}")

        # 降级处理
        return ScriptGeneration(
            script_id=str(uuid.uuid4()),
            text=response.strip() if response else "",
            emotion="neutral",
            estimated_duration=5.0,
            style_tags=[],
        )

    async def generate_script_stream(
        self,
        scene_context: str,
        emotion: str,
        style: str,
    ) -> AsyncIterator[str]:
        """
        流式生成脚本（实时预览）

        Yields:
            增量文本片段
        """
        prompt = self._build_script_generation_prompt(
            scene_context, emotion, style, None
        )

        try:
            async for chunk in self._call_deepseek_api_stream(prompt):
                yield chunk
        except Exception as e:
            self.log_error(f"Script streaming failed: {e}")
            yield "脚本生成失败，请稍后重试。"

    async def _call_deepseek_api(self, prompt: str) -> str:
        """调用 DeepSeek API"""
        from openai import AsyncOpenAI

        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
        )

        return response.choices[0].message.content or ""

    async def _call_deepseek_api_stream(self, prompt: str) -> AsyncIterator[str]:
        """调用 DeepSeek API（流式）"""
        from openai import AsyncOpenAI

        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取 JSON"""
        import re

        # 尝试提取 ```json ... ``` 块
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if json_match:
            return json_match.group(1).strip()

        # 尝试直接解析
        text = text.strip()
        if text.startswith("[") or text.startswith("{"):
            return text

        return None

    def configure(self, api_key: str, base_url: Optional[str] = None, model: Optional[str] = None) -> None:
        """
        配置插件参数

        Args:
            api_key: DeepSeek API 密钥
            base_url: API 基础 URL（可选）
            model: 模型名称（可选）
        """
        self._api_key = api_key
        if base_url:
            self._base_url = base_url
        if model:
            self._model = model

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": "DeepSeek AI 生成器，支持场景分析和脚本生成",
            "author": self.manifest.author,
            "provider": "DeepSeek",
            "features": [
                "场景分析 - 分析视频画面提取场景信息",
                "脚本生成 - 基于场景上下文生成解说词",
                "流式生成 - 实时预览脚本生成过程",
            ],
            "supported_emotions": [
                "neutral", "happy", "sad", "suspenseful",
                "motivational", "dramatic", "relaxed"
            ],
            "supported_styles": [
                "纪录片", "短视频", "电影解说", "新闻播报", "自媒体"
            ],
        }
