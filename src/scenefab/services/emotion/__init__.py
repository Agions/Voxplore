"""
SceneFab 情绪点检测模块

功能：
1. 多模态情绪分析（音频 + 视觉）
2. 情绪锚点自动标记
3. 场景类型识别
4. 推荐节奏生成

输出数据结构：
SceneEmotion {
    timestamp: float,
    scene_type: "action" | "dialogue" | "reversal" | "climax" | "resolution",
    emotion_label: "tension" | "joy" | "sadness" | "surprise" | "neutral",
    intensity: 0.0 ~ 1.0,
    recommended_pace: "fast" | "normal" | "slow",
}
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SceneType(str, Enum):
    """场景类型"""
    ACTION = "action"  # 动作场景
    DIALOGUE = "dialogue"  # 对话场景
    REVERSAL = "reversal"  # 反转场景
    CLIMAX = "climax"  # 高潮场景
    RESOLUTION = "resolution"  # 结局场景
    TRANSITION = "transition"  # 过渡场景


class EmotionLabel(str, Enum):
    """情绪标签"""
    TENSION = "tension"  # 紧张
    JOY = "joy"  # 愉快
    SADNESS = "sadness"  # 悲伤
    SURPRISE = "surprise"  # 惊讶
    FEAR = "fear"  # 恐惧
    ANGER = "anger"  # 愤怒
    NEUTRAL = "neutral"  # 中性


class RecommendedPace(str, Enum):
    """推荐节奏"""
    FAST = "fast"  # 快节奏
    NORMAL = "normal"  # 正常节奏
    SLOW = "slow"  # 慢节奏


@dataclass
class SceneEmotion:
    """场景情绪数据"""
    timestamp: float  # 时间戳（秒）
    scene_type: SceneType  # 场景类型
    emotion_label: EmotionLabel  # 情绪标签
    intensity: float  # 情绪强度 0.0-1.0
    recommended_pace: RecommendedPace  # 推荐节奏
    confidence: float  # 置信度 0.0-1.0
    description: str = ""  # 场景描述
    audio_features: dict[str, Any] = field(default_factory=dict)  # 音频特征
    visual_features: dict[str, Any] = field(default_factory=dict)  # 视觉特征


@dataclass
class EmotionDetectionResult:
    """情绪检测结果"""
    video_path: str
    duration: float  # 视频时长（秒）
    scene_emotions: list[SceneEmotion] = field(default_factory=list)
    emotion_curve: list[dict[str, Any]] = field(default_factory=list)  # 情绪曲线数据
    peak_moments: list[dict[str, Any]] = field(default_factory=list)  # 情绪高峰时刻
    detection_time: str = ""
    detector_version: str = "1.0.0"


class EmotionDetector:
    """
    情绪点检测器

    基于多模态分析（音频 + 视觉）检测视频中的情绪点。

    使用方法：
        detector = EmotionDetector()
        result = detector.detect("path/to/video.mp4")
        for emotion in result.scene_emomotions:
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

    def __init__(self, use_visual_analysis: bool = True):
        """
        初始化情绪检测器

        Args:
            use_visual_analysis: 是否使用视觉分析
        """
        self.use_visual_analysis = use_visual_analysis
        logger.info("EmotionDetector 初始化完成")

    def detect(
        self,
        video_path: str,
        sample_interval: float = 5.0,
    ) -> EmotionDetectionResult:
        """
        检测视频中的情绪点

        Args:
            video_path: 视频文件路径
            sample_interval: 采样间隔（秒）

        Returns:
            EmotionDetectionResult: 检测结果
        """
        logger.info(f"开始情绪检测: {video_path}")

        # 获取视频时长
        duration = self._get_video_duration(video_path)

        # 采样时间点
        timestamps = [i * sample_interval for i in range(int(duration / sample_interval) + 1)]

        # 检测每个时间点的情绪
        scene_emotions = []
        for timestamp in timestamps:
            if timestamp >= duration:
                break

            emotion = self._analyze_at_timestamp(video_path, timestamp)
            scene_emotions.append(emotion)

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

    def _extract_audio_features(self, video_path: str, timestamp: float) -> dict[str, Any]:
        """
        提取音频特征

        Args:
            video_path: 视频文件路径
            timestamp: 时间戳（秒）

        Returns:
            dict: 音频特征
        """
        try:
            import librosa
            import numpy as np

            # 加载音频片段（前后 2 秒）
            start_time = max(0, timestamp - 2)
            end_time = timestamp + 2

            y, sr = librosa.load(
                video_path,
                sr=22050,
                offset=start_time,
                duration=end_time - start_time,
            )

            # 提取特征
            features = {
                "energy": float(np.mean(librosa.feature.rms(y=y))),
                "zero_crossing_rate": float(np.mean(librosa.feature.zero_crossing_rate(y))),
                "spectral_centroid": float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))),
                "tempo": float(librosa.beat.tempo(y=y, sr=sr)[0]) if len(y) > 0 else 0,
            }

            # 计算音调变化
            if len(y) > 0:
                pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
                features["pitch_variation"] = float(np.std(pitches[pitches > 0])) if np.any(pitches > 0) else 0
            else:
                features["pitch_variation"] = 0

            return features

        except Exception as e:
            logger.warning(f"音频特征提取失败: {e}")
            return {
                "energy": 0.5,
                "zero_crossing_rate": 0.5,
                "spectral_centroid": 1000,
                "tempo": 100,
                "pitch_variation": 0,
            }

    def _extract_visual_features(self, video_path: str, timestamp: float) -> dict[str, Any]:
        """
        提取视觉特征

        Args:
            video_path: 视频文件路径
            timestamp: 时间戳（秒）

        Returns:
            dict: 视觉特征
        """
        try:
            import cv2
            import numpy as np

            # 打开视频
            cap = cv2.VideoCapture(video_path)
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)

            ret, frame = cap.read()
            cap.release()

            if not ret:
                return {"brightness": 0.5, "contrast": 0.5, "motion": 0}

            # 转换为灰度图
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 计算特征
            features = {
                "brightness": float(np.mean(gray) / 255),
                "contrast": float(np.std(gray) / 255),
                "motion": 0,  # 需要前后帧对比
            }

            return features

        except Exception as e:
            logger.warning(f"视觉特征提取失败: {e}")
            return {"brightness": 0.5, "contrast": 0.5, "motion": 0}

    def _classify_emotion(
        self,
        audio_features: dict[str, Any],
        visual_features: dict[str, Any],
    ) -> tuple[EmotionLabel, float, float]:
        """
        分类情绪

        Args:
            audio_features: 音频特征
            visual_features: 视觉特征

        Returns:
            tuple: (情绪标签, 强度, 置信度)
        """
        # 基于音频特征的简单分类
        energy = audio_features.get("energy", 0.5)
        tempo = audio_features.get("tempo", 100)
        pitch_variation = audio_features.get("pitch_variation", 0)

        # 计算情绪强度
        intensity = min(1.0, energy * 2)

        # 判断情绪类型
        if energy > 0.7 and tempo > 120:
            emotion_label = EmotionLabel.TENSION
            confidence = 0.7
        elif energy > 0.6 and pitch_variation > 50:
            emotion_label = EmotionLabel.SURPRISE
            confidence = 0.6
        elif energy < 0.3 and tempo < 80:
            emotion_label = EmotionLabel.SADNESS
            confidence = 0.6
        elif energy > 0.5 and tempo > 100:
            emotion_label = EmotionLabel.JOY
            confidence = 0.5
        else:
            emotion_label = EmotionLabel.NEUTRAL
            confidence = 0.8

        return emotion_label, intensity, confidence

    def _classify_scene_type(
        self,
        audio_features: dict[str, Any],
        visual_features: dict[str, Any],
        intensity: float,
    ) -> SceneType:
        """
        分类场景类型

        Args:
            audio_features: 音频特征
            visual_features: 视觉特征
            intensity: 情绪强度

        Returns:
            SceneType: 场景类型
        """
        energy = audio_features.get("energy", 0.5)
        tempo = audio_features.get("tempo", 100)

        # 基于特征判断场景类型
        if intensity > 0.7 and energy > 0.6:
            return SceneType.CLIMAX
        elif energy > 0.5 and tempo > 110:
            return SceneType.ACTION
        elif intensity > 0.6 and energy > 0.4:
            return SceneType.REVERSAL
        elif energy < 0.3:
            return SceneType.RESOLUTION
        else:
            return SceneType.DIALOGUE

    def _generate_description(
        self,
        scene_type: SceneType,
        emotion_label: EmotionLabel,
        intensity: float,
    ) -> str:
        """
        生成场景描述

        Args:
            scene_type: 场景类型
            emotion_label: 情绪标签
            intensity: 情绪强度

        Returns:
            str: 场景描述
        """
        intensity_desc = "强烈" if intensity > 0.7 else "中等" if intensity > 0.4 else "轻微"

        scene_desc = {
            SceneType.ACTION: "动作场景",
            SceneType.DIALOGUE: "对话场景",
            SceneType.REVERSAL: "反转场景",
            SceneType.CLIMAX: "高潮场景",
            SceneType.RESOLUTION: "结局场景",
            SceneType.TRANSITION: "过渡场景",
        }

        emotion_desc = {
            EmotionLabel.TENSION: "紧张",
            EmotionLabel.JOY: "愉快",
            EmotionLabel.SADNESS: "悲伤",
            EmotionLabel.SURPRISE: "惊讶",
            EmotionLabel.FEAR: "恐惧",
            EmotionLabel.ANGER: "愤怒",
            EmotionLabel.NEUTRAL: "平静",
        }

        return f"{scene_desc.get(scene_type, '未知场景')}，{intensity_desc}{emotion_desc.get(emotion_label, '未知情绪')}"

    def _generate_emotion_curve(
        self,
        scene_emotions: list[SceneEmotion],
    ) -> list[dict[str, Any]]:
        """
        生成情绪曲线数据

        Args:
            scene_emotions: 场景情绪列表

        Returns:
            list: 情绪曲线数据
        """
        curve_data = []
        for emotion in scene_emotions:
            curve_data.append({
                "timestamp": emotion.timestamp,
                "intensity": emotion.intensity,
                "emotion": emotion.emotion_label.value,
                "scene_type": emotion.scene_type.value,
            })
        return curve_data

    def _detect_peak_moments(
        self,
        scene_emotions: list[SceneEmotion],
    ) -> list[dict[str, Any]]:
        """
        检测情绪高峰时刻

        Args:
            scene_emotions: 场景情绪列表

        Returns:
            list: 情绪高峰时刻
        """
        peak_moments = []

        for i in range(1, len(scene_emotions) - 1):
            prev_intensity = scene_emotions[i - 1].intensity
            curr_intensity = scene_emotions[i].intensity
            next_intensity = scene_emotions[i + 1].intensity

            # 检测峰值（比前后都高）
            if curr_intensity > prev_intensity and curr_intensity > next_intensity:
                if curr_intensity > self.INTENSITY_THRESHOLDS["high"]:
                    peak_moments.append({
                        "timestamp": scene_emotions[i].timestamp,
                        "intensity": curr_intensity,
                        "emotion": scene_emotions[i].emotion_label.value,
                        "scene_type": scene_emotions[i].scene_type.value,
                        "description": scene_emotions[i].description,
                    })

        return peak_moments


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
