"""
AI 配音生成器 (Voice Generator)

将文本转换为高质量 AI 配音。

支持多种 TTS 后端:
- Azure Speech (推荐,支持情感)
- OpenAI TTS
- Edge TTS (免费)

使用示例:
    from app.services.ai import VoiceGenerator, VoiceConfig, VoiceStyle

    generator = VoiceGenerator(provider="edge")

    audio_path = generator.generate(
        text="欢迎观看这个视频",
        output_path="output.mp3",
        style=VoiceStyle.NARRATION,
    )
"""

import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from .voice_models import VoiceConfig, VoiceInfo, GeneratedVoice, VoiceStyle, VoiceGender
from ...utils.security import get_ffmpeg_executor

logger = logging.getLogger(__name__)
_audio_executor = get_ffmpeg_executor()



from .tts_providers import TTSProvider, EdgeTTSProvider, OpenAITTSProvider, F5TTSProvider

class VoiceGenerator:
    """
    AI 配音生成器

    统一的配音生成接口,支持多种 TTS 后端

    使用示例:
        # 使用免费的 Edge TTS
        generator = VoiceGenerator(provider="edge")

        # 使用 F5-TTS 音色克隆(需安装 pip install f5-tts)
        generator = VoiceGenerator(provider="f5tts")
        result = generator.generate(
            text="这是一段克隆音色的配音",
            output_path="cloned.mp3",
            config=VoiceConfig(
                ref_audio="/path/to/reference.wav",
                ref_text="这是参考音频里说的原始文本",
            ),
        )

        # 使用 OpenAI TTS
        generator = VoiceGenerator(provider="openai", api_key="sk-xxx")

        # 生成配音
        result = generator.generate(
            text="欢迎观看这个视频,今天我们来聊一聊AI的发展",
            output_path="voiceover.mp3",
        )
        print(f"配音时长: {result.duration:.2f}秒")
    """

    def __init__(
        self,
        provider: str = "edge",
        api_key: Optional[str] = None,
        **kwargs,
    ):
        """
        初始化配音生成器

        Args:
            provider: 提供者 ("edge", "openai", "azure")
            api_key: API Key(某些提供者需要)
        """
        self.provider_name = provider

        if provider == "edge":
            self._provider = EdgeTTSProvider()
        elif provider == "openai":
            key = api_key or os.getenv("OPENAI_API_KEY")
            if not key:
                raise ValueError("OpenAI TTS 需要 API Key")
            self._provider = OpenAITTSProvider(key)
        elif provider == "f5tts":
            self._provider = F5TTSProvider()
            if not getattr(self._provider, "_available", False):
                raise RuntimeError(
                    "F5-TTS 不可用(未安装或初始化失败)。\n"
                    "请运行: pip install f5-tts\n"
                    "或使用 provider='edge'"
                )
        else:
            raise ValueError(f"不支持的提供者: {provider}")

    def generate(
        self,
        text: str,
        output_path: str,
        config: Optional[VoiceConfig] = None,
    ) -> GeneratedVoice:
        """
        生成配音

        Args:
            text: 要转换的文本
            output_path: 输出文件路径
            config: 配音配置

        Returns:
            生成的配音信息
        """
        config = config or VoiceConfig()

        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        return self._provider.generate(text, output_path, config)

    def generate_segments(
        self,
        segments: List[Dict[str, Any]],
        output_dir: str,
        config: Optional[VoiceConfig] = None,
    ) -> List[GeneratedVoice]:
        """
        批量生成配音片段

        Args:
            segments: 片段列表,每个包含 text, start, duration
            output_dir: 输出目录
            config: 配音配置

        Returns:
            生成的配音列表
        """
        config = config or VoiceConfig()
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results = []

        for i, segment in enumerate(segments):
            text = segment.get("text", "")
            if not text:
                continue

            file_path = output_path / f"segment_{i:03d}.mp3"

            result = self.generate(text, str(file_path), config)

            # 保留原始时间信息
            result.start_time = segment.get("start", 0.0)

            results.append(result)

        return results

    def list_voices(self, language: str = "zh-CN") -> List[VoiceInfo]:
        """列出可用声音"""
        return self._provider.list_voices(language)

    def preview_voice(
        self,
        voice_id: str,
        text: str = "你好,这是一段语音测试。欢迎使用 AI 配音功能。",
        output_path: str = "preview.mp3",
    ) -> GeneratedVoice:
        """预览指定声音"""
        config = VoiceConfig(voice_id=voice_id)
        return self.generate(text, output_path, config)


# =========== 便捷函数 ===========

def generate_voice(
    text: str,
    output_path: str,
    provider: str = "edge",
    voice: Optional[str] = None,
    rate: float = 1.0,
) -> GeneratedVoice:
    """
    快速生成配音

    Args:
        text: 文本
        output_path: 输出路径
        provider: 提供者
        voice: 声音 ID
        rate: 语速
    """
    generator = VoiceGenerator(provider=provider)
    config = VoiceConfig(voice_id=voice or "", rate=rate)
    return generator.generate(text, output_path, config)
