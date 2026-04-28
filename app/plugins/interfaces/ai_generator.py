"""
AI Generator Plugin Interface
AI 生成器插件接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncIterator
from dataclasses import dataclass
from app.plugins.interfaces.base import BasePlugin, PluginType


@dataclass
class SceneAnalysis:
    """场景分析结果"""
    scene_id: str
    scene_type: str           # indoor, outdoor, transition
    location: str             # 地点
    atmosphere: str           # 氛围
    subjects: List[Dict]       # 主体
    key_objects: List[str]    # 关键物体
    importance: float          # 叙事重要性 0-1


@dataclass
class ScriptGeneration:
    """脚本生成结果"""
    script_id: str
    text: str
    emotion: str
    estimated_duration: float
    style_tags: List[str]


class BaseAIGeneratorPlugin(ABC, BasePlugin):
    """
    AI 生成器插件基类

    实现此接口以添加新的 AI 模型支持:
    - 场景分析
    - 脚本生成
    - 语音合成
    """

    plugin_type = PluginType.AI_GENERATOR

    @abstractmethod
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
        ...

    @abstractmethod
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
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """获取 AI Provider 名称"""
        ...

    @abstractmethod
    def get_capabilities(self) -> Dict[str, bool]:
        """
        获取插件能力

        Returns:
            {
                "scene_analysis": bool,
                "script_generation": bool,
                "streaming": bool,
                "voice_synthesis": bool,
            }
        """
        ...
