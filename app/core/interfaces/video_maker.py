#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 核心抽象接口

定义项目中的关键抽象（Protocol），确保：
1. 接口与实现分离
2. 可替换性（不同 LLM Provider、不同 TTS 引擎）
3. 可测试性（Mock 实现的依据）

接口层次：
    IVideoMaker      — 视频制作器（Protocol）
    IScriptGenerator — 文案生成器（Protocol）
    IVoiceGenerator  — 语音生成器（Protocol）
    IExporter        — 导出器（Protocol）

使用示例:
    from app.core.interfaces import IVideoMaker, IScriptGenerator

    # 检查类是否实现接口（延迟导入避免循环依赖）
    import warnings
    def _get_monologue_maker():
        from app.services.video.monologue_maker import MonologueMaker
        return MonologueMaker
    assert isinstance(_get_monologue_maker()(), IVideoMaker)

    # 运行时协议检查
    from typing import runtime_checkable
    @runtime_checkable
    class MockVideoMaker(IVideoMaker):
        ...
"""

from typing import Protocol, Optional, List, runtime_checkable
from typing_extensions import Self


# =============================================================================
# 视频制作器接口
# =============================================================================
@runtime_checkable
class IVideoMaker(Protocol):
    """
    视频制作器接口

    定义视频制作器的核心契约。任何实现此接口的类都可以
    被用作 Voxplore 的视频制作后端。

    当前实现：MonologueMaker（第一人称独白）

    接口契约：
        1. 创建项目（分析视频 + 初始化项目）
        2. 生成文案（AI 驱动）
        3. 生成语音（AI 驱动）
        4. 生成字幕
        5. 导出到目标格式
    """

    def create_project(
        self,
        source_video: str,
        name: Optional[str] = None,
        output_dir: Optional[str] = None,
        **kwargs,
    ) -> Self:
        """分析视频并创建项目。返回项目对象。"""
        ...

    def generate_script(
        self,
        project: Self,
        custom_script: Optional[str] = None,
        **kwargs,
    ) -> Self:
        """为项目生成解说/独白文案。返回更新后的项目。"""
        ...

    def generate_voice(
        self,
        project: Self,
        **kwargs,
    ) -> Self:
        """为项目生成 AI 配音。返回更新后的项目。"""
        ...

    def generate_captions(
        self,
        project: Self,
        style: str = "cinematic",
        **kwargs,
    ) -> Self:
        """为项目生成字幕。返回更新后的项目。"""
        ...

    def export_to_jianying(
        self,
        project: Self,
        output_dir: str,
        **kwargs,
    ) -> str:
        """
        导出到剪映草稿格式

        Args:
            project: 项目对象
            output_dir: 剪映草稿目录

        Returns:
            草稿目录路径
        """
        ...


# =============================================================================
# 文案生成器接口
# =============================================================================
@runtime_checkable
class IScriptGenerator(Protocol):
    """
    AI 文案生成器接口

    定义文案生成器的契约。支持多 LLM 提供商。

    接口契约：
        1. 同步生成文案
        2. 流式生成文案（可选）
        3. 支持多种风格（解说/独白/爆款）
    """

    def generate(
        self,
        topic: str,
        style: str = "commentary",
        duration: Optional[float] = None,
        **kwargs,
    ) -> object:
        """
        生成文案

        Args:
            topic: 主题/视频内容描述
            style: 文案风格 ("commentary" | "monologue" | "viral")
            duration: 目标时长（秒）

        Returns:
            GeneratedScript 对象（包含 content, segments 等）
        """
        ...

    def generate_streaming(
        self,
        topic: str,
        style: str = "commentary",
        duration: Optional[float] = None,
        **kwargs,
    ):
        """
        流式生成文案（生成器）

        Args:
            topic: 主题/视频内容描述
            style: 文案风格
            duration: 目标时长（秒）

        Yields:
            str: 增量生成的文本片段
        """
        ...


# =============================================================================
# 语音生成器接口
# =============================================================================
@runtime_checkable
class IVoiceGenerator(Protocol):
    """
    AI 语音生成器接口

    定义语音生成的契约。支持多种 TTS 引擎。

    接口契约：
        1. 生成语音文件
        2. 支持多种声音风格
    """

    def generate(
        self,
        text: str,
        output_path: Optional[str] = None,
        voice_config: Optional[object] = None,
        **kwargs,
    ) -> str:
        """
        将文本转换为语音

        Args:
            text: 要转换的文本
            output_path: 输出音频文件路径
            voice_config: 声音配置

        Returns:
            生成的音频文件路径
        """
        ...

    def generate_batch(
        self,
        texts: List[str],
        output_dir: str,
        voice_config: Optional[object] = None,
        **kwargs,
    ) -> List[str]:
        """
        批量生成语音

        Args:
            texts: 文本列表
            output_dir: 输出目录
            voice_config: 声音配置

        Returns:
            生成的音频文件路径列表
        """
        ...


# =============================================================================
# 导出器接口
# =============================================================================
@runtime_checkable
class IExporter(Protocol):
    """
    视频导出器接口

    定义导出器的契约。

    接口契约：
        1. 创建草稿/项目
        2. 添加轨道/素材
        3. 执行导出
    """

    def create_draft(self, name: str, **kwargs) -> object:
        """创建导出草稿/项目"""
        ...

    def export(
        self,
        draft: object,
        output_dir: str,
        **kwargs,
    ) -> str:
        """
        执行导出

        Args:
            draft: 草稿对象
            output_dir: 输出目录

        Returns:
            导出后的文件/目录路径
        """
        ...


__all__ = [
    "IVideoMaker",
    "IScriptGenerator",
    "IVoiceGenerator",
    "IExporter",
]
