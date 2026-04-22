#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 服务接口定义

使用 Protocol 定义结构化子类型接口（新 Python 3.8+ 风格），
无需继承即可满足类型检查，实现解耦。

活跃接口:
- IVideoMaker: 视频制作器标准接口
- IScriptGenerator: 文案生成器标准接口
- IVoiceGenerator: 语音生成器标准接口
- ISceneAnalyzer: 场景分析器标准接口

使用示例:
    from app.services.interfaces import IVideoMaker, IScriptGenerator

    def process_video(maker: IVideoMaker, video_path: str) -> str:
        project = maker.create_project(source_video=video_path)
        maker.generate_script(project)
        maker.generate_voice(project)
        return maker.export_to_jianying(project)

    # 任意实现了相同方法的类都可以传入:
    process_video(MonologueMaker(), "video.mp4")
"""

from typing import Protocol, runtime_checkable, Optional, List, Any, Callable


# =============================================================================
# 进度回调类型
# =============================================================================
ProgressCallback = Callable[[str, float], None]
"""进度回调: (stage_name: str, progress: float 0.0-1.0) -> None"""


# =============================================================================
# IVideoMaker — 视频制作器标准接口
# =============================================================================
@runtime_checkable
class IVideoMaker(Protocol):
    """
    视频制作器标准接口

    所有视频制作器（MonologueMaker, MashupMaker 等）都应实现此接口。

    接口契约:
    1. 创建项目（输入源视频 + 上下文）
    2. 生成文案（脚本/解说词）
    3. 生成配音（语音合成）
    4. 生成字幕
    5. 导出到目标格式
    6. 支持进度回调
    """

    def create_project(
        self,
        source_video: str,
        context: str = "",
        **kwargs,
    ) -> Any:
        """
        创建视频项目

        Args:
            source_video: 源视频文件路径
            context: 场景/情境描述
            **kwargs: 额外参数（如 emotion, style 等）

        Returns:
            项目对象（具体类型由实现定义）
        """
        ...

    def generate_script(
        self,
        project: Any,
        custom_script: Optional[str] = None,
    ) -> None:
        """
        生成视频文案/解说词

        Args:
            project: 项目对象（来自 create_project）
            custom_script: 可选的自定义文案，为空则使用 AI 生成
        """
        ...

    def generate_voice(
        self,
        project: Any,
        voice_config: Optional[Any] = None,
    ) -> None:
        """
        生成语音配音

        Args:
            project: 项目对象
            voice_config: 可选的语音配置
        """
        ...

    def generate_captions(
        self,
        project: Any,
        style: str = "cinematic",
    ) -> None:
        """
        生成字幕

        Args:
            project: 项目对象
            style: 字幕样式 ("cinematic", "minimal", "expressive")
        """
        ...

    def export_to_jianying(
        self,
        project: Any,
        output_dir: str,
    ) -> str:
        """
        导出项目到剪映草稿

        Args:
            project: 项目对象
            output_dir: 剪映草稿输出目录

        Returns:
            导出的草稿路径
        """
        ...

    def set_progress_callback(
        self,
        callback: Optional[ProgressCallback],
    ) -> None:
        """
        设置进度回调

        Args:
            callback: 回调函数，签名为 (stage: str, progress: float)
        """
        ...


# =============================================================================
# IScriptGenerator — 文案生成器标准接口
# =============================================================================
@runtime_checkable
class IScriptGenerator(Protocol):
    """
    AI 文案生成器标准接口

    所有文案生成器（ScriptGenerator, StreamingScriptGenerator 等）都应实现此接口。
    """

    def generate(
        self,
        topic: str,
        style: Any,
        duration: float,
        **kwargs,
    ) -> Any:
        """
        生成文案

        Args:
            topic: 主题/话题描述
            style: 文案风格（ScriptStyle 枚举）
            duration: 目标时长（秒）
            **kwargs: 额外参数

        Returns:
            生成的文案对象（具体类型由实现定义）
        """
        ...

    def generate_segments(
        self,
        content: str,
        max_duration: float = 10.0,
    ) -> List[Any]:
        """
        将完整文案切分为片段

        Args:
            content: 完整文案
            max_duration: 每段最大时长（秒）

        Returns:
            片段列表
        """
        ...


# =============================================================================
# IVoiceGenerator — 语音生成器标准接口
# =============================================================================
@runtime_checkable
class IVoiceGenerator(Protocol):
    """
    语音生成器标准接口

    所有语音生成器（VoiceGenerator, F5VoiceGenerator 等）都应实现此接口。
    """

    def generate(
        self,
        text: str,
        output_path: str,
        voice_config: Optional[Any] = None,
    ) -> str:
        """
        生成语音文件

        Args:
            text: 要朗读的文本
            output_path: 输出音频文件路径
            voice_config: 语音配置（声音、语速等）

        Returns:
            生成的音频文件路径
        """
        ...

    def generate_segments(
        self,
        segments: List[Any],
        output_dir: str,
        voice_config: Optional[Any] = None,
    ) -> List[str]:
        """
        批量生成多段语音

        Args:
            segments: 文本片段列表
            output_dir: 输出目录
            voice_config: 语音配置

        Returns:
            生成的音频文件路径列表
        """
        ...


# =============================================================================
# ISceneAnalyzer — 场景分析器标准接口
# =============================================================================
@runtime_checkable
class ISceneAnalyzer(Protocol):
    """
    场景分析器标准接口

    所有场景分析器（SceneAnalyzer, SceneAnalyzerV2 等）都应实现此接口。
    """

    def analyze(
        self,
        video_path: str,
    ) -> List[Any]:
        """
        分析视频场景

        Args:
            video_path: 视频文件路径

        Returns:
            场景列表（List[SceneInfo]）
        """
        ...

    def get_best_scenes(
        self,
        scenes: List[Any],
        count: int = 10,
        min_score: float = 50.0,
    ) -> List[Any]:
        """
        获取最佳场景

        Args:
            scenes: 场景列表
            count: 返回数量
            min_score: 最低分数

        Returns:
            排序后的最佳场景列表
        """
        ...
