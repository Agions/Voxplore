"""
SceneFab 特征提取与情绪分类混入

提供音频特征提取、视觉特征提取、情绪分类、场景类型判断和描述生成等方法。
"""

import logging
from typing import Any

from scenefab.services.emotion.models import (
    EmotionLabel,
    SceneType,
)

logger = logging.getLogger(__name__)


class FeatureExtractorsMixin:
    """特征提取与情绪分类混入类"""

    def _generate_emotion_curve(
        self,
        scene_emotions: list,
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
        scene_emotions: list,
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

            # 优先使用缓存的音频数据
            if video_path in self._audio_cache:
                cached = self._audio_cache[video_path]
                y_full, sr = cached["y"], cached["sr"]
                # 从缓存中切片
                start_sample = int(max(0, timestamp - 2) * sr)
                end_sample = int((timestamp + 2) * sr)
                y = y_full[start_sample:end_sample]
            else:
                # 降级：直接加载片段
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
