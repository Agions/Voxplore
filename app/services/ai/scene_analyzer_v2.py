#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
场景分析器 V2 (Scene Analyzer V2)

在 SceneAnalyzer 基础上扩展了重要性评分和关键时刻提取功能。
适合用于 AI 解说和智能混剪场景。
"""

import logging

from typing import List, Optional, Callable

from .scene_models import SceneType, SceneInfo, AnalysisConfig
from .scene_analyzer import SceneAnalyzer

logger = logging.getLogger(__name__)


class SceneAnalyzerV2(SceneAnalyzer):
    """
    场景分析器 V2

    在 SceneAnalyzer 基础上扩展了重要性评分和关键时刻提取功能。
    适合用于 AI 解说和智能混剪场景。
    """

    def __init__(self, config: Optional[AnalysisConfig] = None):
        """
        初始化场景分析器 V2

        Args:
            config: 分析配置，如果为 None 则使用默认配置
        """
        super().__init__(config)
        self._importance_weights = {
            'duration': 0.20,
            'brightness': 0.15,
            'motion': 0.15,
            'scene_type': 0.30,
            'audio': 0.20,
        }
        self._scorer = SceneScorer()

    def analyze_with_importance(
        self,
        video_path: str,
        narration_importance_fn: Optional[Callable[[SceneInfo], float]] = None,
    ) -> List[SceneInfo]:
        """
        分析视频场景并计算重要性评分

        在原有 analyze() 方法基础上，为每个场景计算 suitability_score
        和可选的 narration_importance。

        Args:
            video_path: 视频文件路径
            narration_importance_fn: 可选的回调函数，用于计算叙事重要性。
                                     函数签名: (SceneInfo) -> float (0-1)
                                     如果为 None，则使用默认计算方法

        Returns:
            场景列表，每个场景都包含计算好的 suitability_score

        Raises:
            FileNotFoundError: 视频文件不存在
        """
        scenes = super().analyze(video_path)

        for scene in scenes:
            scene.suitability_score = self._calculate_enhanced_suitability(scene)

            if narration_importance_fn is not None:
                scene.narration_importance = narration_importance_fn(scene)
            elif not hasattr(scene, 'narration_importance') or scene.narration_importance <= 0:
                scene.narration_importance = self._calculate_default_narration_importance(scene)
            # else: 保留现有 scene.narration_importance 值

        return scenes

    def _calculate_enhanced_suitability(self, scene: SceneInfo) -> float:
        """计算增强版适用性评分 (0-100)"""
        return self._scorer.calculate_importance(scene, self._importance_weights)

    def _calculate_default_narration_importance(self, scene: SceneInfo) -> float:
        """计算默认叙事重要性"""
        return self._scorer.calculate_narration_importance(scene)

    def extract_key_moments(
        self,
        scenes: List[SceneInfo],
        top_k: int = 5,
        min_score: float = 30.0,
    ) -> List[SceneInfo]:
        """提取关键时刻（得分最高的场景）"""
        filtered = [s for s in scenes if s.suitability_score >= min_score]

        sorted_scenes = sorted(
            filtered,
            key=lambda s: s.suitability_score,
            reverse=True
        )

        return sorted_scenes[:top_k]

    def extract_key_moments_by_type(
        self,
        scenes: List[SceneInfo],
        scene_type: SceneType,
        top_k: int = 3,
    ) -> List[SceneInfo]:
        """按场景类型提取关键时刻"""
        filtered = [s for s in scenes if s.type == scene_type]

        sorted_scenes = sorted(
            filtered,
            key=lambda s: s.suitability_score,
            reverse=True
        )

        return sorted_scenes[:top_k]

    def generate_scene_context_prompt(self, scenes: List[SceneInfo]) -> str:
        """生成场景上下文提示（用于 ScriptGenerator）"""
        if not scenes:
            return "## 场景列表\n\n*暂无场景数据*"

        lines = ["## 场景列表\n"]

        for i, scene in enumerate(scenes, 1):
            start_str = self._format_timestamp(scene.start)
            end_str = self._format_timestamp(scene.end)

            type_name = self._get_scene_type_name_cn(scene.type)

            lines.append(f"{i}. **{start_str} - {end_str}** {type_name}")
            lines.append(f"   - 类型: `{scene.type.value}`")
            lines.append(f"   - 评分: {scene.suitability_score:.0f}/100")

            if scene.description:
                lines.append(f"   - 描述: {scene.description}")

            details = []
            if scene.avg_brightness > 0:
                brightness_desc = self._describe_brightness(scene.avg_brightness)
                details.append(f"亮度{brightness_desc}")
            if scene.motion_level > 0:
                motion_desc = self._describe_motion(scene.motion_level)
                details.append(f"运动{motion_desc}")
            if scene.audio_level > 0:
                details.append(f"音频{'有' if scene.audio_level > 0.3 else '弱'}")

            if details:
                lines.append(f"   - 特征: {', '.join(details)}")

            lines.append("")

        return "\n".join(lines)

    def generate_brief_scene_summary(
        self,
        scenes: List[SceneInfo],
        max_scenes: int = 10,
    ) -> str:
        """生成简短场景摘要（适用于提示词）"""
        if not scenes:
            return "视频包含0个有效场景。"

        sorted_scenes = sorted(
            scenes,
            key=lambda s: s.suitability_score,
            reverse=True
        )[:max_scenes]

        parts = [f"视频共 {len(scenes)} 个场景，选取最重要的 {len(sorted_scenes)} 个：\n"]

        for scene in sorted_scenes:
            start_str = self._format_timestamp(scene.start)
            type_name = self._get_scene_type_name_cn(scene.type)
            score = scene.suitability_score

            parts.append(f"- [{start_str}] {type_name} (评分:{score:.0f})")

        return "\n".join(parts)

    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳为 MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _get_scene_type_name_cn(self, scene_type: SceneType) -> str:
        """获取场景类型中文名"""
        names = {
            SceneType.LANDSCAPE: "风景画面",
            SceneType.B_ROLL: "素材画面",
            SceneType.ACTION: "动作场景",
            SceneType.TALKING_HEAD: "人物讲话",
            SceneType.TRANSITION: "转场",
            SceneType.TITLE: "标题画面",
            SceneType.PRODUCT: "产品展示",
            SceneType.UNKNOWN: "未知",
        }
        return names.get(scene_type, "未知")

    def _describe_brightness(self, brightness: float) -> str:
        """描述亮度"""
        if brightness < 0.3:
            return "暗"
        elif brightness > 0.7:
            return "亮"
        else:
            return "适中"

    def _describe_motion(self, motion: float) -> str:
        """描述运动程度"""
        if motion < 0.2:
            return "静态"
        elif motion > 0.7:
            return "剧烈"
        else:
            return "适中"


# =============================================================================
# 重新导出（保持向后兼容）

# Backward compatibility alias
SceneAnalyzer = SceneAnalyzerV2
