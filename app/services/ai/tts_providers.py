"""
TTS 提供者实现

包含 EdgeTTS、OpenAI TTS、F5-TTS 等多种后端实现。
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

from .voice_models import VoiceStyle, VoiceGender, VoiceConfig, VoiceInfo, GeneratedVoice
from ...utils.security import get_ffmpeg_executor, SecurityError

logger = logging.getLogger(__name__)
_audio_executor = get_ffmpeg_executor()

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

    def _get_audio_duration(self, audio_path: str) -> float:
        """统一获取音频时长（子模块如有更优实现可覆盖）"""
        # 优先用 pydub（适合本地 wav/mp3）
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0
        except ImportError:
            logger.debug("pydub not available, falling back to ffprobe")
        except Exception as e:
            logger.debug(f"pydub failed for {audio_path}: {e}")

        # ffprobe 兜底
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0', audio_path
            ]
            result = _audio_executor.run(cmd, timeout=30)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except FileNotFoundError:
            logger.debug("ffprobe not found")
        except SecurityError as e:
            logger.warning(f"ffprobe failed: {e}")
        except Exception as e:
            logger.debug(f"Getting audio duration failed: {e}")
        return 0.0


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
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-codec:a", "libmp3lame", "-q:a", "2",
            output_path,
        ]
        _audio_executor.run(cmd, timeout=60)

    def list_voices(self, language: str = "zh-CN") -> List[VoiceInfo]:
        """
        列出可用"声音"(音色克隆模式下实际返回已注册的参考音频)
        F5-TTS 本身无预设声音库,需用户提供参考音频进行克隆。
        """
        # 当无可用参考时返回空列表
        return []

