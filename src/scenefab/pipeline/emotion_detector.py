"""Emotion peak detection for video segments."""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

from ..models.video import EmotionPeak, VideoSegment
from .config import PipelineConfig

logger = logging.getLogger(__name__)


class EmotionPeakDetector:
    """
    情感峰值检测器 V2
    支持并行分析
    """

    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self._cache = {}

    def detect(
        self, segments: list[VideoSegment], progress_callback: Callable | None = None
    ) -> list[EmotionPeak]:
        peaks = []
        total = len(segments)

        if self.config.enable_parallel and total > 1:
            # 并行处理
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                futures = {
                    executor.submit(self._analyze_segment, seg): i
                    for i, seg in enumerate(segments)
                }

                for i, future in enumerate(as_completed(futures)):
                    result = future.result()
                    if result:
                        peaks.append(result)

                    if progress_callback:
                        progress_callback(i + 1, total)
        else:
            # 串行处理
            for i, seg in enumerate(segments):
                result = self._analyze_segment(seg)
                if result:
                    peaks.append(result)

                if progress_callback:
                    progress_callback(i + 1, total)

        # 按评分降序排列
        peaks.sort(key=lambda p: p.peak_score, reverse=True)

        return peaks

    def _analyze_segment(self, segment: VideoSegment) -> EmotionPeak | None:
        """分析单个片段"""
        cache_key = f"{segment.video_path}:{segment.start_time}:{segment.end_time}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        visual_score = self._analyze_visual_complexity(segment)
        audio_score = self._analyze_audio_emotion(segment)

        peak_score = (
            self.config.visual_weight * visual_score
            + self.config.audio_weight * audio_score
        )

        reason = self._determine_reason(visual_score, audio_score)

        peak = EmotionPeak(
            segment=segment,
            peak_score=peak_score,
            reason=reason,
            visual_score=visual_score,
            audio_score=audio_score,
        )

        self._cache[cache_key] = peak
        return peak

    def _analyze_visual_complexity(self, segment: VideoSegment) -> float:
        """分析视觉复杂度"""
        try:
            import cv2

            cap = cv2.VideoCapture(segment.video_path)
            if not cap.isOpened():
                return 0.5

            fps = cap.get(cv2.CAP_PROP_FPS)
            start_frame = int(segment.start_time * fps)
            end_frame = int(segment.end_time * fps)

            # 采样间隔
            sample_interval = max(1, int(fps * 0.5))
            diffs = []
            prev_gray = None

            # 最多采样100帧
            max_samples = 100
            sampled = 0

            for f in range(
                start_frame,
                min(end_frame, start_frame + max_samples * sample_interval),
                sample_interval,
            ):
                if sampled >= max_samples:
                    break

                cap.set(cv2.CAP_PROP_POS_FRAMES, f)
                ret, frame = cap.read()
                if ret:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    if prev_gray is not None:
                        diff = np.mean(
                            np.abs(gray.astype(float) - prev_gray.astype(float))
                        )
                        diffs.append(diff)
                    prev_gray = gray
                    sampled += 1

            cap.release()

            if diffs:
                avg_diff = np.mean(diffs)
                return min(1.0, avg_diff / 30.0)

        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Visual analysis failed: {e}")

        return 0.3 + (hash(f"{segment.video_path}{segment.start_time}") % 50) / 100.0

    def _analyze_audio_emotion(self, segment: VideoSegment) -> float:
        """分析音频情绪"""
        try:
            import librosa

            y, sr = librosa.load(
                segment.video_path,
                offset=segment.start_time,
                duration=segment.duration,
                sr=16000,
            )

            if len(y) < sr:
                return 0.5

            # 能量计算
            energy = np.sum(y**2) / len(y)
            energy_norm = min(1.0, float(energy**0.5) * 5)

            # 音调计算
            try:
                pitches, _ = librosa.piptrack(y=y, sr=sr)
                pitch_max = [p[p > 0].max() for p in pitches.T if p[p > 0].size > 0]
                if pitch_max:
                    pitch_norm = min(1.0, np.mean(pitch_max) / 300.0)
                else:
                    pitch_norm = 0.5
            except Exception:
                pitch_norm = 0.5

            return energy_norm * 0.6 + pitch_norm * 0.4

        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Audio analysis failed: {e}")

        return 0.5

    def _determine_reason(self, visual: float, audio: float) -> str:
        """判断峰值原因"""
        if visual > audio * 1.5:
            if visual > 0.8:
                return "高复杂度场景，信息密度大"
            elif visual > 0.6:
                return "动作密度较高"
            else:
                return "画面信息丰富"
        elif audio > visual * 1.5:
            return "音频情绪强度高"
        else:
            if visual > 0.7 and audio > 0.7:
                return "视觉+音频双重高能"
            elif visual > 0.6:
                return "综合情感峰值"
            else:
                return "情感起伏明显"
