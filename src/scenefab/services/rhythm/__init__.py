"""
SceneFab BPM 卡点剪辑模块

功能：
1. BPM 检测（librosa.beat_track）
2. 节奏重音提取
3. 画面切换点自动对齐
4. 三套节奏模板预设

技术栈：
- librosa: 音频分析
- numpy: 数值计算
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class RhythmTemplate(str, Enum):
    """节奏模板"""

    FAST = "fast"  # 快节奏：平均镜头 1.2s / BPM 140+
    MEDIUM = "medium"  # 中节奏：平均镜头 2.5s / BPM 90-110
    SLOW = "slow"  # 慢节奏：平均镜头 4.0s+ / BPM < 80


@dataclass
class BeatPoint:
    """节奏点"""

    timestamp: float  # 时间戳（秒）
    strength: float  # 强度 0.0-1.0
    beat_number: int  # 第几个节拍
    is_downbeat: bool = False  # 是否为强拍


@dataclass
class CutPoint:
    """切镜点"""

    timestamp: float  # 时间戳（秒）
    beat_point: BeatPoint | None = None  # 对应的节奏点
    confidence: float = 1.0  # 置信度
    cut_type: str = "beat"  # 切镜类型：beat, manual, auto


@dataclass
class RhythmAnalysis:
    """节奏分析结果"""

    bpm: float  # BPM
    beat_count: int  # 节拍数
    average_beat_interval: float  # 平均节拍间隔（秒）
    rhythm_template: RhythmTemplate  # 推荐节奏模板
    beat_points: list[BeatPoint] = field(default_factory=list)
    confidence: float = 0.0  # 分析置信度


@dataclass
class BMPSyncResult:
    """BPM 同步结果"""

    video_path: str
    audio_path: str
    rhythm_analysis: RhythmAnalysis
    cut_points: list[CutPoint] = field(default_factory=list)
    sync_time: str = ""
    sync_version: str = "1.0.0"


class BMPSynchronizer:
    """
    BPM 同步器

    用于检测音频 BPM，并生成与节奏同步的切镜点。

    使用方法：
        synchronizer = BMPSynchronizer()
        result = synchronizer.sync(
            video_path="video.mp4",
            audio_path="audio.mp3",
            template=RhythmTemplate.MEDIUM,
        )
        for cut_point in result.cut_points:
            print(f"切镜点: {cut_point.timestamp}秒")
    """

    # 节奏模板参数
    TEMPLATE_PARAMS = {
        RhythmTemplate.FAST: {
            "target_bpm_range": (140, 180),
            "average_shot_duration": 1.2,
            "min_shot_duration": 0.5,
            "max_shot_duration": 2.0,
        },
        RhythmTemplate.MEDIUM: {
            "target_bpm_range": (90, 110),
            "average_shot_duration": 2.5,
            "min_shot_duration": 1.5,
            "max_shot_duration": 4.0,
        },
        RhythmTemplate.SLOW: {
            "target_bpm_range": (60, 80),
            "average_shot_duration": 4.0,
            "min_shot_duration": 2.5,
            "max_shot_duration": 8.0,
        },
    }

    def __init__(self):
        """初始化 BPM 同步器"""
        logger.info("BMPSynchronizer 初始化完成")

    def sync(
        self,
        video_path: str,
        audio_path: str | None = None,
        template: RhythmTemplate = RhythmTemplate.MEDIUM,
        tolerance_ms: float = 50,
    ) -> BMPSyncResult:
        """
        同步 BPM 与切镜点

        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径（可选，默认从视频提取）
            template: 节奏模板
            tolerance_ms: 容差（毫秒）

        Returns:
            BMPSyncResult: 同步结果
        """
        logger.info(f"开始 BPM 同步: {video_path}")

        # 如果没有提供音频路径，从视频提取
        if audio_path is None:
            audio_path = self._extract_audio(video_path)

        # 分析节奏
        rhythm_analysis = self._analyze_rhythm(audio_path, template)

        # 生成切镜点
        cut_points = self._generate_cut_points(
            rhythm_analysis, video_path, tolerance_ms
        )

        result = BMPSyncResult(
            video_path=video_path,
            audio_path=audio_path,
            rhythm_analysis=rhythm_analysis,
            cut_points=cut_points,
        )

        logger.info(
            f"BPM 同步完成: BPM={rhythm_analysis.bpm}, 切镜点={len(cut_points)}"
        )
        return result

    def _extract_audio(self, video_path: str) -> str:
        """
        从视频提取音频

        Args:
            video_path: 视频文件路径

        Returns:
            str: 音频文件路径
        """
        import subprocess
        from pathlib import Path

        audio_path = str(Path(video_path).with_suffix(".wav"))

        try:
            cmd = [
                "ffmpeg",
                "-i",
                video_path,
                "-vn",  # 不包含视频
                "-acodec",
                "pcm_s16le",
                "-ar",
                "22050",
                "-ac",
                "1",
                "-y",  # 覆盖输出文件
                audio_path,
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=60)
            logger.info(f"音频提取成功: {audio_path}")
            return audio_path
        except Exception as e:
            logger.error(f"音频提取失败: {e}")
            raise

    def _analyze_rhythm(
        self,
        audio_path: str,
        template: RhythmTemplate,
    ) -> RhythmAnalysis:
        """分析音频节奏，返回 RhythmAnalysis。失败时返回默认分析结果。"""
        try:
            y, sr, tempo, beat_times = self._detect_bpm_and_beats(audio_path)
            average_beat_interval = self._compute_average_beat_interval(
                beat_times, tempo
            )
            onset_env, onset_times = self._compute_onset_envelope(y, sr)
            beat_points = self._build_beat_points(
                beat_times, onset_env, onset_times
            )
            return self._assemble_rhythm_analysis(
                tempo, beat_points, average_beat_interval
            )
        except Exception as e:
            logger.error(f"节奏分析失败: {e}")
            return self._default_rhythm_analysis()

    def _assemble_rhythm_analysis(
        self,
        tempo,
        beat_points: list[BeatPoint],
        average_beat_interval: float,
    ) -> RhythmAnalysis:
        """汇总 tempo / beat_points / 平均间隔，构造 RhythmAnalysis。"""
        recommended_template = self._recommend_template(float(tempo))
        confidence = self._calculate_confidence(beat_points, float(tempo))
        return RhythmAnalysis(
            bpm=float(tempo),
            beat_count=len(beat_points),
            average_beat_interval=average_beat_interval,
            rhythm_template=recommended_template,
            beat_points=beat_points,
            confidence=confidence,
        )

    def _default_rhythm_analysis(self) -> RhythmAnalysis:
        """节奏分析失败时的默认 RhythmAnalysis。"""
        return RhythmAnalysis(
            bpm=100.0,
            beat_count=0,
            average_beat_interval=0.6,
            rhythm_template=RhythmTemplate.MEDIUM,
            beat_points=[],
            confidence=0.0,
        )

    def _detect_bpm_and_beats(self, audio_path: str):
        """加载音频并检测 BPM 与节拍时间戳，返回 (y, sr, tempo, beat_times)。"""
        import librosa

        y, sr = librosa.load(audio_path, sr=22050)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)

        return y, sr, tempo, beat_times

    def _compute_average_beat_interval(
        self,
        beat_times,
        tempo,
    ) -> float:
        """根据节拍时间戳与 BPM 计算平均节拍间隔（秒）。"""
        import numpy as np

        if len(beat_times) > 1:
            beat_intervals = np.diff(beat_times)
            return float(np.mean(beat_intervals))

        return 60.0 / tempo if tempo > 0 else 0.5  # type: ignore[assignment]

    def _compute_onset_envelope(self, y, sr):
        """计算 onset 强度包络，返回 (onset_env, onset_times)。"""
        import librosa

        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onset_times = librosa.times_like(onset_env, sr=sr)

        return onset_env, onset_times

    def _build_beat_points(
        self,
        beat_times,
        onset_env,
        onset_times,
    ) -> list[BeatPoint]:
        """根据节拍时间戳与 onset 强度构造 BeatPoint 列表。"""
        import numpy as np

        beat_points: list[BeatPoint] = []
        for i, beat_time in enumerate(beat_times):
            # 找到最近的 onset 强度
            onset_idx = np.argmin(np.abs(onset_times - beat_time))
            strength = (
                float(onset_env[onset_idx]) if onset_idx < len(onset_env) else 0.5
            )

            # 归一化强度
            strength = (
                min(1.0, strength / np.max(onset_env))
                if np.max(onset_env) > 0
                else 0.5
            )

            # 判断是否为强拍（每 4 个节拍一个强拍）
            is_downbeat = i % 4 == 0

            beat_points.append(
                BeatPoint(
                    timestamp=float(beat_time),
                    strength=strength,
                    beat_number=i,
                    is_downbeat=is_downbeat,
                )
            )

        return beat_points

    def _recommend_template(self, bpm: float) -> RhythmTemplate:
        """
        推荐节奏模板

        Args:
            bpm: BPM 值

        Returns:
            RhythmTemplate: 推荐的节奏模板
        """
        if bpm >= 140:
            return RhythmTemplate.FAST
        elif bpm >= 90:
            return RhythmTemplate.MEDIUM
        else:
            return RhythmTemplate.SLOW

    def _calculate_confidence(
        self,
        beat_points: list[BeatPoint],
        bpm: float,
    ) -> float:
        """
        计算置信度

        Args:
            beat_points: 节拍点列表
            bpm: BPM 值

        Returns:
            float: 置信度 0.0-1.0
        """
        if not beat_points:
            return 0.0

        # 计算节拍间隔的一致性
        intervals = []
        for i in range(1, len(beat_points)):
            interval = beat_points[i].timestamp - beat_points[i - 1].timestamp
            intervals.append(interval)

        if not intervals:
            return 0.5

        # 计算标准差
        import numpy as np

        std = np.std(intervals)
        mean = np.mean(intervals)

        # 变异系数
        cv = std / mean if mean > 0 else 1.0

        # 变异系数越小，置信度越高
        confidence = max(0.0, 1.0 - cv)

        return float(confidence)

    def _generate_cut_points(
        self,
        rhythm_analysis: RhythmAnalysis,
        video_path: str,
        tolerance_ms: float,
    ) -> list[CutPoint]:
        """
        生成切镜点

        Args:
            rhythm_analysis: 节奏分析结果
            video_path: 视频文件路径
            tolerance_ms: 容差（毫秒）

        Returns:
            list: 切镜点列表
        """
        cut_points = []

        # 获取视频时长
        video_duration = self._get_video_duration(video_path)

        # 获取模板参数
        template_params = self.TEMPLATE_PARAMS.get(
            rhythm_analysis.rhythm_template,
            self.TEMPLATE_PARAMS[RhythmTemplate.MEDIUM],
        )

        # 基于节拍生成切镜点
        for beat_point in rhythm_analysis.beat_points:
            # 检查是否在视频范围内
            if beat_point.timestamp > video_duration:
                break

            # 只在强拍或高强度节拍处切镜
            if beat_point.is_downbeat or beat_point.strength > 0.6:
                cut_points.append(
                    CutPoint(
                        timestamp=beat_point.timestamp,
                        beat_point=beat_point,
                        confidence=beat_point.strength,
                        cut_type="beat",
                    )
                )

        # 如果切镜点太少，添加额外的切镜点
        if len(cut_points) < 3:
            cut_points = self._add_extra_cut_points(
                cut_points, rhythm_analysis, video_duration, template_params
            )

        # 按时间排序
        cut_points.sort(key=lambda x: x.timestamp)

        return cut_points

    def _get_video_duration(self, video_path: str) -> float:
        """
        获取视频时长

        Args:
            video_path: 视频文件路径

        Returns:
            float: 视频时长（秒）
        """
        try:
            import subprocess

            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"获取视频时长失败: {e}")
            return 0.0

    def _add_extra_cut_points(
        self,
        existing_cut_points: list[CutPoint],
        rhythm_analysis: RhythmAnalysis,
        video_duration: float,
        template_params: dict[str, Any],
    ) -> list[CutPoint]:
        """
        添加额外的切镜点

        Args:
            existing_cut_points: 现有切镜点
            rhythm_analysis: 节奏分析结果
            video_duration: 视频时长
            template_params: 模板参数

        Returns:
            list: 切镜点列表
        """
        extra_points = []
        target_duration = template_params["average_shot_duration"]

        # 计算目标切镜点数量
        target_count = int(video_duration / target_duration)

        # 如果现有切镜点不足，按固定间隔添加
        if len(existing_cut_points) < target_count:
            interval = video_duration / target_count
            for i in range(1, target_count):
                timestamp = i * interval

                # 检查是否与现有切镜点太近
                too_close = False
                for existing in existing_cut_points:
                    if abs(existing.timestamp - timestamp) < interval * 0.5:
                        too_close = True
                        break

                if not too_close:
                    extra_points.append(
                        CutPoint(
                            timestamp=timestamp,
                            beat_point=None,
                            confidence=0.5,
                            cut_type="auto",
                        )
                    )

        return existing_cut_points + extra_points


def sync_bpm(
    video_path: str,
    audio_path: str | None = None,
    template: RhythmTemplate = RhythmTemplate.MEDIUM,
) -> BMPSyncResult:
    """
    便捷函数：同步 BPM 与切镜点

    Args:
        video_path: 视频文件路径
        audio_path: 音频文件路径
        template: 节奏模板

    Returns:
        BMPSyncResult: 同步结果
    """
    synchronizer = BMPSynchronizer()
    return synchronizer.sync(
        video_path=video_path,
        audio_path=audio_path,
        template=template,
    )
