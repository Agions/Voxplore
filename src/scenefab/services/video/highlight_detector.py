#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
高光检测器 (Highlight Detector)

从视频中自动检测"高光时刻"——观众最可能感兴趣的片段。

检测策略：
1. 画面突变检测 — 镜头切换、场景变换处通常是新事件
2. 音频能量峰值 — 笑声、欢呼、爆炸声等高能量音频片段
3. 运动强度检测 — 画面变化率高的片段（动作场面）
4. 色彩饱和度变化 — 色彩更丰富的片段往往更吸引注意力

功能：
- 基于 FFmpeg + 帧分析检测高光
- 返回时间戳列表 + 置信度分数
- 支持自定义阈值和最小片段时长
- 可与 BeatDetector 结合做音乐节奏同步

使用示例：
    from scenefab.services.video import HighlightDetector, HighlightSegment

    detector = HighlightDetector()
    highlights = detector.detect("video.mp4", min_confidence=0.6)
    for h in highlights:
        print(f"高光时刻: {h.timestamp:.1f}s, 置信度: {h.confidence:.2f}")
"""

__all__ = ["HighlightReason", "HighlightSegment", "HighlightDetectorConfig", "HighlightDetector"]

import logging
import subprocess
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

from ...utils.security import SecurityError

# 性能优化：缩放目标尺寸 (160x90 ≈ 14K像素，相比HD图减少约95%数据量)
_TARGET_SIZE = (160, 90)

logger = logging.getLogger(__name__)

# 可选依赖，用于帧分析
try:
    import numpy as np  # noqa: F401
    from PIL import Image  # noqa: F401
    _OPTIONAL_DEPS_OK = True
except ImportError:
    _OPTIONAL_DEPS_OK = False
    np = None
    Image = None


class HighlightReason(Enum):
    """高光原因分类"""
    SCENE_CHANGE = "scene_change"      # 场景突变
    AUDIO_PEAK = "audio_peak"          # 音频能量峰值
    MOTION_INTENSE = "motion_intense"  # 剧烈运动
    COLOR_VIBRANT = "color_vibrant"    # 色彩鲜艳
    COMBINED = "combined"              # 多因素综合


@dataclass
class HighlightSegment:
    """
    单个高光片段

    Attributes:
        start: 开始时间（秒）
        end: 结束时间（秒）
        confidence: 置信度 0-1
        reason: 高光原因
        peak_timestamp: 最具代表性时间点
    """
    start: float
    end: float
    confidence: float
    reason: HighlightReason
    peak_timestamp: float = 0.0

    @property
    def duration(self) -> float:
        """片段时长（秒）"""
        return self.end - self.start

    def to_dict(self) -> dict:
        d = asdict(self)
        d["reason"] = self.reason.value
        d["duration"] = self.duration
        return d


@dataclass
class HighlightDetectorConfig:
    """高光检测配置"""
    # 时长阈值
    min_duration: float = 1.0        # 最小高光时长（秒）
    max_duration: float = 30.0      # 最大高光时长（秒）
    min_gap: float = 0.5             # 高光间最小间隔（秒）

    # 置信度阈值
    min_confidence: float = 0.5      # 最小置信度 0-1

    # 检测策略权重
    scene_change_weight: float = 0.3
    audio_peak_weight: float = 0.4
    motion_weight: float = 0.2
    color_weight: float = 0.1

    # FFmpeg 参数
    sample_rate: int = 44100
    fps: int = 1                     # 每秒采样帧数（分析用）
    block_size: int = 1              # 块大小（秒）


# ── 全局安全执行器（延迟初始化）────────────────────────────────
_executor = None


def _get_executor():
    """获取全局安全执行器（延迟初始化）"""
    global _executor
    if _executor is None:
        from ...utils.security import get_ffmpeg_executor
        _executor = get_ffmpeg_executor()
    return _executor


class HighlightDetector:
    """
    高光检测器

    通过多维度分析自动识别视频中的高光片段。
    """

    def __init__(self, config: Optional[HighlightDetectorConfig] = None):
        """
        初始化高光检测器

        Args:
            config: 检测配置，默认使用 HighlightDetectorConfig()
        """
        self.config = config or HighlightDetectorConfig()

    def detect(
        self,
        video_path: str,
        min_confidence: Optional[float] = None,
    ) -> List[HighlightSegment]:
        """
        检测视频中的高光片段

        Args:
            video_path: 视频文件路径
            min_confidence: 覆盖最小置信度阈值

        Returns:
            高光片段列表，按开始时间排序
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        threshold = min_confidence or self.config.min_confidence

        # 并行运行多种检测
        scene_changes = self._detect_scene_changes(video_path)
        audio_peaks = self._detect_audio_peaks(video_path)
        motion_intense = self._detect_motion_intensity(video_path)
        color_vibrant = self._detect_color_vibrancy(video_path)

        # 合并评分
        highlights = self._merge_highlights(
            scene_changes,
            audio_peaks,
            motion_intense,
            color_vibrant,
        )

        # 过滤低置信度
        highlights = [h for h in highlights if h.confidence >= threshold]

        # 合并重叠片段
        highlights = self._merge_overlapping(highlights)

        # 过滤时长
        highlights = [
            h for h in highlights
            if self.config.min_duration <= h.duration <= self.config.max_duration
        ]

        return highlights

    def _run_ffmpeg(self, cmd: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
        """执行 ffmpeg 命令"""
        try:
            result = _get_executor().run(cmd, timeout=timeout)
            return result
        except SecurityError:
            # 命令注入攻击被拦截，不要静默吞噬
            logger.warning(f"FFmpeg command blocked by security policy: {cmd[0]}")
            return subprocess.CompletedProcess(cmd, 1, "", "SecurityError: command blocked")
        except Exception as e:
            logger.debug(f"FFmpeg 执行失败: {e}")
            return subprocess.CompletedProcess(cmd, 1, "", str(e))

    def _extract_frames(self, video_path: Path, prefix: str) -> List[Path]:
        """提取视频帧到临时目录，返回帧文件列表（已缩放到小尺寸）"""
        temp_dir = video_path.parent / ".scenefab_highlight_cache"
        temp_dir.mkdir(exist_ok=True)
        output_prefix = temp_dir / f"{video_path.stem}_{prefix}"
        # 性能优化：在 FFmpeg 中直接缩放，避免处理大图
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', f"fps={self.config.fps},scale={_TARGET_SIZE[0]}:{_TARGET_SIZE[1]}",
            '-q:v', '2',
            f"{output_prefix}%04d.jpg",
        ]
        self._run_ffmpeg(cmd)
        return sorted(temp_dir.glob(f"{video_path.stem}_{prefix}*.jpg"))

    def _cleanup_frames(self, frame_files: List[Path]) -> None:
        """清理临时帧文件"""
        for f in frame_files:
            f.unlink(missing_ok=True)

    def _detect_scene_changes(self, video_path: Path) -> List[Tuple[float, float]]:
        """
        检测场景突变（镜头切换）

        Returns:
            List of (timestamp, score) tuples
        """
        frame_files = self._extract_frames(video_path, "scene")
        if not frame_files:
            return []

        changes = []
        try:
            import numpy as np
            from PIL import Image

            prev_hist = None
            for i, frame_path in enumerate(frame_files):
                timestamp = i / self.config.fps
                # 性能优化：小图已由 FFmpeg 缩放，直接转 numpy 计算直方图
                img = Image.open(frame_path)
                arr = np.array(img, dtype=np.int32)
                # 合并 RGB 通道直方图（与原 PIL histogram() 等效）
                if arr.ndim == 3:
                    hist = np.concatenate([np.histogram(arr[:, :, c], bins=256, range=(0, 256))[0]
                                           for c in range(arr.shape[2])])
                else:
                    hist = np.histogram(arr, bins=256, range=(0, 256))[0]

                if prev_hist is not None:
                    # 计算直方图差异（向量化）
                    diff = np.sum(np.sqrt((hist - prev_hist).astype(np.float64) ** 2))
                    diff /= len(hist) * 255.0  # 归一化

                    if diff > 0.3:  # 阈值
                        changes.append((timestamp, min(diff * 2, 1.0)))

                prev_hist = hist

        except ImportError:
            # 无 PIL 时使用简化的帧文件大小变化
            prev_size = None
            for i, frame_path in enumerate(frame_files):
                timestamp = i / self.config.fps
                size = frame_path.stat().st_size
                if prev_size is not None and size > 0:
                    ratio = abs(size - prev_size) / size
                    if ratio > 0.5:
                        changes.append((timestamp, min(ratio * 2, 1.0)))
                prev_size = size

        self._cleanup_frames(frame_files)
        return changes

    def _detect_audio_peaks(self, video_path: Path) -> List[Tuple[float, float]]:
        """检测音频能量峰值（高能量 = 可能的高光）"""
        temp_dir = video_path.parent / ".scenefab_highlight_cache"
        temp_dir.mkdir(exist_ok=True)

        audio_path = temp_dir / f"{video_path.stem}_audio.wav"

        # 提取音频
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', str(self.config.sample_rate),
            '-ac', '1',
            str(audio_path),
        ]
        self._run_ffmpeg(cmd)

        peaks = []

        try:
            import numpy as np
            from pydub import AudioSegment

            audio = AudioSegment.from_wav(str(audio_path))
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            samples = samples / (2 ** 15)  # 归一化

            # 分块计算能量（向量化，避免逐块循环）
            block_size_samples = int(self.config.sample_rate * self.config.block_size)
            num_blocks = len(samples) // block_size_samples

            blocks = samples[:num_blocks * block_size_samples].reshape(num_blocks, block_size_samples)
            energies = np.sqrt(np.mean(blocks ** 2, axis=1))
            mask = energies > 0.3
            peak_indices = np.where(mask)[0]

            for idx in peak_indices:
                timestamp = idx * self.config.block_size
                peaks.append((timestamp, min(energies[idx] * 2, 1.0)))

        except ImportError:
            # 无 numpy/pydub 时跳过音频分析
            logger.debug("numpy 或 pydub 未安装，跳过音频峰值检测")

        # 清理临时文件
        if audio_path.exists():
            audio_path.unlink()

        return peaks

    def _detect_motion_intensity(self, video_path: Path) -> List[Tuple[float, float]]:
        """
        检测画面运动强度

        Returns:
            List of (timestamp, score) tuples
        """
        frame_files = self._extract_frames(video_path, "motion")
        if not frame_files:
            return []
        if not _OPTIONAL_DEPS_OK:
            return []

        motions = []
        import numpy as np
        from PIL import Image

        prev_data = None
        for i, frame_path in enumerate(frame_files):
            timestamp = i / self.config.fps
            # 性能优化：小图已由 FFmpeg 缩放，直接加载灰度
            img = Image.open(frame_path).convert('L')
            data = np.frombuffer(img.getdata(), dtype=np.uint8).astype(np.float32)

            if prev_data is not None:
                diff = np.sum(np.abs(data - prev_data)) / (len(data) * 255.0)
                if diff > 0.1:
                    motions.append((timestamp, min(diff * 3, 1.0)))

            prev_data = data

        self._cleanup_frames(frame_files)
        return motions

    def _detect_color_vibrancy(self, video_path: Path) -> List[Tuple[float, float]]:
        """
        检测色彩鲜艳程度

        Returns:
            List of (timestamp, score) tuples
        """
        frame_files = self._extract_frames(video_path, "color")
        if not frame_files:
            return []
        if not _OPTIONAL_DEPS_OK:
            return []

        vibrant = []
        import numpy as np
        from PIL import Image

        for i, frame_path in enumerate(frame_files):
            timestamp = i / self.config.fps
            # 性能优化：小图已由 FFmpeg 缩放，直接加载 RGB
            img = Image.open(frame_path).convert('RGB')
            arr = np.array(img, dtype=np.float32)  # (h, w, 3)

            r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

            # 平均亮度
            brightness = (r.mean() + g.mean() + b.mean()) / (3 * 255.0)

            # 色彩饱和度（向量化）
            max_rgb = np.maximum(np.maximum(r, g), b)
            min_rgb = np.minimum(np.minimum(r, g), b)
            saturation = (max_rgb - min_rgb) / (max_rgb + 1e-6)
            avg_saturation = saturation.mean()

            # 高饱和度 + 中等亮度 = 鲜艳
            vibrancy = avg_saturation * (1 - abs(brightness - 0.5) * 2)
            if vibrancy > 0.4:
                vibrant.append((timestamp, min(vibrancy * 2, 1.0)))

        self._cleanup_frames(frame_files)
        return vibrant

    def _merge_highlights(
        self,
        scene_changes: List[Tuple[float, float]],
        audio_peaks: List[Tuple[float, float]],
        motion_intense: List[Tuple[float, float]],
        color_vibrant: List[Tuple[float, float]],
    ) -> List[HighlightSegment]:
        """
        合并多种检测结果，加权评分
        """
        # 构建时间线分数
        timeline: dict[float, dict] = {}

        for ts, score in scene_changes:
            if ts not in timeline:
                timeline[ts] = {"scene": 0, "audio": 0, "motion": 0, "color": 0}
            timeline[ts]["scene"] = score

        for ts, score in audio_peaks:
            if ts not in timeline:
                timeline[ts] = {"scene": 0, "audio": 0, "motion": 0, "color": 0}
            timeline[ts]["audio"] = score

        for ts, score in motion_intense:
            if ts not in timeline:
                timeline[ts] = {"scene": 0, "audio": 0, "motion": 0, "color": 0}
            timeline[ts]["motion"] = score

        for ts, score in color_vibrant:
            if ts not in timeline:
                timeline[ts] = {"scene": 0, "audio": 0, "motion": 0, "color": 0}
            timeline[ts]["color"] = score

        # 计算加权综合分数
        highlights = []
        for ts, scores in sorted(timeline.items()):
            combined = (
                scores["scene"] * self.config.scene_change_weight +
                scores["audio"] * self.config.audio_peak_weight +
                scores["motion"] * self.config.motion_weight +
                scores["color"] * self.config.color_weight
            )

            # 判断主要原因：dict dispatch 替代 if/elif 链
            _SCORE_REASON_MAP = {
                "scene": HighlightReason.SCENE_CHANGE,
                "audio": HighlightReason.AUDIO_PEAK,
                "motion": HighlightReason.MOTION_INTENSE,
                "color": HighlightReason.COLOR_VIBRANT,
            }
            reason = _SCORE_REASON_MAP.get(max(scores, key=lambda k: scores[k]), HighlightReason.COMBINED)

            highlights.append(HighlightSegment(
                start=ts,
                end=ts + self.config.block_size,
                confidence=combined,
                reason=reason,
                peak_timestamp=ts,
            ))

        return highlights

    def _merge_overlapping(
        self,
        highlights: List[HighlightSegment],
    ) -> List[HighlightSegment]:
        """
        合并重叠的高光片段
        """
        if not highlights:
            return []

        # 按开始时间排序
        sorted_hl = sorted(highlights, key=lambda h: h.start)

        merged = [sorted_hl[0]]

        for current in sorted_hl[1:]:
            last = merged[-1]

            # 如果重叠或接近
            if current.start <= last.end + self.config.min_gap:
                # 合并：扩展结束时间，取最大置信度
                new_end = max(last.end, current.end)
                new_confidence = max(last.confidence, current.confidence)
                # 重新计算 peak_timestamp
                if current.confidence > last.confidence:
                    new_peak = current.peak_timestamp
                    new_reason = current.reason
                else:
                    new_peak = last.peak_timestamp
                    new_reason = last.reason

                merged[-1] = HighlightSegment(
                    start=last.start,
                    end=new_end,
                    confidence=new_confidence,
                    reason=new_reason,
                    peak_timestamp=new_peak,
                )
            else:
                merged.append(current)

        return merged

    def detect_with_beat_sync(
        self,
        video_path: str,
        beat_info: List,
        min_confidence: float = 0.5,
    ) -> List[HighlightSegment]:
        """
        结合节拍信息检测高光（节奏同步剪辑用）

        Args:
            video_path: 视频路径
            beat_info: BeatDetector 输出的节拍信息列表
            min_confidence: 最小置信度

        Returns:
            对齐到节拍的高光片段
        """
        highlights = self.detect(video_path, min_confidence)

        # 将高光时间戳对齐到最近的强拍
        beat_timestamps = [b.timestamp for b in beat_info if b.strength.value == "strong"]

        for h in highlights:
            if beat_timestamps:
                nearest_beat = min(beat_timestamps, key=lambda b: abs(b - h.peak_timestamp))
                h.peak_timestamp = nearest_beat
                h.start = nearest_beat
                h.end = nearest_beat + h.duration

        return highlights
