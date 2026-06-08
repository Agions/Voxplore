"""
SceneFab 情绪点检测器核心逻辑

提供视频情绪检测流程编排：采样、并行/串行分析、
情绪曲线生成和高峰时刻检测。
"""

import logging
from typing import Any

from scenefab.services.emotion.feature_extractors import FeatureExtractorsMixin
from scenefab.services.emotion.models import (
    EmotionDetectionResult,
    EmotionLabel,
    RecommendedPace,
    SceneEmotion,
    SceneType,
)

logger = logging.getLogger(__name__)


class EmotionDetector(FeatureExtractorsMixin):
    """
    情绪点检测器

    基于多模态分析（音频 + 视觉）检测视频中的情绪点。

    使用方法：
        detector = EmotionDetector()
        result = detector.detect("path/to/video.mp4")
        for emotion in result.scene_emotions:
            print(f"{emotion.timestamp}秒: {emotion.emotion_label} ({emotion.intensity})")
    """

    # 情绪强度阈值
    INTENSITY_THRESHOLDS = {
        "high": 0.7,
        "medium": 0.4,
        "low": 0.0,
    }

    # 场景类型对应的推荐节奏
    SCENE_PACE_MAPPING = {
        SceneType.ACTION: RecommendedPace.FAST,
        SceneType.DIALOGUE: RecommendedPace.NORMAL,
        SceneType.REVERSAL: RecommendedPace.FAST,
        SceneType.CLIMAX: RecommendedPace.FAST,
        SceneType.RESOLUTION: RecommendedPace.SLOW,
        SceneType.TRANSITION: RecommendedPace.NORMAL,
    }

    def __init__(self, use_visual_analysis: bool = True, max_workers: int = 4):
        """
        初始化情绪检测器

        Args:
            use_visual_analysis: 是否使用视觉分析
            max_workers: 并行处理线程数
        """
        self.use_visual_analysis = use_visual_analysis
        self.max_workers = max_workers
        self._frame_cache: dict[str, Any] = {}  # 帧缓存
        self._audio_cache: dict[str, Any] = {}  # 音频缓存
        logger.info(f"EmotionDetector 初始化完成 (workers={max_workers})")

    def detect(
        self,
        video_path: str,
        sample_interval: float = 5.0,
        parallel: bool = True,
    ) -> EmotionDetectionResult:
        """
        检测视频中的情绪点

        Args:
            video_path: 视频文件路径
            sample_interval: 采样间隔（秒）
            parallel: 是否并行处理

        Returns:
            EmotionDetectionResult: 检测结果
        """
        logger.info(f"开始情绪检测: {video_path}")

        # 获取视频时长
        duration = self._get_video_duration(video_path)

        # 采样时间点
        timestamps = [i * sample_interval for i in range(int(duration / sample_interval) + 1)]
        timestamps = [t for t in timestamps if t < duration]

        # 预加载音频（并行模式下共享）
        if parallel and len(timestamps) > 1:
            self._preload_audio(video_path)

        # 检测每个时间点的情绪
        if parallel and len(timestamps) > 1:
            scene_emotions = self._detect_parallel(video_path, timestamps)
        else:
            scene_emotions = self._detect_sequential(video_path, timestamps)

        # 生成情绪曲线
        emotion_curve = self._generate_emotion_curve(scene_emotions)

        # 检测情绪高峰时刻
        peak_moments = self._detect_peak_moments(scene_emotions)

        result = EmotionDetectionResult(
            video_path=video_path,
            duration=duration,
            scene_emotions=scene_emotions,
            emotion_curve=emotion_curve,
            peak_moments=peak_moments,
        )

        logger.info(f"情绪检测完成: 检测到 {len(scene_emotions)} 个情绪点")
        return result

    def _preload_audio(self, video_path: str):
        """预加载音频数据（避免重复读取）"""
        try:
            import librosa
            y, sr = librosa.load(video_path, sr=22050)
            self._audio_cache[video_path] = {"y": y, "sr": sr}
            logger.debug(f"音频预加载完成: {len(y)/sr:.1f}s")
        except Exception as e:
            logger.warning(f"音频预加载失败: {e}")

    def _detect_parallel(self, video_path: str, timestamps: list[float]) -> list[SceneEmotion]:
        """并行检测情绪"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = [None] * len(timestamps)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {
                executor.submit(self._analyze_at_timestamp, video_path, ts): i
                for i, ts in enumerate(timestamps)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    logger.warning(f"时间点 {timestamps[idx]}s 分析失败: {e}")
                    results[idx] = self._fallback_emotion(timestamps[idx])

        return [r for r in results if r is not None]

    def _detect_sequential(self, video_path: str, timestamps: list[float]) -> list[SceneEmotion]:
        """串行检测情绪"""
        scene_emotions = []
        for timestamp in timestamps:
            try:
                emotion = self._analyze_at_timestamp(video_path, timestamp)
                scene_emotions.append(emotion)
            except Exception as e:
                logger.warning(f"时间点 {timestamp}s 分析失败: {e}")
                scene_emotions.append(self._fallback_emotion(timestamp))
        return scene_emotions

    def _fallback_emotion(self, timestamp: float) -> SceneEmotion:
        """失败时的降级情绪数据"""
        return SceneEmotion(
            timestamp=timestamp,
            scene_type=SceneType.TRANSITION,
            emotion_label=EmotionLabel.NEUTRAL,
            intensity=0.5,
            recommended_pace=RecommendedPace.NORMAL,
            confidence=0.0,
            description="分析失败，使用默认值",
        )

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
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"获取视频时长失败: {e}")
            return 0.0

    def _analyze_at_timestamp(self, video_path: str, timestamp: float) -> SceneEmotion:
        """
        分析指定时间点的情绪

        Args:
            video_path: 视频文件路径
            timestamp: 时间戳（秒）

        Returns:
            SceneEmotion: 场景情绪数据
        """
        # 提取音频特征
        audio_features = self._extract_audio_features(video_path, timestamp)

        # 提取视觉特征（如果启用）
        visual_features = {}
        if self.use_visual_analysis:
            visual_features = self._extract_visual_features(video_path, timestamp)

        # 基于特征判断情绪
        emotion_label, intensity, confidence = self._classify_emotion(
            audio_features, visual_features
        )

        # 判断场景类型
        scene_type = self._classify_scene_type(
            audio_features, visual_features, intensity
        )

        # 获取推荐节奏
        recommended_pace = self.SCENE_PACE_MAPPING.get(
            scene_type, RecommendedPace.NORMAL
        )

        # 生成描述
        description = self._generate_description(
            scene_type, emotion_label, intensity
        )

        return SceneEmotion(
            timestamp=timestamp,
            scene_type=scene_type,
            emotion_label=emotion_label,
            intensity=intensity,
            recommended_pace=recommended_pace,
            confidence=confidence,
            description=description,
            audio_features=audio_features,
            visual_features=visual_features,
        )


def detect_emotions(
    video_path: str,
    sample_interval: float = 5.0,
    use_visual_analysis: bool = True,
) -> EmotionDetectionResult:
    """
    便捷函数：检测视频情绪点

    Args:
        video_path: 视频文件路径
        sample_interval: 采样间隔（秒）
        use_visual_analysis: 是否使用视觉分析

    Returns:
        EmotionDetectionResult: 检测结果
    """
    detector = EmotionDetector(use_visual_analysis=use_visual_analysis)
    return detector.detect(video_path, sample_interval=sample_interval)
