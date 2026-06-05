"""
PilotTTS Provider

2026年新开源 TTS 方案，支持：
- 指令级情感控制（11 种情绪）
- 14 种方言
- 零样本音色克隆
- 中文为主

GitHub: https://github.com/PilotTTS/PilotTTS
"""

import logging
import os
from pathlib import Path
from typing import Any

import httpx

from .tts_providers import TTSProvider
from .voice_models import (
    GeneratedVoice,
    VoiceConfig,
    VoiceGender,
    VoiceInfo,
    VoiceStyle,
)

logger = logging.getLogger(__name__)


class PilotTTSProvider(TTSProvider):
    """
    PilotTTS 语音合成 Provider

    核心能力：
    - 11 种情绪控制（neutral, happy, sad, angry, fearful, disgusted, surprised, calm, excited, romantic, tense）
    - 14 种方言（普通话、粤语、四川话、东北话等）
    - 零样本音色克隆（15-30 秒参考音频）
    - 中文为主，支持英文
    """

    # 情绪映射
    EMOTIONS = {
        "neutral": "neutral",
        "happy": "happy",
        "sad": "sad",
        "angry": "angry",
        "fearful": "fearful",
        "disgusted": "disgusted",
        "surprised": "surprised",
        "calm": "calm",
        "excited": "excited",
        "romantic": "romantic",
        "tense": "tense",
    }

    # 方言映射
    DIALECTS = {
        "mandarin": "普通话",
        "cantonese": "粤语",
        "sichuan": "四川话",
        "dongbei": "东北话",
        "henan": "河南话",
        "hunan": "湖南话",
        "jiangxi": "江西话",
        "fujian": "福建话",
        "shanghai": "上海话",
        "shandong": "山东话",
        "shaanxi": "陕西话",
        "hubei": "湖北话",
        "anhui": "安徽话",
        "jiangsu": "江苏话",
    }

    # 预设声音库
    PRESET_VOICES = [
        VoiceInfo(
            id="pilot_male_01",
            name="男声-标准",
            language="zh-CN",
            gender=VoiceGender.MALE,
            styles=["neutral"],
            description="标准普通话男声",
        ),
        VoiceInfo(
            id="pilot_female_01",
            name="女声-标准",
            language="zh-CN",
            gender=VoiceGender.FEMALE,
            styles=["neutral"],
            description="标准普通话女声",
        ),
        VoiceInfo(
            id="pilot_male_02",
            name="男声-磁性",
            language="zh-CN",
            gender=VoiceGender.MALE,
            styles=["calm"],
            description="磁性低沉男声",
        ),
        VoiceInfo(
            id="pilot_female_02",
            name="女声-甜美",
            language="zh-CN",
            gender=VoiceGender.FEMALE,
            styles=["happy"],
            description="甜美活泼女声",
        ),
    ]

    def __init__(
        self,
        api_key: str = "",
        api_base: str = "http://localhost:8080",
        model: str = "pilot-tts-v1",
    ):
        """
        初始化 PilotTTS Provider

        Args:
            api_key: API Key（本地部署可为空）
            api_base: API 基础 URL
            model: 模型名称
        """
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.client = httpx.Client(timeout=60.0)

        logger.info(f"PilotTTS Provider 初始化完成: {model}")

    def generate(
        self,
        text: str,
        output_path: str,
        config: VoiceConfig,
    ) -> GeneratedVoice:
        """
        生成配音

        Args:
            text: 要合成的文本
            output_path: 输出音频文件路径
            config: 声音配置

        Returns:
            GeneratedVoice: 生成的配音信息
        """
        try:
            # 构建请求
            url = f"{self.api_base}/v1/audio/speech"
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            # 获取情绪和方言
            emotion = self.EMOTIONS.get(config.style.value, "neutral")
            dialect = "普通话"  # 默认普通话

            payload = {
                "model": self.model,
                "input": text,
                "voice": config.voice_id or "pilot_male_01",
                "emotion": emotion,
                "dialect": dialect,
                "speed": config.rate,
                "pitch": config.pitch,
            }

            # 如果有参考音频，添加音色克隆参数
            if config.ref_audio:
                payload["ref_audio"] = config.ref_audio

            # 调用 API
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            # 保存音频文件
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path_obj, "wb") as f:
                f.write(response.content)

            # 获取音频时长
            duration = self._get_audio_duration(output_path)

            return GeneratedVoice(
                audio_path=output_path,
                duration=duration,
                text=text,
                voice_id=config.voice_id or "pilot_male_01",
                sample_rate=24000,
                format="mp3",
            )

        except Exception as e:
            logger.error(f"PilotTTS 生成失败: {e}")
            raise

    def list_voices(self, language: str = "zh-CN") -> list[VoiceInfo]:
        """列出可用声音"""
        return [v for v in self.PRESET_VOICES if language in v.language]

    def clone_voice(
        self,
        ref_audio_path: str,
        text: str,
        output_path: str,
        emotion: str = "neutral",
    ) -> GeneratedVoice:
        """
        零样本音色克隆

        Args:
            ref_audio_path: 参考音频路径（15-30 秒）
            text: 要合成的文本
            output_path: 输出路径
            emotion: 情绪

        Returns:
            GeneratedVoice: 生成的配音
        """
        config = VoiceConfig(
            voice_id="clone",
            ref_audio=ref_audio_path,
            style=VoiceStyle.NARRATION,
        )
        return self.generate(text, output_path, config)


class OmniVoiceProvider(TTSProvider):
    """
    OmniVoice 语音合成 Provider

    核心能力：
    - 600+ 语言支持
    - 零样本克隆 + 声音设计（性别/年龄/音高/方言/气声）
    - 本地 GPU 部署

    GitHub: https://github.com/OmniVoice/OmniVoice
    """

    # 预设声音库
    PRESET_VOICES = [
        VoiceInfo(
            id="omni_male_01",
            name="男声-通用",
            language="multi",
            gender=VoiceGender.MALE,
            styles=["neutral"],
            description="多语言通用男声",
        ),
        VoiceInfo(
            id="omni_female_01",
            name="女声-通用",
            language="multi",
            gender=VoiceGender.FEMALE,
            styles=["neutral"],
            description="多语言通用女声",
        ),
    ]

    def __init__(
        self,
        api_key: str = "",
        api_base: str = "http://localhost:8081",
        model: str = "omnivoice-v1",
    ):
        """
        初始化 OmniVoice Provider

        Args:
            api_key: API Key
            api_base: API 基础 URL
            model: 模型名称
        """
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.client = httpx.Client(timeout=60.0)

        logger.info(f"OmniVoice Provider 初始化完成: {model}")

    def generate(
        self,
        text: str,
        output_path: str,
        config: VoiceConfig,
    ) -> GeneratedVoice:
        """生成配音"""
        try:
            url = f"{self.api_base}/v1/audio/speech"
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {
                "model": self.model,
                "input": text,
                "voice": config.voice_id or "omni_male_01",
                "speed": config.rate,
                "pitch": config.pitch,
            }

            # 音色克隆
            if config.ref_audio:
                payload["ref_audio"] = config.ref_audio

            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path_obj, "wb") as f:
                f.write(response.content)

            duration = self._get_audio_duration(output_path)

            return GeneratedVoice(
                audio_path=output_path,
                duration=duration,
                text=text,
                voice_id=config.voice_id or "omni_male_01",
                sample_rate=24000,
                format="mp3",
            )

        except Exception as e:
            logger.error(f"OmniVoice 生成失败: {e}")
            raise

    def list_voices(self, language: str = "zh-CN") -> list[VoiceInfo]:
        """列出可用声音"""
        return self.PRESET_VOICES


class IndexTTS2Provider(TTSProvider):
    """
    IndexTTS2 语音合成 Provider

    核心能力：
    - 精确时长控制
    - 情感表达
    - 零样本音色克隆
    - 中文 + 英文 + 混合

    GitHub: https://github.com/IndexTTS/IndexTTS2
    """

    # 预设声音库
    PRESET_VOICES = [
        VoiceInfo(
            id="index_male_01",
            name="男声-标准",
            language="zh-CN",
            gender=VoiceGender.MALE,
            styles=["neutral"],
            description="标准中文男声",
        ),
        VoiceInfo(
            id="index_female_01",
            name="女声-标准",
            language="zh-CN",
            gender=VoiceGender.FEMALE,
            styles=["neutral"],
            description="标准中文女声",
        ),
    ]

    def __init__(
        self,
        api_key: str = "",
        api_base: str = "http://localhost:8082",
        model: str = "indextts2-v1",
    ):
        """
        初始化 IndexTTS2 Provider

        Args:
            api_key: API Key
            api_base: API 基础 URL
            model: 模型名称
        """
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.client = httpx.Client(timeout=60.0)

        logger.info(f"IndexTTS2 Provider 初始化完成: {model}")

    def generate(
        self,
        text: str,
        output_path: str,
        config: VoiceConfig,
    ) -> GeneratedVoice:
        """生成配音"""
        try:
            url = f"{self.api_base}/v1/audio/speech"
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {
                "model": self.model,
                "input": text,
                "voice": config.voice_id or "index_male_01",
                "speed": config.rate,
                "pitch": config.pitch,
            }

            # 情感控制
            if config.style:
                payload["emotion"] = config.style.value

            # 音色克隆
            if config.ref_audio:
                payload["ref_audio"] = config.ref_audio

            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path_obj, "wb") as f:
                f.write(response.content)

            duration = self._get_audio_duration(output_path)

            return GeneratedVoice(
                audio_path=output_path,
                duration=duration,
                text=text,
                voice_id=config.voice_id or "index_male_01",
                sample_rate=24000,
                format="mp3",
            )

        except Exception as e:
            logger.error(f"IndexTTS2 生成失败: {e}")
            raise

    def list_voices(self, language: str = "zh-CN") -> list[VoiceInfo]:
        """列出可用声音"""
        return self.PRESET_VOICES
