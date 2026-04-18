#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Subtitle Track Widget
字幕轨道编辑组件 - 多轨道字幕时间线编辑器组件

功能:
- 多轨道字幕显示与编辑
- 时间线标尺
- 字幕块拖拽、调整大小
- 轨道增删管理
- 缩放和平移
"""

from typing import List, Optional, Dict, Any, Tuple
import math

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QSlider, QScrollArea, QToolTip,
    QAbstractItemView, QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, Signal, Slot, QRect, QPoint, QSize
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QLinearGradient, 
    QPainterPath, QMouseEvent, QPalette, QFont
)

from .subsubtitles import (
    SubtitleTrack, SubtitleBlock, MultiTrackSubtitleEditor,
    SubtitleStylePreset, SubtitlePosition, SubtitleAnimation,
)


class TimeRulerWidget(QWidget):
    """
    时间标尺组件
    
    显示时间刻度和当前位置。
    
    Signals:
        position_changed(float): 位置改变信号（秒）
    """
    
    position_changed = Signal(float)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._duration: float = 0.0
        self._position: float = 0.0
        self._scale: float = 50.0  # px/sec
        self._markers: List[Tuple[float, str]] = []
        
        self.setMinimumHeight(30)
        self.setMaximumHeight(30)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
    
    def set_duration(self, duration: float) -> None:
        """设置总时长（秒）"""
        self._duration = duration
        self.update()
    
    def set_position(self, pos: float) -> None:
        """设置当前播放位置"""
        self._position = max(0, min(pos, self._duration)) if self._duration > 0 else 0
        self.update()
    
    def set_scale(self, scale: float) -> None:
        """设置缩放比例"""
        self._scale = max(10, min(scale, 200))
        self.update()
    
    def add_marker(self, time: float, label: str = "") -> None:
        """添加标记点"""
        self._markers.append((time, label))
        self.update()
    
    def clear_markers(self) -> None:
        """清空标记点"""
        self._markers.clear()
        self.update()
    
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # 背景
        painter.fillRect(self.rect(), QColor("#0D1117"))
        
        if self._duration <= 0:
            return
        
        # 绘制刻度
        painter.setPen(QPen(QColor("#334155"), 1))
        
        # 计算主刻度间隔
        sec_per_mark = 1
        if self._scale < 20:
            sec_per_mark = 10
        elif self._scale < 40:
            sec_per_mark = 5
        
        # 绘制刻度
        for sec in range(0, int(self._duration) + 1):
            x = sec * self._scale
            if x > w:
                break
            
            if sec % sec_per_mark == 0:
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
        for marker_time, label in self._markers:
            x = marker_time * self._scale
            if 0 <= x <= w:
                painter.drawEllipse(int(x) - 4, h - 24, 8, 8)
                if label:
                    painter.drawText(int(x) + 6, h - 20, label)
        
        # 当前位置指示器
        pos_x = self._position * self._scale
        if 0 <= pos_x <= w:
            painter.setPen(QPen(QColor("#22D3EE"), 2))
            painter.drawLine(int(pos_x), 0, int(pos_x), h)
            
            # 三角形指示器
            painter.setBrush(QBrush(QColor("#22D3EE")))
            painter.drawPolygon([
                QPoint(int(pos_x) - 6, 0),
                QPoint(int(pos_x) + 6, 0),
                QPoint(int(pos_x), 8)
            ])
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._update_position(event.position().x())
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.LeftButton:
            self._update_position(event.position().x())
    
    def _update_position(self, x: float) -> None:
        if self._duration <= 0:
            return
        pos = x / self._scale
        pos = max(0, min(pos, self._duration))
        self._position = pos
        self.position_changed.emit(pos)
        self.update()


class SubtitleBlockWidget(QWidget):
    """
    字幕块编辑组件
    
    显示单个字幕块，支持拖拽和调整大小。
    
    Signals:
        block_changed(str block_id): 字幕块改变信号
        block_selected(str block_id): 字幕块选中信号
    """
    
    block_changed = Signal(str)
    block_selected = Signal(str)
    
    def __init__(
        self,
        block: SubtitleBlock,
        style: SubtitleStylePreset,
        scale: float = 50.0,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self._block = block
        self._style = style
        self._scale = scale
        self._is_selected = False
        self._is_dragging = False
        self._is_resizing = False
        self._drag_start_x = 0
        self._original_start = 0.0
        self._original_end = 0.0
        
        self.setMinimumHeight(36)
        self.setCursor(Qt.SizeHorCursor)
        self.setMouseTracking(True)
    
    def set_scale(self, scale: float) -> None:
        """设置缩放比例"""
        self._scale = scale
        self.update()
    
    def set_selected(self, selected: bool) -> None:
        """设置选中状态"""
        self._is_selected = selected
        self.update()
    
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # 颜色
        bg_color = QColor(self._style.font_color)
        bg_color.setAlpha(40)
        
        border_color = QColor("#6366F1") if self._is_selected else QColor("#475569")
        
        # 背景
        painter.fillRect(self.rect(), bg_color)
        
        # 边框
        painter.setPen(QPen(border_color, 2 if self._is_selected else 1))
        painter.drawRoundedRect(0, 2, w - 1, h - 4, 4, 4)
        
        # 左侧调整手柄
        painter.setPen(QPen(QColor("#6366F1"), 3))
        painter.drawLine(4, 8, 4, h - 8)
        
        # 右侧调整手柄
        painter.drawLine(w - 4, 8, w - 4, h - 8)
        
        # 文本
        text = self._block.text
        if len(text) > 20:
            text = text[:20] + "..."
        
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QPen(QColor(self._style.font_color), 1))
        painter.drawText(8, h // 2 + 4, text)
        
        # 时间显示
        time_str = f"{self._block.start_time:.1f}s - {self._block.end_time:.1f}s"
        painter.setPen(QPen(QColor("#94A3B8"), 1))
        painter.drawText(w - 80, h // 2 + 4, time_str)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_start_x = event.position().x()
            self._original_start = self._block.start_time
            self._original_end = self._block.end_time
            self.block_selected.emit(self._block.id)
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging:
            delta_x = event.position().x() - self._drag_start_x
            delta_time = delta_x / self._scale
            
            new_start = self._original_start + delta_time
            new_end = self._original_end + delta_time
            
            if new_start >= 0 and new_end > new_start:
                self._block.start_time = new_start
                self._block.end_time = new_end
                self.block_changed.emit(self._block.id)
                self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._is_dragging = False


class SubtitleTrackWidget(QFrame):
    """
    字幕轨道编辑组件
    
    显示和管理单个字幕轨道。
    
    Signals:
        block_selected(str block_id): 字幕块选中信号
        block_changed(str block_id): 字幕块改变信号
        track_changed(str track_id): 轨道改变信号
    """
    
    block_selected = Signal(str)
    block_changed = Signal(str)
    track_changed = Signal(str)
    
    def __init__(
        self,
        track: SubtitleTrack,
        style: SubtitleStylePreset,
        scale: float = 50.0,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self._track = track
        self._style = style
        self._scale = scale
        self._selected_block_id: Optional[str] = None
        
        self._setup_ui()
        self._setup_styles()
    
    def _setup_ui(self) -> None:
        """设置UI"""
        self.setObjectName("subtitleTrackWidget")
        self.setMinimumHeight(50)
        self.setMaximumHeight(80)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(60, 4, 12, 4)
        layout.setSpacing(0)
        
        # 轨道标签
        label = QLabel(self._track.name)
        label.setObjectName("trackLabel")
        label.setFixedWidth(56)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        # 轨道内容区（需要scroll area）
        self._blocks_container = QWidget()
        self._blocks_layout = QVBoxLayout(self._blocks_container)
        self._blocks_layout.setContentsMargins(0, 0, 0, 0)
        self._blocks_layout.setSpacing(2)
        
        self._update_blocks()
    
    def _setup_styles(self) -> None:
        """设置样式"""
        self.setStyleSheet("""
            QFrame#subtitleTrackWidget {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
            }
            QLabel#trackLabel {
                color: #94A3B8;
                font-size: 11px;
                font-weight: 600;
                background-color: #0F172A;
                border-radius: 4px;
                padding: 4px;
            }
        """)
    
    def set_scale(self, scale: float) -> None:
        """设置缩放比例"""
        self._scale = scale
        self._update_blocks()
    
    def set_selected_block(self, block_id: Optional[str]) -> None:
        """设置选中的字幕块"""
        self._selected_block_id = block_id
        self._update_blocks()
    
    def _update_blocks(self) -> None:
        """更新字幕块显示"""
        # 清除现有块
        while self._blocks_layout.count():
            item = self._blocks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 添加字幕块
        for block in sorted(self._track.blocks, key=lambda b: b.start_time):
            block_widget = SubtitleBlockWidget(block, self._style, self._scale)
            block_widget.set_selected(block.id == self._selected_block_id)
            block_widget.block_selected.connect(self.block_selected.emit)
            block_widget.block_changed.connect(self._on_block_changed)
            self._blocks_layout.addWidget(block_widget)
    
    def _on_block_changed(self, block_id: str) -> None:
        """字幕块改变处理"""
        self.block_changed.emit(block_id)
        self.track_changed.emit(self._track.id)


class SubtitleTimelineWidget(QFrame):
    """
    字幕时间线编辑器主组件
    
    功能:
    - 多轨道字幕编辑
    - 时间线标尺
    - 播放控制
    - 缩放和平移
    - 轨道增删管理
    
    Signals:
        position_changed(float): 位置改变信号
        block_selected(str block_id): 字幕块选中信号
        editor_changed(): 编辑器改变信号
    """
    
    position_changed = Signal(float)
    block_selected = Signal(str)
    editor_changed = Signal()
    
    def __init__(
        self,
        editor: Optional[MultiTrackSubtitleEditor] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        
        self._editor = editor or MultiTrackSubtitleEditor()
        self._scale = 50.0  # px/sec
        self._position = 0.0
        self._selected_block_id: Optional[str] = None
        
        self._setup_ui()
        self._setup_styles()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """设置UI"""
        self.setObjectName("subtitleTimelineWidget")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 工具栏
        toolbar = QFrame()
        toolbar.setObjectName("timelineToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 6, 12, 6)
        
        # 播放控制
        self._play_btn = QPushButton("▶")
        self._play_btn.setObjectName("playBtn")
        self._play_btn.setFixedSize(36, 28)
        toolbar_layout.addWidget(self._play_btn)
        
        self._stop_btn = QPushButton("⏹")
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setFixedSize(36, 28)
        toolbar_layout.addWidget(self._stop_btn)
        
        # 时间显示
        self._time_label = QLabel("00:00.0 / 00:00.0")
        self._time_label.setObjectName("timeLabel")
        toolbar_layout.addWidget(self._time_label)
        
        toolbar_layout.addStretch()
        
        # 缩放控制
        toolbar_layout.addWidget(QLabel("缩放:"))
        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setObjectName("zoomSlider")
        self._zoom_slider.setRange(10, 200)
        self._zoom_slider.setValue(50)
        self._zoom_slider.setFixedWidth(120)
        toolbar_layout.addWidget(self._zoom_slider)
        
        self._zoom_label = QLabel("1.0x")
        self._zoom_label.setObjectName("zoomLabel")
        toolbar_layout.addWidget(self._zoom_label)
        
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
        
        # 时间标尺
        self._ruler = TimeRulerWidget()
        self._ruler.position_changed.connect(self._on_position_changed)
        container_layout.addWidget(self._ruler)
        
        # 轨道容器
        self._tracks_container = QWidget()
        self._tracks_layout = QVBoxLayout(self._tracks_container)
        self._tracks_layout.setContentsMargins(0, 8, 0, 8)
        self._tracks_layout.setSpacing(8)
        
        container_layout.addWidget(self._tracks_container)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
    
    def _setup_styles(self) -> None:
        """设置样式"""
        self.setStyleSheet("""
            QFrame#subtitleTimelineWidget {
                background-color: #090D14;
                border: 1px solid #1E293B;
                border-radius: 8px;
            }
            QFrame#timelineToolbar {
                background-color: #0D1117;
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
    
    def _connect_signals(self) -> None:
        """连接信号"""
        self._play_btn.clicked.connect(self._on_play_clicked)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        self._zoom_slider.valueChanged.connect(self._on_zoom_changed)
    
    # ─────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────
    
    def set_editor(self, editor: MultiTrackSubtitleEditor) -> None:
        """设置编辑器"""
        self._editor = editor
        self._update_tracks()
        self._update_duration()
    
    def set_position(self, pos: float) -> None:
        """设置播放位置"""
        self._position = pos
        self._ruler.set_position(pos)
        self._update_time_label()
    
    def get_editor(self) -> MultiTrackSubtitleEditor:
        """获取编辑器"""
        return self._editor
    
    def _update_tracks(self) -> None:
        """更新轨道显示"""
        # 清除现有轨道
        while self._tracks_layout.count():
            item = self._tracks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 添加轨道
        for track in self._editor.tracks:
            style = self._editor.get_style_for_track(track)
            track_widget = SubtitleTrackWidget(track, style, self._scale)
            track_widget.block_selected.connect(self.block_selected.emit)
            track_widget.block_changed.connect(self._on_block_changed)
            track_widget.track_changed.connect(self._on_track_changed)
            self._tracks_layout.addWidget(track_widget)
    
    def _update_duration(self) -> None:
        """更新时长"""
        duration = self._editor.calculate_duration()
        self._ruler.set_duration(duration)
        self._update_time_label()
    
    def _update_time_label(self) -> None:
        """更新时间标签"""
        m, s = divmod(int(self._position), 60)
        ms = int((self._position % 1) * 10)
        pos_str = f"{m:02d}:{s:02d}.{ms}"
        
        duration = self._editor.duration
        m2, s2 = divmod(int(duration), 60)
        dur_str = f"{m2:02d}:{s2:02d}"
        
        self._time_label.setText(f"{pos_str} / {dur_str}")
    
    # ─────────────────────────────────────────────────────────────
    # Event Handlers
    # ─────────────────────────────────────────────────────────────
    
    def _on_play_clicked(self) -> None:
        """播放按钮点击"""
        self.position_changed.emit(self._position)
    
    def _on_stop_clicked(self) -> None:
        """停止按钮点击"""
        self._position = 0.0
        self._ruler.set_position(0.0)
        self._update_time_label()
        self.position_changed.emit(0.0)
    
    def _on_position_changed(self, pos: float) -> None:
        """位置改变"""
        self._position = pos
        self._update_time_label()
        self.position_changed.emit(pos)
    
    def _on_zoom_changed(self, value: int) -> None:
        """缩放改变"""
        self._scale = float(value)
        self._zoom_label.setText(f"{value / 50:.1f}x")
        
        self._ruler.set_scale(self._scale)
        
        # 更新所有轨道
        for i in range(self._tracks_layout.count()):
            track_widget = self._tracks_layout.itemAt(i).widget()
            if isinstance(track_widget, SubtitleTrackWidget):
                track_widget.set_scale(self._scale)
    
    def _on_block_changed(self, block_id: str) -> None:
        """字幕块改变"""
        self.editor_changed.emit()
    
    def _on_track_changed(self, track_id: str) -> None:
        """轨道改变"""
        self.editor_changed.emit()


__all__ = [
    "TimeRulerWidget",
    "SubtitleBlockWidget",
    "SubtitleTrackWidget",
    "SubtitleTimelineWidget",
]
