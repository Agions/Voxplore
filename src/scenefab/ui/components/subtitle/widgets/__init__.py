#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Subtitle Widgets - 字幕编辑器 UI 组件

从 subtitle_wgts.py 拆分出来的独立 Widget 类。
"""

from .subtitle_block import SubtitleBlockWidget
from .subtitle_track import SubtitleTrackWidget
from .time_ruler import TimeRulerWidget
from .timeline_widget import SubtitleTimelineWidget

__all__ = [
    "TimeRulerWidget",
    "SubtitleBlockWidget",
    "SubtitleTrackWidget",
    "SubtitleTimelineWidget",
]
