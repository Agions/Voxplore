#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Subtitle Component
多轨道字幕组件

导出:
    - SubtitleStylePreset: 字幕样式预设数据类
    - SubtitleBlock: 字幕块数据类
    - SubtitleTrack: 字幕轨道数据类
    - MultiTrackSubtitleEditor: 多轨道字幕编辑器数据类
    - SubtitleTrackWidget: 轨道编辑widget
    - TimeRulerWidget: 时间标尺widget
    - SubtitleTimelineWidget: 时间线编辑器widget
    - SubtitleExporter: 字幕导出器
    - SubtitleImporter: 字幕导入器
"""

from .subsubtitles import (
    SubtitlePosition,
    SubtitleAnimation,
    SubtitleStylePreset,
    SubtitleBlock,
    SubtitleTrack,
    MultiTrackSubtitleEditor,
    DEFAULT_PRESETS,
    export_to_jianying_text_track,
)

from .subsubtitles_models import (
    SubtitleExporter,
    SubtitleImporter,
)

from .subsubtitles_widgets import (
    TimeRulerWidget,
    SubtitleBlockWidget,
    SubtitleTrackWidget,
    SubtitleTimelineWidget,
)

__all__ = [
    # 枚举
    "SubtitlePosition",
    "SubtitleAnimation",
    # 数据模型
    "SubtitleStylePreset",
    "SubtitleBlock",
    "SubtitleTrack",
    "MultiTrackSubtitleEditor",
    # 导入导出
    "SubtitleExporter",
    "SubtitleImporter",
    # UI组件
    "TimeRulerWidget",
    "SubtitleBlockWidget",
    "SubtitleTrackWidget",
    "SubtitleTimelineWidget",
    # 工具
    "DEFAULT_PRESETS",
    "export_to_jianying_text_track",
]
