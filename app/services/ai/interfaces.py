#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Provider 接口定义

定义 Vision、LLM、TTS 三类 AI Provider 的协议接口。
实现这些协议即可接入自定义的 AI 模型。
"""

from typing import Protocol, runtime_checkable
from dataclasses import dataclass


@dataclass
class VideoAnalysis:
    """视频分析结果"""
    summary: str
    tags: list[str]
    scene_changes: list[float]


@dataclass
class ScriptResult:
    """脚本生成结果"""
    script: str
    style: str
    character: str | None


@dataclass
class AudioData:
    """音频数据"""
    audio_bytes: bytes
    duration_ms: int
    format: str


@runtime_checkable
class VisionProvider(Protocol):
    """视觉理解 Provider

    实现此协议以接入自定义视觉模型（如 Qwen2.5-VL、GPT-5 Vision 等）。
    """

    def analyze_video(self, video_path: str) -> VideoAnalysis:
        """分析视频内容

        Args:
            video_path: 视频文件路径

        Returns:
            VideoAnalysis: 包含摘要、标签、场景变化点的分析结果
        """
        ...

    def extract_keyframes(self, video_path: str, count: int) -> list[bytes]:
        """提取关键帧

        Args:
            video_path: 视频文件路径
            count: 目标关键帧数量

        Returns:
            list[bytes]: 关键帧图像数据列表
        """
        ...


@runtime_checkable
class LLMProvider(Protocol):
    """大语言 Model Provider

    实现此协议以接入自定义 LLM（如 DeepSeek、Qwen、GPT 等）。
    """

    def generate_script(self, prompt: str, style: str | None = None) -> ScriptResult:
        """生成视频脚本

        Args:
            prompt: 生成提示词
            style: 脚本风格（如 "narrative", "commentary"）

        Returns:
            ScriptResult: 包含脚本内容、风格、角色的结果
        """
        ...

    def generate_narration(self, context: str, character: str | None = None) -> str:
        """生成解说文案

        Args:
            context: 上下文信息
            character: 角色设定（如 "年轻女性"、"旁白"）

        Returns:
            str: 生成的解说文案
        """
        ...


@runtime_checkable
class TTSProvider(Protocol):
    """文本转语音 Provider

    实现此协议以接入自定义 TTS 服务（如 Edge-TTS、F5-TTS、Azure TTS 等）。
    """

    def synthesize(self, text: str, voice: str | None = None) -> AudioData:
        """文本转语音

        Args:
            text: 待合成文本
            voice: 声音标识（如 "zh-CN-Xiaoxiao"）

        Returns:
            AudioData: 包含音频数据、时长、格式的结果
        """
        ...

    def synthesize_with_timing(self, text: str, word_timings: list[float]) -> AudioData:
        """带词级别时间戳的语音合成

        Args:
            text: 待合成文本
            word_timings: 每个词对应的时间戳（秒）

        Returns:
            AudioData: 包含音频数据和格式的结果
        """
        ...
