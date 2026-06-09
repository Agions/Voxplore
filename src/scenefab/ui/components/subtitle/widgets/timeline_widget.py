#!/usr/bin/env python3

"""
字幕时间线组件

管理字幕编辑时间线视图，整合轨道、时间尺和字幕块。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..subtitle_core import MultiTrackSubtitleEditor
from .subtitle_track import SubtitleTrackWidget
from .time_ruler import TimeRulerWidget


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
        editor: MultiTrackSubtitleEditor | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self._editor = editor or MultiTrackSubtitleEditor()
        self._scale = 50.0  # px/sec
        self._position = 0.0
        self._selected_block_id: str | None = None

        self._setup_ui()
        self._setup_styles()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """装配时间线 — 编排器, 委派到 _build_toolbar / _build_content_area."""
        self.setObjectName("subtitleTimelineWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_toolbar())

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)  # type: ignore[attr-defined]
        sep.setObjectName("toolbarSep")
        layout.addWidget(sep)

        layout.addWidget(self._build_content_area(), 1)

    def _build_toolbar(self) -> QFrame:
        """构建顶部工具栏: 播放/停止按钮 + 时间显示 + 缩放滑块."""
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
        self._zoom_slider = QSlider(Qt.Horizontal)  # type: ignore[attr-defined]
        self._zoom_slider.setObjectName("zoomSlider")
        self._zoom_slider.setRange(10, 200)
        self._zoom_slider.setValue(50)
        self._zoom_slider.setFixedWidth(120)
        toolbar_layout.addWidget(self._zoom_slider)

        self._zoom_label = QLabel("1.0x")
        self._zoom_label.setObjectName("zoomLabel")
        toolbar_layout.addWidget(self._zoom_label)

        return toolbar

    def _build_content_area(self) -> QScrollArea:
        """构建时间线内容区: 时间标尺 + 轨道容器, 包裹在滚动区域中."""
        scroll = QScrollArea()
        scroll.setObjectName("timelineScroll")
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # type: ignore[attr-defined]
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # type: ignore[attr-defined]

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
        return scroll

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
            if item.widget():  # type: ignore[union-attr]
                item.widget().deleteLater()  # type: ignore[union-attr]

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
            track_widget = self._tracks_layout.itemAt(i).widget()  # type: ignore[union-attr]
            if isinstance(track_widget, SubtitleTrackWidget):
                track_widget.set_scale(self._scale)

    def _on_block_changed(self, block_id: str) -> None:
        """字幕块改变"""
        self.editor_changed.emit()

    def _on_track_changed(self, track_id: str) -> None:
        """轨道改变"""
        self.editor_changed.emit()


__all__ = ["SubtitleTimelineWidget"]
