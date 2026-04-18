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

import os
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from abc import ABC, abstractmethod
import logging
logger = logging.getLogger(__name__)

from .voice_models import VoiceStyle, VoiceGender, VoiceConfig, VoiceInfo, GeneratedVoice


class TTSProvider(ABC):
    """TTS 提供者抽象基类"""

    @abstractmethod
    def generate(
        self,
        text: str,
        output_path: str,
        config: VoiceConfig,
    ) -> GeneratedVoice:
        """生成配音"""
        pass

    @abstractmethod
    def list_voices(self, language: str = "zh-CN") -> List[VoiceInfo]:
        """列出可用声音"""
        pass


class EdgeTTSProvider(TTSProvider):
    """
    Edge TTS 提供者(免费)

    使用微软 Edge 的 TTS 服务,无需 API Key

    安装: pip install edge-tts
    """

    # 中文推荐声音
    CHINESE_VOICES = {
        "female": [
            ("zh-CN-XiaoxiaoNeural", "晓晓 - 温柔女声"),
            ("zh-CN-XiaoyiNeural", "晓依 - 知性女声"),
            ("zh-CN-XiaohanNeural", "晓涵 - 甜美女声"),
            ("zh-CN-XiaomoNeural", "晓墨 - 成熟女声"),
            ("zh-CN-XiaoxuanNeural", "晓萱 - 活泼女声"),
            ("zh-CN-XiaoruiNeural", "晓睿 - 少女音"),
        ],
        "male": [
            ("zh-CN-YunxiNeural", "云希 - 阳光男声"),
            ("zh-CN-YunjianNeural", "云健 - 磁性男声"),
            ("zh-CN-YunyangNeural", "云扬 - 新闻播报"),
        ],
    }

    def __init__(self):
        try:
            import edge_tts
            self.edge_tts = edge_tts
        except ImportError:
            raise ImportError("请安装 edge-tts: pip install edge-tts")

    def generate(
        self,
        text: str,
        output_path: str,
        config: VoiceConfig,
    ) -> GeneratedVoice:
        """生成配音，并捕获句子级时间戳"""
        # 选择声音
        voice = config.voice_id or self._select_voice(config)

        # 构建语速/音调参数
        rate_str = f"+{int((config.rate - 1) * 100)}%" if config.rate >= 1 else f"{int((config.rate - 1) * 100)}%"
        pitch_str = f"+{int((config.pitch - 1) * 50)}Hz" if config.pitch >= 1 else f"{int((config.pitch - 1) * 50)}Hz"

        # 异步生成（同时收集时间戳）
        sentence_timestamps: List[Dict[str, Any]] = []

        async def _generate():
            nonlocal sentence_timestamps
            communicate = self.edge_tts.Communicate(
                text,
                voice,
                rate=rate_str,
                pitch=pitch_str,
            )

            submaker = self.edge_tts.SubMaker()
            audio_chunks = []

            async for chunk in communicate.stream():
                if chunk["type"] == "SentenceBoundary":
                    submaker.feed(chunk)
                    # 转换为秒（offset/duration 单位是 100-nanoseconds）
                    start_s = chunk["offset"] / 10_000_000
                    end_s = (chunk["offset"] + chunk["duration"]) / 10_000_000
                    sentence_timestamps.append({
                        "text": chunk["text"],
                        "start": start_s,
                        "end": end_s,
                    })
                elif chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

            # 写入音频文件
            with open(output_path, "wb") as f:
                for chunk in audio_chunks:
                    f.write(chunk)

        # 避免 asyncio.run() 与已有 event loop 冲突
        try:
            asyncio.get_running_loop()
            # 已有 loop，在新线程中运行（EdgeTTS 必须在自己的 loop 中）
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(asyncio.run, _generate()).result()
        except RuntimeError:
            # 没有运行中的 loop，可以安全用 asyncio.run()
            asyncio.run(_generate())

        # 获取音频时长
        duration = self._get_audio_duration(output_path)

        return GeneratedVoice(
            audio_path=output_path,
            duration=duration,
            text=text,
            voice_id=voice,
            format=config.output_format,
            sentence_timestamps=sentence_timestamps,
        )

    def _select_voice(self, config: VoiceConfig) -> str:
        """根据配置选择声音"""
        gender_key = config.gender.value
        voices = self.CHINESE_VOICES.get(gender_key, self.CHINESE_VOICES["female"])

        # 根据风格选择
        if config.style == VoiceStyle.NEWSCAST:
            return "zh-CN-YunyangNeural"  # 新闻播报
        elif config.style == VoiceStyle.CHEERFUL:
            return "zh-CN-XiaoxuanNeural"  # 活泼
        elif config.style == VoiceStyle.CONVERSATIONAL:
            return "zh-CN-XiaoxiaoNeural"  # 对话
        else:
            return voices[0][0]  # 默认第一个

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0  # 毫秒转秒
        except ImportError:
            logger.debug("pydub not available for duration, falling back to ffprobe")

        # 使用 ffprobe
        try:
            import subprocess
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception:
            logger.debug("Operation failed")

        return 0.0

    def list_voices(self, language: str = "zh-CN") -> List[VoiceInfo]:
        """列出可用声音"""
        voices = []

        for voice_id, name in self.CHINESE_VOICES["female"]:
            voices.append(VoiceInfo(
                id=voice_id,
                name=name,
                gender=VoiceGender.FEMALE,
                language=language,
            ))

        for voice_id, name in self.CHINESE_VOICES["male"]:
            voices.append(VoiceInfo(
                id=voice_id,
                name=name,
                gender=VoiceGender.MALE,
                language=language,
            ))

        return voices


class OpenAITTSProvider(TTSProvider):
    """
    OpenAI TTS 提供者

    使用 OpenAI 的 TTS API
    """

    VOICES = {
        "alloy": "Alloy - 中性",
        "echo": "Echo - 男声",
        "fable": "Fable - 英式男声",
        "onyx": "Onyx - 低沉男声",
        "nova": "Nova - 温柔女声",
        "shimmer": "Shimmer - 清脆女声",
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")

    def generate(
        self,
        text: str,
        output_path: str,
        config: VoiceConfig,
    ) -> GeneratedVoice:
        """生成配音"""
        voice = config.voice_id or "nova"  # 默认 nova

        # 语速映射 (OpenAI TTS 不支持精确控制,只能通过 SSML 或模型选择)
        speed = min(max(config.rate, 0.25), 4.0)

        response = self.client.audio.speech.create(
            model="tts-1-hd",
            voice=voice,
            input=text,
            speed=speed,
        )

        # 保存文件
        response.stream_to_file(output_path)

        # 获取时长
        duration = self._get_audio_duration(output_path)

        return GeneratedVoice(
            audio_path=output_path,
            duration=duration,
            text=text,
            voice_id=voice,
            format=config.output_format,
            sentence_timestamps=[],
        )

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        try:
            import subprocess
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception:
            logger.debug("Operation failed")
        return 0.0

    def list_voices(self, language: str = "zh-CN") -> List[VoiceInfo]:
        """列出可用声音"""
        return [
            VoiceInfo(id=vid, name=name, gender=VoiceGender.FEMALE, language="en-US")
            for vid, name in self.VOICES.items()
        ]


class F5TTSProvider(TTSProvider):
    """
    F5-TTS 提供者(零样本音色克隆)

    基于开源 F5-TTS 模型,支持从 15-30 秒参考音频克隆任意音色。

    安装: pip install f5-tts
    设备: 自动检测 CUDA / CPU

    使用示例:
        provider = F5TTSProvider()
        result = provider.generate(
            text="这是一段新生成的语音",
            output_path="output.wav",
            config=VoiceConfig(
                ref_audio="/path/to/reference.wav",
                ref_text="这是参考音频中的原始文本内容",
            ),
        )
    """

    def __init__(self):
        self._f5_tts = None
        self._available = False
        try:
            from f5_tts import F5TTS
            # 自动检测设备
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._f5_tts = F5TTS(device=device)
            self._available = True
            logger.info(f"F5-TTS initialized on {device}")
        except ImportError:
            logger.warning(
                "F5-TTS 未安装。安装命令: pip install f5-tts\n"
                "音色克隆功能不可用,将回退到 Edge-TTS"
            )
        except Exception as e:
            logger.warning(f"F5-TTS 初始化失败: {e}")

    @property
    def is_available(self) -> bool:
        """F5-TTS 是否可用"""
        return self._available

    def generate(
        self,
        text: str,
        output_path: str,
        config: VoiceConfig,
    ) -> GeneratedVoice:
        """使用 F5-TTS 生成配音(支持音色克隆)"""
        if not self._available:
            raise RuntimeError(
                "F5-TTS 未安装或初始化失败。\n"
                "请运行: pip install f5-tts\n"
                "或使用 provider='edge' 回退到 Edge-TTS"
            )

        ref_audio = getattr(config, "ref_audio", None)
        ref_text = getattr(config, "ref_text", "")

        if not ref_audio:
            raise ValueError(
                "F5-TTS 需要 ref_audio 参数(参考音频路径)。\n"
                "建议: 提供 15-30 秒的清晰人声作为音色参考。"
            )

        ref_audio_path = Path(ref_audio)
        if not ref_audio_path.exists():
            raise FileNotFoundError(f"参考音频不存在: {ref_audio}")

        # 生成
        self._f5_tts.generate(
            text=text,
            ref_audio=str(ref_audio_path),
            ref_text=ref_text,
            output_path=output_path,
        )

        # 转码为 MP3(如果需要)
        output_path = Path(output_path)
        if config.output_format != "wav" and output_path.suffix.lower() == ".wav":
            mp3_path = output_path.with_suffix(".mp3")
            self._convert_to_mp3(str(output_path), str(mp3_path))
            output_path = mp3_path

        duration = self._get_audio_duration(str(output_path))

        return GeneratedVoice(
            audio_path=str(output_path),
            duration=duration,
            text=text,
            voice_id=f"f5tts://{ref_audio_path.stem}",
            format=config.output_format,
            sentence_timestamps=[],
        )

    def _convert_to_mp3(self, input_path: str, output_path: str) -> None:
        """将 WAV 转码为 MP3"""
        import subprocess
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-codec:a", "libmp3lame", "-q:a", "2",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True)

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长"""
        try:
            import subprocess
            cmd = [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0", audio_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            logger.debug(f"ffprobe duration failed for {audio_path}: {e}")
        return 0.0

    def list_voices(self, language: str = "zh-CN") -> List[VoiceInfo]:
        """
        列出可用"声音"(音色克隆模式下实际返回已注册的参考音频)
        F5-TTS 本身无预设声音库,需用户提供参考音频进行克隆。
        """
        # 当无可用参考时返回空列表
        return []


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


def demo_generate():
    """演示配音生成"""
    print("=" * 50)
    print("AI 配音生成演示")
    print("=" * 50)

    # 使用免费的 Edge TTS
    generator = VoiceGenerator(provider="edge")

    # 列出可用声音
    print("\n可用声音:")
    for voice in generator.list_voices():
        print(f"  - {voice.id}: {voice.name}")

    # 生成配音
    text = """
    欢迎来到 Voxplore!
    这是一款 AI 驱动的视频创作工具。
    让我们一起创作爆款视频吧!
    """

    print("\n正在生成配音...")
    result = generator.generate(
        text=text.strip(),
        output_path="demo_voice.mp3",
        config=VoiceConfig(
            voice_id="zh-CN-XiaoxiaoNeural",
            rate=1.1,
        )
    )

    print("\n✅ 配音生成成功!")
    print(f"   文件: {result.audio_path}")
    print(f"   时长: {result.duration:.2f}秒")
    print(f"   声音: {result.voice_id}")


if __name__ == '__main__':
    demo_generate()
