#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Subtitle Track Widget (Backward Compatibility)

此文件已弃用，请使用 subtitle.widgets 模块。
"""

# Re-export from new module structure for backward compatibility
from .widgets.time_ruler import TimeRulerWidget
from .widgets.subtitle_block import SubtitleBlockWidget
from .widgets.subtitle_track import SubtitleTrackWidget
from .widgets.timeline_widget import SubtitleTimelineWidget

__all__ = [
    "TimeRulerWidget",
    "SubtitleBlockWidget",
    "SubtitleTrackWidget",
    "SubtitleTimelineWidget",
]
