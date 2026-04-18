"""
语音转字幕提取器 (Speech Subtitle Extractor)

从视频/音频中通过语音识别提取字幕。
支持 OpenAI Whisper API 和本地 Faster-Whisper 模型。

支持:
1. OpenAI Whisper API(推荐,精度高)
2. 本地 Faster-Whisper 模型(离线,速度快 3-4x,推荐)
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from .subtitle_types import SubtitleSegment, SubtitleExtractionResult


logger = logging.getLogger(__name__)


class SpeechSubtitleExtractor:
    """
    语音转字幕提取器
    从视频/音频中通过语音识别提取字幕
    """

    # 支持的本地模型大小(Faster-Whisper)
    WHISPER_MODELS = {
        "tiny": {"name": "Whisper Tiny", "params": "~39M", "VRAM": "~1GB"},
        "base": {"name": "Whisper Base", "params": "~74M", "VRAM": "~1GB"},
        "small": {"name": "Whisper Small", "params": "~244M", "VRAM": "~2GB"},
        "medium": {"name": "Whisper Medium", "params": "~769M", "VRAM": "~5GB"},
        "large": {"name": "Whisper Large", "params": "~1550M", "VRAM": "~10GB"},
        # Faster-Whisper 额外支持量化模型
        "large-v2": {"name": "Whisper Large V2", "params": "~1550M", "VRAM": "~5GB (int8)"},
        "large-v3": {"name": "Whisper Large V3", "params": "~1550M", "VRAM": "~5GB (int8)"},
    }

    def __init__(self, api_key: Optional[str] = None,
                 mode: str = "local",
                 local_model: str = "medium"):
        """
        Args:
            api_key: OpenAI API key(mode=api 时需要)
            mode: "api"(OpenAI Whisper API) / "local"(本地 faster-whisper)
            local_model: 本地模型大小 ("tiny"/"base"/"small"/"medium"/"large")
                      推荐 "medium":精度与速度最佳平衡(GPU 2-3min / 10min 音频)
        """
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._mode = mode
        self._local_model = local_model if local_model in self.WHISPER_MODELS else "base"
        self._local_model_instance = None  # 缓存加载的模型

    def extract(self, video_path: str,
                language: str = "zh") -> SubtitleExtractionResult:
        """
        从视频/音频提取语音字幕

        Args:
            video_path: 视频或音频文件路径
            language: 语言代码
        """
        path = Path(video_path)
        duration = self._get_duration(str(path))

        result = SubtitleExtractionResult(
            video_path=str(path),
            duration=duration,
            language=language,
            method="speech",
        )

        # 先提取音频
        audio_path = self._extract_audio(str(path))

        try:
            if self._mode == "api":
                segments = self._transcribe_api(audio_path, language)
            else:
                segments = self._transcribe_local(audio_path, language)

            result.segments = segments
            result.full_text = " ".join(s.text for s in segments)
        finally:
            # 清理临时音频
            if audio_path != str(path):
                try:
                    os.unlink(audio_path)
                except Exception:
                    logger.debug("Operation failed")

        return result

    def _transcribe_api(self, audio_path: str,
                        language: str) -> List[SubtitleSegment]:
        """使用 OpenAI Whisper API 转录"""
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)

        with open(audio_path, 'rb') as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

        segments = []
        if hasattr(response, 'segments') and response.segments:
            for seg in response.segments:
                segments.append(SubtitleSegment(
                    start=seg.get("start", seg.start) if isinstance(seg, dict) else seg.start,
                    end=seg.get("end", seg.end) if isinstance(seg, dict) else seg.end,
                    text=(seg.get("text", "") if isinstance(seg, dict) else seg.text).strip(),
                    confidence=seg.get("avg_logprob", 0) if isinstance(seg, dict) else getattr(seg, 'avg_logprob', 0),
                    source="speech",
                ))
        elif hasattr(response, 'text'):
            # 无时间戳,整段返回
            segments.append(SubtitleSegment(
                start=0, end=self._get_duration(audio_path),
                text=response.text.strip(),
                source="speech",
            ))

        return segments

    def _transcribe_local(self, audio_path: str,
                          language: str) -> List[SubtitleSegment]:
        """使用本地 faster-whisper 模型转录(CPU/GPU 自动检测)"""
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError(
                "本地 Faster-Whisper 需要安装: pip install faster-whisper"
            )

        # 使用缓存的模型实例（避免重复加载）
        if self._local_model_instance is None:
            try:
                # 自动检测 GPU/CUDA 支持
                device, compute_type, batch_size = self._detect_device()

                if device == "cuda":
                    logger.info(f"Faster-Whisper 使用 GPU 加速 ({compute_type}, batch_size={batch_size})")
                else:
                    logger.info(f"Faster-Whisper 使用 CPU ({compute_type})")

                self._local_model_instance = WhisperModel(
                    self._local_model,
                    device=device,
                    compute_type=compute_type,
                )
                # 缓存 batch_size 供转录使用
                self._local_model_instance._batch_size = batch_size
            except Exception as e:
                raise RuntimeError(
                    f"加载 Faster-Whisper {self._local_model} 模型失败: {e}\n"
                    f"请确保有足够的内存和正确的模型文件。"
                )

        model = self._local_model_instance
        batch_size = getattr(model, '_batch_size', None)

        # 转录参数
        transcribe_options = {
            "language": language if language != "auto" else None,
            "task": "transcribe",
            "vad_filter": True,  # 语音活动检测，过滤静音
        }

        # GPU 时启用批处理以获得 8.9x 加速
        if batch_size:
            transcribe_options["batch_size"] = batch_size

        # 如果语言是 auto,让模型自己检测
        if language == "auto":
            transcribe_options.pop("language")

        try:
            segments_gen, info = model.transcribe(audio_path, **transcribe_options)
        except Exception as e:
            raise RuntimeError(f"Faster-Whisper 转录失败: {e}")

        segments = []
        for seg in segments_gen:
            text = seg.text.strip()
            if text:  # 跳过空文本
                segments.append(SubtitleSegment(
                    start=seg.start,
                    end=seg.end,
                    text=text,
                    source="speech",
                ))

        return segments

    def _detect_device(self) -> Tuple[str, str, Optional[int]]:
        """
        自动检测可用的计算设备

        Returns:
            Tuple[str, str, Optional[int]]: (device, compute_type, batch_size)
                - device: "cuda" 或 "cpu"
                - compute_type: "float16", "int8" 等
                - batch_size: GPU 时启用批处理（8x 加速），CPU 时 None
        """
        # 优先检测 CUDA/GPU
        try:
            import torch
            if torch.cuda.is_available():
                # GPU 可用：float16 + batch_size=8（8.9x 加速，benchmark 数据）
                # 参考：faster-whisper batch=8 @ RTX 3070 Ti: 16s vs 143s (8.9x)
                return ("cuda", "float16", 8)
        except ImportError:
            logger.debug("torch not available for GPU detection, falling back to CPU")

        # CPU 方案：int8 量化（2.4x 加速 vs fp32）
        return ("cpu", "int8", None)

    def get_available_models(self) -> List[str]:
        """获取可用的本地模型列表"""
        return list(self.WHISPER_MODELS.keys())

    def _extract_audio(self, video_path: str) -> str:
        """从视频提取音频"""
        # 如果已经是音频文件,直接返回
        ext = Path(video_path).suffix.lower()
        if ext in ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac'):
            return video_path

        output = tempfile.mktemp(suffix='.wav', prefix='narrafiilm_stt_')
        cmd = [
            'ffmpeg', '-y', '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le',
            '-ar', '16000', '-ac', '1',
            output
        ]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0:
            raise RuntimeError(f"音频提取失败: {r.stderr.decode()[:200]}")
        return output

    def _get_duration(self, path: str) -> float:
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries',
               'format=duration', '-of', 'csv=p=0', path]
        r = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return float(r.stdout.strip())
        except (ValueError, AttributeError):
            return 0.0
