#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频服务数据模型

提供视频制作相关的数据结构和模型。
"""

from .monologue_models import (
    MonologueStyle,
    EmotionType,
    MonologueSegment,
)


__all__ = [
    "MonologueStyle",
    "EmotionType",
    "MonologueSegment",
]
