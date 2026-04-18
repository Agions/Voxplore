#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 时间线组件
多轨时间线编辑器：视频轨 / 音频轨 / 字幕轨
"""

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QToolButton
)
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QMouseEvent, QPaintEvent


class TimelineClip:
    """时间线上的片段"""
    def __init__(self, clip_id: str, start: float, end: float,
                 label: str = "", color: str = "#667eea", track_type: str = "video"):
        self.id = clip_id
        self.start = start
        self.end = end
        self.label = label
        self.color = color
        self.track_type = track_type
        self.selected = False

    @property
    def duration(self) -> float:
        return self.end - self.start


class TimelineTrackWidget(QFrame):
    """单条轨道"""
    clip_clicked = Signal(str)  # clip_id
    clip_moved = Signal(str, float)  # clip_id, new_start

    def __init__(self, track_id: str, track_type: str, label: str, color: str, parent=None):
        super().__init__(parent)
        self.track_id = track_id
        self.track_type = track_type
        self.track_label = label
        self.track_color = QColor(color)
        self.clips: List[TimelineClip] = []
        self.total_duration = 60.0  # 默认60秒
        self.pixels_per_second = 10.0
        self._drag_clip: Optional[TimelineClip] = None
        self._drag_offset = 0.0

        self.setFixedHeight(48)
        self.setMinimumWidth(600)
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: #1e1e1e; border: none; border-bottom: 1px solid #333;")

    def set_duration(self, duration: float):
        self.total_duration = max(duration, 1)
        self.setMinimumWidth(int(self.total_duration * self.pixels_per_second) + 80)
        self.update()

    def set_zoom(self, pixels_per_second: float):
        self.pixels_per_second = max(2, min(pixels_per_second, 100))
        self.setMinimumWidth(int(self.total_duration * self.pixels_per_second) + 80)
        self.update()

    def add_clip(self, clip: TimelineClip):
        self.clips.append(clip)
        self.update()

    def clear_clips(self):
        self.clips.clear()
        self.update()

    def _time_to_x(self, t: float) -> int:
        return int(80 + t * self.pixels_per_second)

    def _x_to_time(self, x: int) -> float:
        return max(0, (x - 80) / self.pixels_per_second)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 轨道标签
        painter.setPen(QColor("#999"))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(QRect(4, 0, 72, self.height()), Qt.AlignmentFlag.AlignVCenter, self.track_label)

        # 绘制片段
        for clip in self.clips:
            x1 = self._time_to_x(clip.start)
            x2 = self._time_to_x(clip.end)
            w = max(x2 - x1, 4)
            h = self.height() - 8
            y = 4

            # 片段背景
            color = QColor(clip.color)
            if clip.selected:
                color = color.lighter(130)
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawRoundedRect(x1, y, w, h, 3, 3)

            # 片段标签
            if w > 40:
                painter.setPen(QColor("#fff"))
                painter.setFont(QFont("Arial", 8))
                text_rect = QRect(x1 + 4, y, w - 8, h)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                                 clip.label[:20])

        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            t = self._x_to_time(int(event.position().x()))
            for clip in self.clips:
                if clip.start <= t <= clip.end:
                    # 选中
                    for c in self.clips:
                        c.selected = False
                    clip.selected = True
                    self._drag_clip = clip
                    self._drag_offset = t - clip.start
                    self.clip_clicked.emit(clip.id)
                    self.update()
                    return
            # 取消选中
            for c in self.clips:
                c.selected = False
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._drag_clip:
            self.clip_moved.emit(self._drag_clip.id, self._drag_clip.start)
            self._drag_clip = None

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_clip:
            t = self._x_to_time(int(event.position().x())) - self._drag_offset
            dur = self._drag_clip.duration
            t = max(0, min(t, self.total_duration - dur))
            self._drag_clip.start = t
            self._drag_clip.end = t + dur
            self.update()


class TimelineRuler(QWidget):
    """时间标尺"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self.total_duration = 60.0
        self.pixels_per_second = 10.0
        self.setStyleSheet("background-color: #252525;")

    def set_params(self, duration: float, pps: float):
        self.total_duration = duration
        self.pixels_per_second = pps
        self.setMinimumWidth(int(duration * pps) + 80)
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setPen(QColor("#666"))
        painter.setFont(QFont("Arial", 8))

        # 计算刻度间隔
        interval = 5  # 5秒
        if self.pixels_per_second > 20:
            interval = 1
        elif self.pixels_per_second > 10:
            interval = 2

        t = 0.0
        while t <= self.total_duration:
            x = int(80 + t * self.pixels_per_second)
            painter.drawLine(x, 16, x, 24)

            # 时间标签
            minutes = int(t // 60)
            seconds = int(t % 60)
            painter.drawText(x - 15, 14, f"{minutes}:{seconds:02d}")
            t += interval

        painter.end()


class Timeline(QWidget):
    """多轨时间线编辑器"""

    clip_selected = Signal(str)  # clip_id
    position_changed = Signal(float)  # seconds

    def __init__(self, application=None):
        super().__init__(application)
        self.application = application
        self._tracks: List[TimelineTrackWidget] = []
        self._duration = 60.0
        self._pps = 10.0  # pixels per second
        self._playback_pos = 0.0

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 4, 8, 4)

        self.zoom_in_btn = QToolButton()
        self.zoom_in_btn.setText("🔍+")
        self.zoom_in_btn.clicked.connect(lambda: self._set_zoom(self._pps * 1.5))

        self.zoom_out_btn = QToolButton()
        self.zoom_out_btn.setText("🔍-")
        self.zoom_out_btn.clicked.connect(lambda: self._set_zoom(self._pps / 1.5))

        self.fit_btn = QToolButton()
        self.fit_btn.setText("适配")
        self.fit_btn.clicked.connect(self._fit_to_view)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #999; font-size: 11px;")

        toolbar.addWidget(self.zoom_out_btn)
        toolbar.addWidget(self.zoom_in_btn)
        toolbar.addWidget(self.fit_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.time_label)

        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar)
        toolbar_widget.setStyleSheet("background-color: #2a2a2a; border-bottom: 1px solid #444;")
        layout.addWidget(toolbar_widget)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("background-color: #1a1a1a; border: none;")

        self._track_container = QWidget()
        self._track_layout = QVBoxLayout(self._track_container)
        self._track_layout.setContentsMargins(0, 0, 0, 0)
        self._track_layout.setSpacing(0)

        # 标尺
        self._ruler = TimelineRuler()
        self._track_layout.addWidget(self._ruler)

        # 默认三轨道
        self._add_track("video", "🎬 视频", "#667eea")
        self._add_track("audio", "🔊 音频", "#43e97b")
        self._add_track("subtitle", "💬 字幕", "#fa709a")

        self._track_layout.addStretch()
        scroll.setWidget(self._track_container)
        layout.addWidget(scroll)

    def _add_track(self, track_type: str, label: str, color: str) -> TimelineTrackWidget:
        track = TimelineTrackWidget(f"track-{track_type}", track_type, label, color)
        track.clip_clicked.connect(self.clip_selected.emit)
        track.set_duration(self._duration)
        track.set_zoom(self._pps)
        self._tracks.append(track)
        self._track_layout.addWidget(track)
        return track

    def _set_zoom(self, pps: float):
        self._pps = max(2, min(pps, 100))
        self._ruler.set_params(self._duration, self._pps)
        for t in self._tracks:
            t.set_zoom(self._pps)

    def _fit_to_view(self):
        if self._duration > 0:
            available = max(self.width() - 100, 200)
            self._set_zoom(available / self._duration)

    def set_duration(self, duration: float):
        self._duration = max(duration, 1)
        self._ruler.set_params(self._duration, self._pps)
        for t in self._tracks:
            t.set_duration(self._duration)
        m, s = divmod(int(self._duration), 60)
        self.time_label.setText(f"00:00 / {m:02d}:{s:02d}")

    def load_timeline_data(self, data: Dict[str, Any]):
        """从 WorkflowEngine 的 TimelineData 加载"""
        duration = data.get("total_duration", 60)
        self.set_duration(duration)

        # 清空
        for t in self._tracks:
            t.clear_clips()

        # 视频轨
        video_track = next((t for t in self._tracks if t.track_type == "video"), None)
        for clip_data in data.get("video", data.get("video_track", [])):
            if video_track:
                video_track.add_clip(TimelineClip(
                    clip_data.get("id", ""), clip_data.get("start", 0), clip_data.get("end", 0),
                    label=clip_data.get("source", "").split("/")[-1][:15] if clip_data.get("source") else "",
                    color="#667eea", track_type="video",
                ))

        # 音频轨
        audio_track = next((t for t in self._tracks if t.track_type == "audio"), None)
        for clip_data in data.get("audio", data.get("audio_track", [])):
            if audio_track:
                audio_track.add_clip(TimelineClip(
                    clip_data.get("id", ""), clip_data.get("start", 0), clip_data.get("end", 0),
                    label="🔊", color="#43e97b", track_type="audio",
                ))

        # 字幕轨
        sub_track = next((t for t in self._tracks if t.track_type == "subtitle"), None)
        for clip_data in data.get("subtitle", data.get("subtitle_track", [])):
            if sub_track:
                sub_track.add_clip(TimelineClip(
                    clip_data.get("id", ""), clip_data.get("start", 0), clip_data.get("end", 0),
                    label=clip_data.get("text", "")[:12], color="#fa709a", track_type="subtitle",
                ))

    def set_playback_position(self, position_ms: int):
        self._playback_pos = position_ms / 1000.0
        m, s = divmod(int(self._playback_pos), 60)
        dm, ds = divmod(int(self._duration), 60)
        self.time_label.setText(f"{m:02d}:{s:02d} / {dm:02d}:{ds:02d}")
        self.position_changed.emit(self._playback_pos)

    def cleanup(self):
        for t in self._tracks:
            t.clear_clips()

    def update_theme(self, is_dark: bool = True):
        bg = "#1a1a1a" if is_dark else "#f0f0f0"
        self.setStyleSheet(f"background-color: {bg};")
