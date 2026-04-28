"""
Timeline Shuttle Component
时间线穿梭器 - 解说与原片时间线对照编辑
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QSlider, QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from typing import List, Dict, Tuple

from app.services.video.models.perspective_models import (
    NarrationSegment, ClipSegment, InterleaveDecision,
    InterleaveTimeline, TransitionType
)


class TimelineRuler(QWidget):
    """
    时间线标尺
    显示时间刻度和当前位置
    """

    position_changed = Signal(float)  # 秒

    def __init__(self, parent=None):
        super().__init__(parent)
        self.duration = 0.0       # 总时长（秒）
        self.position = 0.0       # 当前播放位置
        self.scale = 50.0          # 每秒像素数
        self.markers: List[Tuple[float, str]] = []  # (时间, 标签)

        self.setMinimumHeight(30)
        self.setMaximumHeight(30)
        self.setCursor(Qt.PointingHandCursor)

    def set_duration(self, duration: float):
        self.duration = duration
        self.update()

    def set_position(self, pos: float):
        self.position = max(0, min(pos, self.duration))
        self.update()

    def set_scale(self, scale: float):
        self.scale = max(10, min(scale, 200))
        self.update()

    def add_marker(self, time: float, label: str = ""):
        self.markers.append((time, label))
        self.update()

    def clear_markers(self):
        self.markers.clear()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 背景
        painter.fillRect(self.rect(), QColor("#0D1117"))

        if self.duration <= 0:
            return

        # 计算可见范围
        px_per_sec = self.scale
        self.duration * px_per_sec

        # 绘制刻度
        painter.setPen(QPen(QColor("#334155"), 1))

        # 主要刻度（每10秒）
        for sec in range(0, int(self.duration) + 1):
            x = sec * px_per_sec
            if x > w:
                break

            if sec % 10 == 0:
                # 长刻度 + 标签
                painter.drawLine(int(x), h - 15, int(x), h)
                painter.setPen(QPen(QColor("#94A3B8"), 10, Qt.AlignCenter))
                painter.drawText(int(x) - 15, h - 18, 30, 14, Qt.AlignCenter, f"{sec}s")
                painter.setPen(QPen(QColor("#334155"), 1))
            elif sec % 5 == 0:
                # 中刻度
                painter.drawLine(int(x), h - 10, int(x), h)
            else:
                # 短刻度
                painter.drawLine(int(x), h - 6, int(x), h)

        # 绘制标记点
        painter.setBrush(QBrush(QColor("#6366F1")))
        for marker_time, label in self.markers:
            x = marker_time * px_per_sec
            if 0 <= x <= w:
                painter.drawEllipse(int(x) - 4, h - 24, 8, 8)
                if label:
                    painter.drawText(int(x) + 6, h - 20, label)

        # 当前位置指示器
        pos_x = self.position * px_per_sec
        if 0 <= pos_x <= w:
            painter.setPen(QPen(QColor("#22D3EE"), 2))
            painter.drawLine(int(pos_x), 0, int(pos_x), h)

            # 三角形指示器
            painter.setBrush(QBrush(QColor("#22D3EE")))
            [
                QPoint(int(pos_x) - 6, 0),
                QPoint(int(pos_x) + 6, 0),
                QPoint(int(pos_x), 8),
            ]
            # 简化绘制
            painter.drawPolygon([
                QPoint(int(pos_x) - 6, 0),
                QPoint(int(pos_x) + 6, 0),
                QPoint(int(pos_x), 8)
            ])

    def mousePressEvent(self, event):
        self._update_position(event.position().x())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._update_position(event.position().x())

    def _update_position(self, x: float):
        if self.duration <= 0:
            return
        pos = x / self.scale
        pos = max(0, min(pos, self.duration))
        self.position = pos
        self.position_changed.emit(pos)
        self.update()


class TimelineTrack(QWidget):
    """
    单条时间线轨道
    支持解说轨、原片轨、字幕轨
    """

    def __init__(self, name: str, track_type: str = "default", parent=None):
        super().__init__(parent)
        self.name = name
        self.track_type = track_type
        self.segments: List[Dict] = []
        self.duration = 0.0
        self.scale = 50.0
        self.height_hint = 40

        self.setMinimumHeight(self.height_hint)
        self.setMaximumHeight(self.height_hint)

    def set_segments(self, segments: List[Dict]):
        """设置轨道片段"""
        self.segments = segments
        self.update()

    def set_duration(self, duration: float):
        self.duration = duration
        self.update()

    def set_scale(self, scale: float):
        self.scale = scale
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 背景
        painter.fillRect(self.rect(), QColor("#1E293B"))

        if self.duration <= 0:
            return

        px_per_sec = self.scale

        # 绘制片段
        for seg in self.segments:
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            color = seg.get("color", "#6366F1")

            x1 = int(start * px_per_sec)
            x2 = int(end * px_per_sec)
            seg_w = max(4, x2 - x1)

            if x2 < 0 or x1 > w:
                continue

            # 片段矩形
            painter.fillRect(
                max(0, x1), 4,
                min(seg_w, w - x1),
                h - 8,
                QColor(color)
            )

            # 圆角效果
            painter.setPen(QPen(QColor(color).lighter(120), 1))
            painter.drawRoundedRect(
                max(0, x1), 4,
                min(seg_w, w - x1),
                h - 8, 4, 4
            )

            # 标签
            if seg_w > 40:
                text = seg.get("label", "")
                painter.setPen(QPen(QColor("#FFFFFF"), 1))
                painter.drawText(
                    max(0, x1) + 4, h // 2 + 4,
                    min(seg_w - 8, w - x1 - 8),
                    16, Qt.AlignLeft | Qt.AlignVCenter,
                    text[:10]
                )


class TimelineShuttle(QFrame):
    """
    时间线穿梭器 - 双轨时间线对照编辑

    功能:
    - 解说轨 + 原片轨双轨显示
    - 同步播放控制
    - 穿插预览
    - 缩放和平移
    """

    # 信号
    position_changed = Signal(float)       # 秒
    segment_clicked = Signal(str, str)      # segment_id, track_type
    playback_requested = Signal(float)       # 开始播放时间

    def __init__(self, parent=None):
        super().__init__(parent)
        self.narration_segments: List[NarrationSegment] = []
        self.original_clips: List[ClipSegment] = []
        self.decisions: List[InterleaveDecision] = []
        self.duration = 0.0
        self.position = 0.0
        self.scale = 50.0  # px/sec

        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        self.setObjectName("timelineShuttle")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部工具栏
        toolbar = QFrame()
        toolbar.setObjectName("timelineToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 6, 12, 6)

        # 播放控制
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("playBtn")
        self.play_btn.setFixedSize(36, 28)
        self.play_btn.clicked.connect(self._on_play_clicked)
        toolbar_layout.addWidget(self.play_btn)

        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setFixedSize(36, 28)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        toolbar_layout.addWidget(self.stop_btn)

        # 时间显示
        self.time_label = QLabel("00:00.0 / 00:00.0")
        self.time_label.setObjectName("timeLabel")
        toolbar_layout.addWidget(self.time_label)

        toolbar_layout.addStretch()

        # 缩放控制
        toolbar_layout.addWidget(QLabel("缩放:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setObjectName("zoomSlider")
        self.zoom_slider.setRange(10, 200)
        self.zoom_slider.setValue(50)
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        toolbar_layout.addWidget(self.zoom_slider)

        # 缩放值显示
        self.zoom_label = QLabel("1x")
        self.zoom_label.setObjectName("zoomLabel")
        toolbar_layout.addWidget(self.zoom_label)

        layout.addWidget(toolbar)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("toolbarSep")
        layout.addWidget(sep)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setObjectName("timelineScroll")
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 时间线容器
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # 标尺
        self.ruler = TimelineRuler()
        self.ruler.position_changed.connect(self._on_position_changed)
        container_layout.addWidget(self.ruler)

        # 轨道区域
        tracks_container = QWidget()
        tracks_layout = QVBoxLayout(tracks_container)
        tracks_layout.setContentsMargins(0, 8, 0, 8)
        tracks_layout.setSpacing(8)

        # 解说轨
        narration_track_frame = QFrame()
        narration_track_frame.setObjectName("trackFrame")
        narration_layout = QHBoxLayout(narration_track_frame)
        narration_layout.setContentsMargins(12, 0, 12, 0)

        narration_label = QLabel("解说")
        narration_label.setFixedWidth(60)
        narration_label.setObjectName("trackLabel")
        narration_layout.addWidget(narration_label)

        self.narration_track = TimelineTrack("解说", "narration")
        narration_layout.addWidget(self.narration_track, 1)

        tracks_layout.addWidget(narration_track_frame)

        # 原片轨
        original_track_frame = QFrame()
        original_track_frame.setObjectName("trackFrame")
        original_layout = QHBoxLayout(original_track_frame)
        original_layout.setContentsMargins(12, 0, 12, 0)

        original_label = QLabel("原片")
        original_label.setFixedWidth(60)
        original_label.setObjectName("trackLabel")
        original_layout.addWidget(original_label)

        self.original_track = TimelineTrack("原片", "original")
        original_layout.addWidget(self.original_track, 1)

        tracks_layout.addWidget(original_track_frame)

        container_layout.addWidget(tracks_container)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

    def _apply_theme(self):
        self.setStyleSheet("""
            QFrame#timelineShuttle {
                background-color: #090D14;
                border: 1px solid #1E293B;
                border-radius: 8px;
            }
            QFrame#trackFrame {
                background-color: transparent;
            }
            QLabel#trackLabel {
                color: #94A3B8;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#playBtn, QPushButton#stopBtn {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 4px;
                color: #F1F5F9;
                font-size: 14px;
            }
            QPushButton#playBtn:hover, QPushButton#stopBtn:hover {
                background-color: #334155;
            }
            QLabel#timeLabel {
                color: #F1F5F9;
                font-family: monospace;
                font-size: 13px;
            }
            QLabel#zoomLabel {
                color: #94A3B8;
                font-size: 12px;
                min-width: 30px;
            }
        """)

    # ─────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────

    def set_timeline(self, timeline: InterleaveTimeline) -> None:
        """设置完整时间线"""
        self.decisions = timeline.decisions
        self.duration = timeline.total_duration

        # 更新标尺
        self.ruler.set_duration(self.duration)

        # 构建解说轨数据
        narration_segs = []
        for d in timeline.decisions:
            ns = d.narration_segment
            narration_segs.append({
                "start": ns.start_time,
                "end": ns.end_time,
                "label": ns.text[:15],
                "color": "#6366F1",
            })

        self.narration_track.set_segments(narration_segs)
        self.narration_track.set_duration(self.duration)
        self.narration_track.set_scale(self.scale)

        # 构建原片轨数据
        original_segs = []
        for d in timeline.decisions:
            if d.show_original and d.clip_segment:
                cs = d.clip_segment
                # 转场颜色
                color = {
                    TransitionType.CUT: "#334155",
                    TransitionType.FADE: "#6366F1",
                    TransitionType.DISSOLVE: "#8B5CF6",
                    TransitionType.ZOOM_HIGHLIGHT: "#22D3EE",
                }.get(d.transition, "#334155")

                original_segs.append({
                    "start": d.original_start or cs.start_time,
                    "end": d.original_end or cs.end_time,
                    "label": "原片",
                    "color": color,
                })

        self.original_track.set_segments(original_segs)
        self.original_track.set_duration(self.duration)
        self.original_track.set_scale(self.scale)

        # 更新容器宽度
        container = self.findChild(QWidget, "timelineScroll").widget()
        if container:
            container.setMinimumWidth(int(self.duration * self.scale) + 100)

        self._update_time_label()

    def set_narration_segments(self, segments: List[NarrationSegment]) -> None:
        """设置解说片段"""
        self.narration_segments = segments
        self.duration = max(d.end_time for (d) in segments) if segments else 0

        self.ruler.set_duration(self.duration)

        narration_segs = [{
            "start": s.start_time,
            "end": s.end_time,
            "label": s.text[:15],
            "color": "#6366F1",
        } for s in segments]

        self.narration_track.set_segments(narration_segs)
        self.narration_track.set_duration(self.duration)
        self.narration_track.set_scale(self.scale)

    def set_original_clips(self, clips: List[ClipSegment]) -> None:
        """设置原片片段"""
        self.original_clips = clips

        original_segs = [{
            "start": c.start_time,
            "end": c.end_time,
            "label": "原片",
            "color": "#334155",
        } for c in clips]

        self.original_track.set_segments(original_segs)
        self.original_track.set_duration(self.duration)
        self.original_track.set_scale(self.scale)

    def set_position(self, pos: float) -> None:
        """设置播放位置"""
        self.position = pos
        self.ruler.set_position(pos)
        self._update_time_label()

    def clear(self) -> None:
        """清空时间线"""
        self.narration_segments.clear()
        self.original_clips.clear()
        self.decisions.clear()
        self.duration = 0.0
        self.position = 0.0
        self.ruler.set_duration(0)
        self.narration_track.set_segments([])
        self.original_track.set_segments([])
        self._update_time_label()

    # ─────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────

    def _on_play_clicked(self):
        self.playback_requested.emit(self.position)

    def _on_stop_clicked(self):
        self.position = 0.0
        self.ruler.set_position(0.0)
        self._update_time_label()
        self.position_changed.emit(0.0)

    def _on_position_changed(self, pos: float):
        self.position = pos
        self._update_time_label()
        self.position_changed.emit(pos)

    def _on_zoom_changed(self, value: int):
        self.scale = float(value)
        self.zoom_label.setText(f"{value/50:.1f}x")

        self.ruler.set_scale(self.scale)
        self.narration_track.set_scale(self.scale)
        self.original_track.set_scale(self.scale)

    def _update_time_label(self):
        m, s = divmod(int(self.position), 60)
        ms = int((self.position % 1) * 10)
        pos_str = f"{m:02d}:{s:02d}.{ms}"

        m2, s2 = divmod(int(self.duration), 60)
        dur_str = f"{m2:02d}:{s2:02d}"

        self.time_label.setText(f"{pos_str} / {dur_str}")
