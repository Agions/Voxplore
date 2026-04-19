#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
场景评分器 (Scene Scorer)

提供场景重要性评分功能，包括亮度、运动、音频、场景类型等维度的评分计算。
从 SceneAnalyzerV2 中提取的独立评分逻辑。
"""

from dataclasses import dataclass
from typing import Dict

from .scene_models import SceneType, SceneInfo


# =============================================================================
# 场景类型优先级（数值越高越重要）
# =============================================================================
SCENE_TYPE_PRIORITY: Dict[SceneType, int] = {
    SceneType.LANDSCAPE: 10,     # 风景画面 - 最适合展示
    SceneType.B_ROLL: 8,         # 素材画面 - 适合混剪
    SceneType.ACTION: 6,         # 动作场景
    SceneType.TALKING_HEAD: 4,   # 人物讲话 - 较少使用
    SceneType.TRANSITION: 2,     # 转场 - 不适合
    SceneType.TITLE: 3,          # 标题画面
    SceneType.PRODUCT: 5,        # 产品展示
    SceneType.UNKNOWN: 1,        # 未知 - 最低优先级
}


@dataclass
class SceneScorer:
    """
    场景评分器

    提供独立的场景评分功能，支持以下维度:
    - duration: 时长评分 (3-15秒为最佳)
    - brightness: 亮度评分 (0.3-0.7为最佳)
    - motion: 运动程度评分 (0.2-0.6为最佳)
    - scene_type: 场景类型评分
    - audio: 音频评分

    使用示例:
        scorer = SceneScorer()
        duration_score = scorer.score_duration(5.0)
        brightness_score = scorer.score_brightness(0.5)
        total_score = scorer.calculate_importance(scene)
    """

    def score_duration(self, duration: float) -> float:
        """
        评分时长因素 - 最佳范围: 3-15秒

        Args:
            duration: 时长（秒）

        Returns:
            评分 (0-100)
        """
        if 3.0 <= duration <= 15.0:
            return 100.0
        elif 1.0 <= duration < 3.0 or 15.0 < duration <= 30.0:
            return 60.0
        else:
            return 20.0

    def score_brightness(self, brightness: float) -> float:
        """
        评分亮度因素 - 最佳范围: 0.3-0.7

        Args:
            brightness: 亮度值 (0-1)

        Returns:
            评分 (0-100)
        """
        if 0.3 <= brightness <= 0.7:
            return 100.0
        elif brightness < 0.3:
            return (brightness / 0.3) * 100.0
        else:
            return ((1.0 - brightness) / 0.3) * 100.0

    def score_motion(self, motion: float) -> float:
        """
        评分运动程度因素 - 最佳范围: 0.2-0.6

        Args:
            motion: 运动程度 (0-1)

        Returns:
            评分 (0-100)
        """
        if 0.2 <= motion <= 0.6:
            return 100.0
        elif motion < 0.1:
            return 30.0
        elif motion < 0.2:
            return 30.0 + (motion - 0.1) / 0.1 * 70.0
        elif motion <= 0.9:
            return 100.0 - (motion - 0.6) / 0.3 * 40.0
        else:
            return 20.0

    def score_scene_type(self, scene_type: SceneType) -> float:
        """
        评分场景类型因素

        Args:
            scene_type: 场景类型

        Returns:
            评分 (0-100)
        """
        priority = SCENE_TYPE_PRIORITY.get(scene_type, 1)
        max_priority = max(SCENE_TYPE_PRIORITY.values())
        return (priority / max_priority) * 100.0

    def score_audio(self, audio_level: float) -> float:
        """
        评分音频因素

        Args:
            audio_level: 音频音量 (0-1)

        Returns:
            评分 (0-100)
        """
        return audio_level * 100.0

    def calculate_importance(
        self,
        scene: SceneInfo,
        weights: Dict[str, float],
    ) -> float:
        """
        计算场景重要性综合评分 (0-100)

        Args:
            scene: 场景信息
            weights: 权重字典，包含:
                - duration: 时长权重
                - brightness: 亮度权重
                - motion: 运动权重
                - scene_type: 场景类型权重
                - audio: 音频权重

        Returns:
            综合评分 (0-100)
        """
        score = 50.0  # 基础分

        duration_score = self.score_duration(scene.duration)
        score += duration_score * weights.get('duration', 0.20) * 2

        brightness_score = self.score_brightness(scene.avg_brightness)
        score += brightness_score * weights.get('brightness', 0.15) * 2

        motion_score = self.score_motion(scene.motion_level)
        score += motion_score * weights.get('motion', 0.15) * 2

        type_score = self.score_scene_type(scene.type)
        score += type_score * weights.get('scene_type', 0.30) * 2

        audio_score = self.score_audio(scene.audio_level)
        score += audio_score * weights.get('audio', 0.20) * 2

        return max(0.0, min(100.0, score))

    def calculate_narration_importance(self, scene: SceneInfo) -> float:
        """
        计算默认叙事重要性

        Args:
            scene: 场景信息

        Returns:
            叙事重要性 (0-1)
        """
        type_weight = (
            SCENE_TYPE_PRIORITY.get(scene.type, 1)
            / max(SCENE_TYPE_PRIORITY.values())
        )

        if 3.0 <= scene.duration <= 15.0:
            duration_weight = 1.0
        elif 1.0 <= scene.duration < 3.0 or 15.0 < scene.duration <= 30.0:
            duration_weight = 0.6
        else:
            duration_weight = 0.2

        suitability_weight = scene.suitability_score / 100.0

        importance = (
            type_weight * 0.4 +
            duration_weight * 0.3 +
            suitability_weight * 0.3
        )

        return max(0.0, min(1.0, importance))


__all__ = [
    "SceneScorer",
    "SCENE_TYPE_PRIORITY",
]
