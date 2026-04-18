#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Emotion Controller Component
情感控制器组件 - 情感曲线编辑与预设管理

导出:
    - EmotionController: 主控制器 widget
    - EmotionCurveWidget: 自定义绘制的情感曲线 widget
    - EmotionPresetButton: 情感预设按钮
"""

from .emotion_controller import EmotionController
from .emotion_curve_widget import EmotionCurveWidget
from .emotion_presets import EMOTION_PRESETS, EmotionPresetButton

__all__ = [
    "EmotionController",
    "EmotionCurveWidget", 
    "EmotionPresetButton",
    "EMOTION_PRESETS",
]
