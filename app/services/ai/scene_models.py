#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
场景分析数据模型

定义视频场景分析相关的枚举和数据结构。
"""

from dataclasses import dataclass
from enum import Enum
from typing import List


class SceneType(Enum):
    """场景类型"""
    TALKING_HEAD = "talking_head"    # 人物讲话
    B_ROLL = "b_roll"                # 画面素材
    TITLE = "title"                  # 标题画面
    TRANSITION = "transition"        # 转场
    ACTION = "action"                # 动作场景
    LANDSCAPE = "landscape"          # 风景
    PRODUCT = "product"              # 产品展示
    UNKNOWN = "unknown"              # 未知


@dataclass
class SceneInfo:
    """
    场景信息

    包含场景的时间范围、类型和分析结果
    """
    index: int                       # 场景序号
    start: float                     # 开始时间（秒）
    end: float                       # 结束时间（秒）
    duration: float                  # 持续时长（秒）

    type: SceneType = SceneType.UNKNOWN  # 场景类型
    description: str = ""            # 场景描述

    # 分析数据
    keyframe_path: str = ""          # 关键帧图片路径
    avg_brightness: float = 0.0      # 平均亮度
    motion_level: float = 0.0        # 运动程度 (0-1)
    audio_level: float = 0.0          # 音频音量

    # 适用性评分
    suitability_score: float = 0.0   # 作为解说画面的适用性 (0-100)

    def __post_init__(self):
        self.duration = self.end - self.start


@dataclass
class AnalysisConfig:
    """分析配置"""
    scene_threshold: float = 0.3     # 场景变化阈值 (0-1)
    min_scene_duration: float = 0.5   # 最小场景时长（秒）
    extract_keyframes: bool = True   # 是否提取关键帧
    keyframe_dir: str = ""           # 关键帧保存目录
    analyze_audio: bool = True        # 是否分析音频
    # PySceneDetect 专用配置
    use_pyscenect: bool = True       # 是否优先使用 PySceneDetect
    detector_type: str = "adaptive"   # 检测器类型: "content" 或 "adaptive" 或 "threshold"


__all__ = [
    "SceneType",
    "SceneInfo",
    "AnalysisConfig",
]
