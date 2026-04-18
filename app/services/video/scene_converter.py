#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
场景转换与情感曲线生成器

提供 SceneInfo → SceneSegment、MonologueSegment → NarrationSegment/ClipSegment 的转换，
以及基于独白片段的情感曲线生成。
"""

import uuid
from typing import List, Optional

from app.services.ai.scene_models import SceneInfo, SceneType
from app.services.video.models.perspective_models import (
    ClipSegment,
    NarrationSegment,
    SceneSegment,
    SubjectPosition,
    SubjectRole,
)
from app.services.video.models.monologue_models import EmotionType, MonologueSegment


# ─────────────────────────────────────────────────────────────
# 辅助映射
# ─────────────────────────────────────────────────────────────

def _scene_type_to_str(scene_type: SceneType) -> str:
    """将 SceneType 映射为 scene_type 字符串"""
    mapping = {
        SceneType.TALKING_HEAD: "indoor",
        SceneType.B_ROLL: "outdoor",
        SceneType.TITLE: "transition",
        SceneType.TRANSITION: "transition",
        SceneType.ACTION: "outdoor",
        SceneType.LANDSCAPE: "outdoor",
        SceneType.PRODUCT: "indoor",
        SceneType.UNKNOWN: "indoor",
    }
    return mapping.get(scene_type, "indoor")


def _emotion_type_to_str(emotion: EmotionType) -> str:
    """将 EmotionType 映射为 emotion 字符串"""
    mapping = {
        EmotionType.NEUTRAL: "neutral",
        EmotionType.SAD: "sad",
        EmotionType.HAPPY: "happy",
        EmotionType.ANGRY: "angry",
        EmotionType.CALM: "calm",
        EmotionType.EXCITED: "excited",
        EmotionType.TENDER: "tender",
    }
    return mapping.get(emotion, "neutral")


def _emotion_type_to_intensity(emotion: EmotionType) -> float:
    """将 EmotionType 映射为情感强度值 (0.0–1.0)"""
    mapping = {
        EmotionType.CALM: 0.1,
        EmotionType.NEUTRAL: 0.2,
        EmotionType.TENDER: 0.4,
        EmotionType.SAD: 0.5,
        EmotionType.HAPPY: 0.6,
        EmotionType.EXCITED: 0.8,
        EmotionType.ANGRY: 0.9,
    }
    return mapping.get(emotion, 0.5)


# ─────────────────────────────────────────────────────────────
# SceneConverter
# ─────────────────────────────────────────────────────────────

class SceneConverter:
    """
    场景数据转换器。

    提供三类转换：
    1. SceneInfo (AI 场景分析) → SceneSegment (视角决策)
    2. MonologueSegment (独白) → NarrationSegment (解说片段)
    3. MonologueSegment (独白) → ClipSegment (原片片段)
    """

    @staticmethod
    def from_scene_info(scene_info: SceneInfo) -> SceneSegment:
        """
        将 SceneInfo 转换为 SceneSegment。

        Args:
            scene_info: 来自 scene_models 的场景信息

        Returns:
            对应的 SceneSegment 实例
        """
        # 生成场景 ID
        scene_id = f"scene_{scene_info.index:04d}_{int(scene_info.start * 1000)}"

        # 根据 suitability_score 估算 narration_importance
        narration_importance = scene_info.suitability_score / 100.0

        # 根据平均亮度推断氛围
        if scene_info.avg_brightness > 0.7:
            atmosphere = "bright"
        elif scene_info.avg_brightness < 0.3:
            atmosphere = "dark"
        else:
            atmosphere = "neutral"

        # 关键物体从描述中简单提取（逗号分隔）
        key_objects: List[str] = (
            [k.strip() for k in scene_info.description.split(",") if k.strip()]
            if scene_info.description
            else []
        )

        return SceneSegment(
            scene_id=scene_id,
            start_time=scene_info.start,
            end_time=scene_info.end,
            scene_type=_scene_type_to_str(scene_info.type),
            location="",  # SceneInfo 没有 location 字段
            atmosphere=atmosphere,
            subjects=[],  # SceneInfo 不含主体位置信息
            key_objects=key_objects,
            narration_importance=narration_importance,
        )

    @staticmethod
    def from_monologue_segment(
        segment: MonologueSegment,
        segment_id: Optional[str] = None,
    ) -> NarrationSegment:
        """
        将 MonologueSegment 转换为 NarrationSegment。

        Args:
            segment: 独白片段
            segment_id: 可选的解说片段 ID，默认自动生成

        Returns:
            对应的 NarrationSegment 实例
        """
        if segment_id is None:
            segment_id = f"nar_{uuid.uuid4().hex[:8]}"

        emotion_str = _emotion_type_to_str(segment.emotion)
        duration = segment.audio_duration if segment.audio_duration > 0 else (
            segment.video_end - segment.video_start
        )

        return NarrationSegment(
            segment_id=segment_id,
            text=segment.script,
            start_time=segment.video_start,
            end_time=segment.video_end,
            duration=duration,
            emotion=emotion_str,
            emphasis_words=[],  # 暂不填充
            pause_before=0.0,
            pause_after=0.0,
        )

    @staticmethod
    def monologue_to_clip_segment(
        segment: MonologueSegment,
        source_path: str = "",
        clip_id: Optional[str] = None,
    ) -> ClipSegment:
        """
        将 MonologueSegment 转换为 ClipSegment（原片片段）。

        注意：ClipSegment 通常从原片分析得到，这里提供一种基于独白时间戳的
        近似转换，适用于"纯解说"视频中需要嵌入原片素材的场景。

        Args:
            segment: 独白片段
            source_path: 原片路径
            clip_id: 可选的片段 ID，默认自动生成

        Returns:
            对应的 ClipSegment 实例
        """
        if clip_id is None:
            clip_id = f"clip_{uuid.uuid4().hex[:8]}"

        duration = segment.audio_duration if segment.audio_duration > 0 else (
            segment.video_end - segment.video_start
        )

        # 高情绪时刻视为关键时刻
        is_key = segment.emotion in (EmotionType.EXCITED, EmotionType.ANGRY, EmotionType.HAPPY)

        return ClipSegment(
            clip_id=clip_id,
            source_path=source_path,
            start_time=segment.video_start,
            end_time=segment.video_end,
            duration=duration,
            is_key_moment=is_key,
            key_content=segment.script[:100] if segment.script else "",
        )


# ─────────────────────────────────────────────────────────────
# EmotionCurveGenerator
# ─────────────────────────────────────────────────────────────

class EmotionCurveGenerator:
    """
    情感曲线生成器。

    分析 MonologueSegment 列表，基于各片段的 emotion 字段
    分配强度值，再通过移动均值平滑，生成连续的情绪曲线。
    """

    # EmotionType → 基础强度值 (0.0–1.0)
    EMOTION_INTENSITY_MAP = {
        EmotionType.CALM: 0.1,
        EmotionType.NEUTRAL: 0.2,
        EmotionType.TENDER: 0.4,
        EmotionType.SAD: 0.5,
        EmotionType.HAPPY: 0.6,
        EmotionType.EXCITED: 0.8,
        EmotionType.ANGRY: 0.9,
    }

    # 默认强度（未知情感）
    DEFAULT_INTENSITY: float = 0.3

    def __init__(self, smoothing_window: int = 3):
        """
        Args:
            smoothing_window: 移动均值窗口大小（奇数），默认为 3。
                               值越大曲线越平滑，但细节丢失越多。
        """
        if smoothing_window < 1:
            raise ValueError("smoothing_window must be >= 1")
        if smoothing_window % 2 == 0:
            raise ValueError("smoothing_window must be an odd number")
        self.smoothing_window = smoothing_window

    def generate_curve(
        self,
        segments: List[MonologueSegment],
        normalize: bool = True,
    ) -> List[float]:
        """
        为给定的独白片段列表生成情感强度曲线。

        处理流程：
        1. 遍历片段，根据 emotion 分配基础强度值
        2. 使用镜号扩展：将每个片段的强度展平到其实际时间跨度
        3. 应用移动均值平滑
        4. （可选）归一化到 [0.0, 1.0]

        Args:
            segments: MonologueSegment 列表（按时间顺序）
            normalize: 是否将最终曲线归一化到 [0, 1]

        Returns:
            浮点值列表，每项代表对应时间点的情感强度（0.0–1.0）
        """
        if not segments:
            return []

        # Step 1: 收集原始强度值
        raw_intensities = [
            self.EMOTION_INTENSITY_MAP.get(seg.emotion, self.DEFAULT_INTENSITY)
            for seg in segments
        ]

        # Step 2: 展平到时间轴（每片段强度在其时间范围内保持不变）
        flat_curve: List[float] = []
        for seg, intensity in zip(segments, raw_intensities):
            duration = seg.video_end - seg.video_start
            if duration <= 0:
                continue
            # 按 0.1 秒为步长展平（固定分辨率，便于平滑）
            steps = max(1, int(duration * 10))
            flat_curve.extend([intensity] * steps)

        if not flat_curve:
            return []

        # Step 3: 移动均值平滑
        smoothed = self._moving_average(flat_curve, self.smoothing_window)

        # Step 4: 归一化
        if normalize:
            smoothed = self._normalize(smoothed)

        return smoothed

    @staticmethod
    def _moving_average(data: List[float], window: int) -> List[float]:
        """计算简单移动均值 (SMA)。"""
        if window <= 1 or len(data) <= window:
            return list(data)

        half = window // 2
        result: List[float] = []
        n = len(data)

        for i in range(n):
            start = max(0, i - half)
            end = min(n, i + half + 1)
            result.append(sum(data[start:end]) / (end - start))

        return result

    @staticmethod
    def _normalize(data: List[float]) -> List[float]:
        """将数据归一化到 [0.0, 1.0] 范围。"""
        if not data:
            return []
        min_val = min(data)
        max_val = max(data)
        if max_val - min_val < 1e-6:
            # 常数曲线，直接返回零到 max
            return [0.0 for _ in data]
        return [(v - min_val) / (max_val - min_val) for v in data]

    def get_segment_emotions(
        self,
        segments: List[MonologueSegment],
    ) -> List[float]:
        """
        返回每个片段的平均情感强度（不做时间展平与平滑）。
        用于快速检查各片段的情感分布。

        Returns:
            与输入片段一一对应的强度值列表
        """
        return [
            self.EMOTION_INTENSITY_MAP.get(seg.emotion, self.DEFAULT_INTENSITY)
            for seg in segments
        ]


__all__ = [
    "SceneConverter",
    "EmotionCurveGenerator",
]
