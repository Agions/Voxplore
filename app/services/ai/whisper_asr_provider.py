#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Whisper ASR 提供者（离线语音识别）

支持三种模式（按优先级）：
1. faster-whisper (ctranslate2) — 推荐，精度高且快
2. openai-whisper — 标准版，需网络下载模型
3. httpx → OpenAI Whisper API — 在线 fallback

使用示例:
    provider = WhisperASRProvider()
    result = provider.transcribe("/path/to/audio.mp3")
    for seg in result.segments:
        print(f"[{seg.start:.1f}-{seg.end:.1f}] {seg.text}")

    # 流式实时识别
    for text in provider.stream_transcribe("/path/to/audio.mp3"):
        print(text, end="", flush=True)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, AsyncIterator

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    """识别结果片段"""
    start: float   # 秒
    end: float     # 秒
    text: str
    language: Optional[str] = None
    confidence: float = 1.0


@dataclass
class TranscriptionResult:
    """完整识别结果"""
    text: str
    segments: List[TranscriptSegment]
    language: Optional[str] = None
    duration: float = 0.0


class WhisperASRProvider:
    """
    Whisper ASR 提供者

    自动选择最佳可用后端：
    1. faster-whisper（本地，GPU/CPU）
    2. openai-whisper（本地，需下载模型）
    3. OpenAI Whisper API（在线）
    """

    def __init__(
        self,
        model_size: str = "medium",
        device: str = "auto",
        language: Optional[str] = "zh",
        batch_size: int = 8,
    ):
        """
        Args:
            model_size: 模型大小 (tiny/base/small/medium/large)
                       越大越准但越慢，medium 推荐性价比
            device: 设备 (auto/cpu/cuda)
            language: 语言代码（None=自动检测）
            batch_size: GPU 批处理大小（仅 GPU 模式生效，设为 8 可获 8.9x 加速）
        """
        self.model_size = model_size
        self.device = device
        self.language = language
        self._batch_size = batch_size
        self._model = None
        self._backend = None  # "faster-whisper" | "openai-whisper" | "api"

        self._setup_backend()

    def _setup_backend(self) -> None:
        """探测可用后端"""
        # 1. 优先: faster-whisper
        try:
            import faster_whisper  # noqa: F401
            self._backend = "faster-whisper"
            logger.info(f"使用 faster-whisper ({self.model_size})")
            return
        except ImportError:
            logger.warning("faster-whisper not available, trying next backend")

        # 2. 回退: openai-whisper
        try:
            import whisper  # noqa: F401
            self._backend = "openai-whisper"
            logger.info(f"使用 openai-whisper ({self.model_size})")
            return
        except ImportError:
            logger.warning("openai-whisper not available, trying next backend")

        # 3. 最终回退: API (需要 OPENAI_API_KEY)
        import os
        if os.getenv("OPENAI_API_KEY"):
            self._backend = "api"
            logger.info("使用 OpenAI Whisper API")
            return

        logger.warning(
            "所有 Whisper 后端均不可用。\n"
            "推荐安装: pip install faster-whisper\n"
            "或: pip install openai-whisper"
        )
        self._backend = None

    @property
    def is_available(self) -> bool:
        """是否可用"""
        return self._backend is not None

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        vad_filter: bool = False,
    ) -> TranscriptionResult:
        """
        转写音频为文字

        Args:
            audio_path: 音频文件路径
            language: 语言（None=自动检测）
            vad_filter: 是否启用语音活动检测（faster-whisper 专用）

        Returns:
            TranscriptionResult
        """
        if not self.is_available:
            raise RuntimeError("Whisper ASR 不可用（无网络且未安装本地模型）")

        lang = language or self.language or "zh"

        if self._backend == "faster-whisper":
            return self._transcribe_faster(audio_path, lang, vad_filter)
        elif self._backend == "openai-whisper":
            return self._transcribe_openai_whisper(audio_path, lang)
        else:
            return self._transcribe_api(audio_path, lang)

    def _transcribe_faster(
        self,
        audio_path: str,
        language: str,
        vad_filter: bool,
    ) -> TranscriptionResult:
        """faster-whisper 转写"""
        import faster_whisper

        if self._model is None:
            logger.info(f"加载 faster-whisper-{self.model_size} 模型...")
            self._model = faster_whisper.load_model(
                self.model_size,
                device=self.device if self.device != "auto" else "cpu",
                download_root=Path.home() / ".cache" / "whisper",
            )

        segments, info = self._model.transcribe(
            audio_path,
            language=language if language != "auto" else None,
            vad_filter=vad_filter,
            vad_parameters=dict(min_silence_duration_ms=500) if vad_filter else None,
            batch_size=self._batch_size,
        )

        result_segments: List[TranscriptSegment] = []
        full_text_parts: List[str] = []

        for seg in segments:
            ts = TranscriptSegment(
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
                language=info.language if hasattr(info, "language") else language,
                confidence=seg.avg_logprob if hasattr(seg, "avg_logprob") else 1.0,
            )
            result_segments.append(ts)
            full_text_parts.append(ts.text)

        return TranscriptionResult(
            text="".join(full_text_parts),
            segments=result_segments,
            language=info.language if hasattr(info, "language") else language,
            duration=info.duration if hasattr(info, "duration") else 0.0,
        )

    def _transcribe_openai_whisper(
        self,
        audio_path: str,
        language: str,
    ) -> TranscriptionResult:
        """openai-whisper 转写"""
        import whisper

        if self._model is None:
            logger.info(f"加载 whisper-{self.model_size} 模型...")
            self._model = whisper.load_model(self.model_size)

        result = self._model.transcribe(
            audio_path,
            language=language if language != "auto" else None,
            fp16=False,  # CPU 模式
        )

        return TranscriptionResult(
            text=result["text"],
            segments=[
                TranscriptSegment(
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"].strip(),
                    language=language,
                )
                for seg in result.get("segments", [])
            ],
            language=result.get("language", language),
            duration=result.get("duration", 0.0),
        )

    def _transcribe_api(
        self,
        audio_path: str,
        language: str,
    ) -> TranscriptionResult:
        """OpenAI Whisper API 转写（需要网络）"""
        import httpx
        import os

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("需要 OPENAI_API_KEY 来使用 Whisper API")

        with open(audio_path, "rb") as f:
            files = {"file": f}
            data = {"model": "whisper-1", "language": language}
            headers = {"Authorization": f"Bearer {api_key}"}

            response = httpx.post(
                "https://api.openai.com/v1/audio/transcriptions",
                files=files,
                data=data,
                headers=headers,
                timeout=60.0,
            )
            response.raise_for_status()
            result = response.json()

        return TranscriptionResult(
            text=result["text"],
            segments=[
                TranscriptSegment(
                    start=0.0,
                    end=0.0,
                    text=result["text"],
                    language=language,
                )
            ],
            language=language,
        )

    def stream_transcribe(self, audio_path: str) -> AsyncIterator[str]:
        """
        流式转写（仅 faster-whisper 支持实时模式）

        Yields:
            实时识别的文本片段
        """
        if self._backend != "faster-whisper":
            # 不支持流式，回退到完整转写
            result = self.transcribe(audio_path)
            yield result.text
            return

        import faster_whisper

        if self._model is None:
            self._model = faster_whisper.load_model(self.model_size, device="cpu")

        # faster-whisper 支持逐段 yield
        segments, _ = self._model.transcribe(
            audio_path,
            language=self.language or None,
            vad_filter=True,
        )
        for seg in segments:
            yield seg.text.strip()
