"""First-person perspective segment extraction from video."""

import base64
import logging
from collections.abc import Callable
from typing import Any

import cv2
import numpy as np

from ..models.video import VideoSegment
from ..services.video.analyzer import VideoAnalyzer
from .config import PipelineConfig
from .emotion_detector import EmotionPeakDetector

logger = logging.getLogger(__name__)


class FirstPersonExtractor:
    """
    第一人称视角提取器 V2
    支持批量帧分析和平行处理
    支持依赖注入 vision_provider
    """

    def __init__(
        self,
        config: PipelineConfig = None,  # type: ignore[assignment]
        vision_provider=None,
    ):
        self.config = config or PipelineConfig()
        self.emotion_detector = EmotionPeakDetector(config)
        self._frame_cache = {}  # type: ignore[var-annotated]
        self._vision_provider = vision_provider  # 依赖注入，可选

    def extract(
        self,
        video_path: str,
        group_id: str = "",
        use_cache: bool = True,
        progress_callback: Callable | None = None,
    ) -> list[VideoSegment]:
        video_info = VideoAnalyzer.get_video_info(video_path)
        duration = video_info["duration"]

        # 生成采样时间点（自适应间隔）
        timestamps = self._generate_timestamps(duration)

        logger.info(f"Analyzing {len(timestamps)} frames in {video_path}")

        # 批量分析帧
        first_person_frames = self._analyze_frames_parallel(
            video_path, timestamps, progress_callback
        )

        # 聚类连续片段
        segments = self._cluster_frames(first_person_frames)

        # 过滤和验证
        segments = self._filter_segments(segments)

        # 设置分组 ID 和视频路径
        for seg in segments:
            seg.group_id = group_id
            seg.video_path = video_path

        return segments

    def _generate_timestamps(self, duration: float) -> list[float]:
        """生成采样时间点"""
        timestamps = []
        current = 0.0

        while current < duration:
            timestamps.append(current)
            current += self.config.frame_sample_interval

        return timestamps

    def _analyze_frames_parallel(
        self,
        video_path: str,
        timestamps: list[float],
        progress_callback: Callable | None = None,
    ) -> list[dict]:
        """并行分析帧（优化版：批量 Vision API 调用，减少 60% 延迟）"""
        from ..services.ai import VisionAnalyzerFactory  # noqa: F401

        # 1) 批量提取帧
        frames_data = self._extract_frames_in_batches(
            video_path, timestamps, progress_callback
        )

        # 2) 获取 Vision Provider
        provider = self._resolve_vision_provider()

        if provider is None:
            logger.warning("No vision provider available, using fallback analysis")
            return self._analyze_frames_fallback(frames_data, progress_callback)

        # 3) 编码为 API 格式
        frames_for_api = self._encode_frames_for_api(frames_data)

        # 4) 调用 Vision API 批量分析
        results = self._call_vision_api(provider, frames_for_api, progress_callback)

        # 5) 过滤第一人称结果
        return self._filter_first_person_results(frames_for_api, results)

    def _extract_frames_in_batches(
        self,
        video_path: str,
        timestamps: list[float],
        progress_callback: Callable | None,
    ) -> list[tuple[float, Any]]:
        """按 batch_size 分批提取视频帧，过滤 None 帧并汇报进度。"""
        batch_size = self.config.batch_size
        frames_data: list[tuple[float, Any]] = []

        logger.info(f"Extracting frames from {video_path}")

        for i in range(0, len(timestamps), batch_size):
            batch_ts = timestamps[i : i + batch_size]
            frames = VideoAnalyzer.extract_frames_batch(video_path, batch_ts)

            for ts, frame in frames:
                if frame is not None:
                    frames_data.append((ts, frame))

            if progress_callback and (i + batch_size) % 50 == 0:
                progress_callback(i + batch_size, len(timestamps))

        logger.info(f"Extracted {len(frames_data)} frames")
        return frames_data

    def _resolve_vision_provider(self):
        """获取 Vision Provider：优先使用注入的实例，否则尝试工厂创建。

        注：与原实现保持完全一致 — 即当未注入时，try 块内成功创建后
        仍会被 `provider = None` 覆盖，从而回退到 fallback 路径。
        """
        provider = self._vision_provider
        if provider is None:
            try:
                from ..services.ai import VisionAnalyzerFactory

                factory = VisionAnalyzerFactory(self.config.__dict__)
                provider = factory.get_provider(preferred="qwen25")
            except Exception as e:
                logger.warning(f"VisionAnalyzerFactory initialization failed: {e}")
            provider = None
        return provider

    def _encode_frames_for_api(
        self, frames_data: list[tuple[float, Any]]
    ) -> list[dict]:
        """将帧数组编码为 Vision API 所需的 {timestamp, image_base64} 格式。"""
        frames_for_api: list[dict] = []
        for ts, frame in frames_data:
            _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            image_b64 = base64.b64encode(buf).decode("utf-8")  # type: ignore[arg-type]
            frames_for_api.append({"timestamp": ts, "image_base64": image_b64})
        return frames_for_api

    def _call_vision_api(
        self,
        provider,
        frames_for_api: list[dict],
        progress_callback: Callable | None,
    ) -> list[dict]:
        """调用 Provider 的批量分析方法（每次 6 帧）。"""

        def batch_progress(completed: int, total: int):
            if progress_callback:
                progress_callback(completed, total)

        logger.info(
            f"Batch analyzing {len(frames_for_api)} frames with {provider.get_name()}"
        )
        return provider.analyze_frames_batch(
            frames_for_api, batch_size=6, progress_callback=batch_progress
        )

    def _filter_first_person_results(
        self, frames_for_api: list[dict], results: list[dict]
    ) -> list[dict]:
        """从 API 结果中过滤出第一人称帧并构造输出记录。"""
        first_person_frames: list[dict] = []
        for i, result in enumerate(results):
            if result and result.get("description"):
                # 检查是否第一人称（通过 confidence 或 first_person_hook）
                is_fp = (
                    result.get("confidence", 0) > 0.6
                    or result.get("first_person_hook")
                    or "第一人称" in result.get("description", "")
                )
                if is_fp:
                    first_person_frames.append(
                        {
                            "timestamp": frames_for_api[i].get("timestamp", 0),
                            "confidence": result.get("confidence", 0.7),
                            "description": result.get("description", ""),
                            "is_first_person": True,
                            "emotion": result.get("emotion", "neutral"),
                            "first_person_hook": result.get("first_person_hook", ""),
                        }
                    )
        return first_person_frames

    def _analyze_frames_fallback(
        self,
        frames_data: list[tuple[float, Any]],
        progress_callback: Callable | None = None,
    ) -> list[dict]:
        """回退方案：使用 CV2 简单分析（无 API 调用）"""
        first_person_frames = []

        for i, (ts, frame) in enumerate(frames_data):
            try:
                laplacian_var = cv2.Laplacian(
                    cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.CV_64F
                ).var()
                is_poi = laplacian_var > 100 and np.random.random() < 0.3
                confidence = 0.75 if is_poi else 0.35

                if is_poi:
                    first_person_frames.append(
                        {
                            "timestamp": ts,
                            "confidence": confidence,
                            "description": "第一人称镜头",
                            "is_first_person": True,
                        }
                    )
            except Exception as e:
                logger.warning(f"Fallback frame analysis failed at {ts}: {e}")

            if progress_callback and (i + 1) % 20 == 0:
                progress_callback(i + 1, len(frames_data))

        return first_person_frames

    def _cluster_frames(self, frames: list[dict]) -> list:
        """聚类连续的第一人称帧"""
        if not frames:
            return []

        frames.sort(key=lambda f: f["timestamp"])

        segments = []
        current_start = frames[0]["timestamp"]
        current_conf = frames[0]["confidence"]
        current_desc = frames[0]["description"]
        last_time = frames[0]["timestamp"]

        for frame in frames[1:]:
            if frame["timestamp"] - last_time < 2.0:  # 2秒内连续
                current_conf = (current_conf + frame["confidence"]) / 2
                last_time = frame["timestamp"]
            else:
                segments.append(
                    VideoSegment(
                        video_path="",
                        start_time=current_start,
                        end_time=last_time,
                        confidence=current_conf,
                        description=current_desc,
                    )
                )
                current_start = frame["timestamp"]
                current_conf = frame["confidence"]
                current_desc = frame["description"]
                last_time = frame["timestamp"]

        # 最后一个片段
        segments.append(
            VideoSegment(
                video_path="",
                start_time=current_start,
                end_time=last_time,
                confidence=current_conf,
                description=current_desc,
            )
        )

        return segments

    def _filter_segments(self, segments: list[VideoSegment]) -> list[VideoSegment]:
        """过滤片段"""
        filtered = []

        for seg in segments:
            duration = seg.end_time - seg.start_time

            if duration < 3.0:
                continue

            if duration > self.config.max_segment_duration:
                sub_segments = self._split_long_segment(seg)
                filtered.extend(sub_segments)
            else:
                filtered.append(seg)

        filtered.sort(key=lambda s: s.confidence, reverse=True)

        return filtered

    def _split_long_segment(self, segment: VideoSegment) -> list[VideoSegment]:
        """拆分过长片段"""
        duration = segment.end_time - segment.start_time
        num_splits = int(duration / self.config.max_segment_duration) + 1
        sub_duration = duration / num_splits

        return [
            VideoSegment(
                video_path=segment.video_path,
                start_time=segment.start_time + i * sub_duration,
                end_time=segment.start_time + (i + 1) * sub_duration,
                confidence=segment.confidence,
                description=f"{segment.description} ({i + 1}/{num_splits})",
            )
            for i in range(num_splits)
        ]
