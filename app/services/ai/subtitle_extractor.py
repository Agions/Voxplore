#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
字幕提取模块
支持两种方式：
1. OCR 提取 — 从视频画面中识别字幕文字（Vision API）
2. 语音转文字 — 从音频中提取语音内容（Whisper / 在线 API）

两种方式可以组合使用，互相补充。
"""

import os
import subprocess
import tempfile
import logging

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .subtitle_types import SubtitleSegment, SubtitleExtractionResult
from .subtitle_speech import SpeechSubtitleExtractor
from .subtitle_merger import SubtitleMerger
from .subtitle_translator import SubtitleTranslator

# 导出所有公共类型和类
__all__ = [
    "SubtitleSegment",
    "SubtitleExtractionResult",
    "OCRSubtitleExtractor",
    "SpeechSubtitleExtractor",
    "SubtitleMerger",
    "SubtitleTranslator",
    "extract_subtitles",
    "translate_subtitles",
]


logger = logging.getLogger(__name__)


class OCRSubtitleExtractor:
    """
    OCR 字幕提取器
    从视频关键帧中通过 Vision API 识别画面中的字幕文字
    """

    def __init__(self, api_key: Optional[str] = None,
                 provider: str = "openai"):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._provider = provider

    def extract(self, video_path: str,
                sample_interval: float = 1.0,
                max_frames: int = 60) -> SubtitleExtractionResult:
        """
        从视频提取 OCR 字幕

        Args:
            video_path: 视频路径
            sample_interval: 采样间隔（秒）
            max_frames: 最大帧数
        """
        import base64

        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"视频不存在: {video_path}")

        duration = self._get_duration(video_path)
        result = SubtitleExtractionResult(
            video_path=video_path,
            duration=duration,
            method="ocr",
        )

        # 提取关键帧
        frames = self._extract_frames(video_path, duration,
                                       sample_interval, max_frames)

        if not frames:
            return result

        # 批量 OCR
        segments = []
        prev_text = ""

        for timestamp, frame_path in frames:
            try:
                with open(frame_path, 'rb') as f:
                    img_b64 = base64.b64encode(f.read()).decode()

                text = self._ocr_frame(img_b64)

                if text and text != prev_text:
                    # 新字幕出现
                    if segments and segments[-1].text == prev_text:
                        segments[-1].end = timestamp

                    segments.append(SubtitleSegment(
                        start=timestamp,
                        end=timestamp + sample_interval,
                        text=text,
                        source="ocr",
                    ))
                    prev_text = text
                elif text and text == prev_text and segments:
                    # 字幕延续
                    segments[-1].end = timestamp + sample_interval

            except Exception as e:
                logger.error(f"OCR 帧 {timestamp:.1f}s 失败: {e}")

        # 清理临时文件
        for _, fp in frames:
            try:
                os.unlink(fp)
            except Exception:
                logger.debug("Operation failed")

        result.segments = segments
        result.full_text = " ".join(s.text for s in segments)
        return result

    def _ocr_frame(self, image_base64: str) -> str:
        """对单帧进行 OCR"""
        if self._provider == "openai":
            return self._ocr_openai(image_base64)
        return ""

    def _ocr_openai(self, image_base64: str) -> str:
        """使用 OpenAI Vision 做 OCR"""
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "提取这张视频截图中的字幕文字。只返回字幕文字内容，如果没有字幕则返回空字符串。不要加任何解释。"},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}",
                        "detail": "low"
                    }}
                ]
            }],
            max_tokens=200,
        )
        text = response.choices[0].message.content.strip()
        if text in ("", "无", "无字幕", "空", "没有字幕"):
            return ""
        return text

    def _extract_frames(self, video_path: str, duration: float,
                        interval: float, max_frames: int) -> List[Tuple[float, str]]:
        """提取关键帧"""
        tmpdir = tempfile.mkdtemp(prefix="narrafiilm_ocr_")
        frames = []
        num = min(int(duration / interval) + 1, max_frames)

        for i in range(num):
            ts = i * interval
            if ts > duration:
                break
            out = os.path.join(tmpdir, f"frame_{i:04d}.jpg")
            cmd = [
                'ffmpeg', '-y', '-ss', str(ts),
                '-i', video_path, '-vframes', '1',
                '-q:v', '5', out
            ]
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode == 0 and os.path.exists(out):
                frames.append((ts, out))

        return frames

    def _get_duration(self, video_path: str) -> float:
        """获取视频时长"""
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0', video_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return float(r.stdout.strip())
        except (ValueError, AttributeError):
            return 0.0


# ========== 便捷函数 ==========

def extract_subtitles(video_path: str,
                      method: str = "speech",
                      api_key: Optional[str] = None,
                      language: str = "zh") -> SubtitleExtractionResult:
    """
    提取字幕的便捷函数

    Args:
        video_path: 视频路径
        method: "ocr" / "speech" / "both"
        api_key: API key
        language: 语言

    Returns:
        字幕提取结果
    """
    if method == "ocr":
        extractor = OCRSubtitleExtractor(api_key=api_key)
        return extractor.extract(video_path)

    elif method == "speech":
        extractor = SpeechSubtitleExtractor(api_key=api_key)
        return extractor.extract(video_path, language=language)

    elif method == "both":
        ocr_ext = OCRSubtitleExtractor(api_key=api_key)
        speech_ext = SpeechSubtitleExtractor(api_key=api_key)

        ocr_result = ocr_ext.extract(video_path)
        speech_result = speech_ext.extract(video_path, language=language)

        return SubtitleMerger.merge(ocr_result, speech_result)

    else:
        raise ValueError(f"不支持的方法: {method}，可选: ocr/speech/both")


def translate_subtitles(subtitle_result: SubtitleExtractionResult,
                       target_lang: str = "en",
                       source_lang: str = "auto",
                       provider: str = "openai",
                       api_key: Optional[str] = None) -> SubtitleExtractionResult:
    """
    翻译字幕的便捷函数

    Args:
        subtitle_result: 原始字幕结果
        target_lang: 目标语言代码
        source_lang: 源语言代码，"auto" 表示自动检测
        provider: 翻译引擎 "openai" / "deepl" / "google"
        api_key: API 密钥

    Returns:
        翻译后的字幕结果
    """
    translator = SubtitleTranslator(api_key=api_key, provider=provider)
    return translator.translate(subtitle_result, target_lang, source_lang)
