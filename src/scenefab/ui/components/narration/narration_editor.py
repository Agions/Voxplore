"""
Narration Editor Component
解说编辑器组件 - 所见即所得的解说稿编辑
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
)

from scenefab.services.video.models.perspective import NarrationSegment


class NarrationSegmentItem(QFrame):
    """
    单个解说片段的卡片组件
    显示：时间、文本预览、情感标签、操作按钮
    """

    clicked = Signal(str)  # segment_id
    edit_requested = Signal(str)  # segment_id
    delete_requested = Signal(str)  # segment_id

    EMOTION_COLORS = {
        "healing": "#10B981",  # 治愈 - 翠绿
        "suspense": "#8B5CF6",  # 悬疑 - 紫色
        "motivational": "#F59E0B",  # 励志 - 琥珀
        "nostalgic": "#6366F1",  # 怀旧 - 靛蓝
        "romantic": "#EC4899",  # 浪漫 - 粉色
    }

    def __init__(self, segment: NarrationSegment, parent=None):
        super().__init__(parent)
        self.segment = segment
        self.segment_id = segment.segment_id
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        """装配卡片 — 编排器, 委派到 _build_time_col / _build_text_col / _build_btn_col."""
        self.setObjectName("narrationSegmentCard")
        self.setFixedHeight(90)
        self.setCursor(Qt.PointingHandCursor)  # type: ignore[attr-defined]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        layout.addWidget(self._build_time_label())
        layout.addWidget(self._build_separator())
        layout.addLayout(self._build_text_column(), 1)
        layout.addLayout(self._build_action_column())

        # 应用情感颜色
        self._apply_emotion_badge_style()

    def _build_time_label(self) -> QLabel:
        """构建左侧时间戳标签."""
        time_label = QLabel(self._format_time(self.segment.start_time))
        time_label.setObjectName("timeLabel")
        time_label.setFixedWidth(70)
        return time_label

    @staticmethod
    def _build_separator() -> QFrame:
        """构建垂直分隔线."""
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)  # type: ignore[attr-defined]
        sep.setObjectName("separator")
        return sep

    def _build_text_column(self) -> QVBoxLayout:
        """构建文本列: 预览 + 情感/时长标签."""
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        self.text_preview = QLabel(self._truncate(self.segment.text, 80))
        self.text_preview.setObjectName("textPreview")
        self.text_preview.setWordWrap(True)
        text_layout.addWidget(self.text_preview)

        tag_layout = QHBoxLayout()
        tag_layout.setSpacing(6)

        self.emotion_badge = QLabel(self.segment.emotion)
        self.emotion_badge.setObjectName("emotionBadge")
        self.emotion_badge.setFixedHeight(20)
        self.emotion_badge.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        tag_layout.addWidget(self.emotion_badge)

        duration_label = QLabel(f"{self.segment.duration:.1f}s")
        duration_label.setObjectName("durationLabel")
        duration_label.setFixedHeight(20)
        tag_layout.addWidget(duration_label)

        tag_layout.addStretch()
        text_layout.addLayout(tag_layout)
        return text_layout

    def _build_action_column(self) -> QVBoxLayout:
        """构建操作列: 编辑/删除按钮."""
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)

        edit_btn = QPushButton("编辑")
        edit_btn.setObjectName("editBtn")
        edit_btn.setFixedSize(50, 24)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.segment_id))
        btn_layout.addWidget(edit_btn)

        del_btn = QPushButton("删除")
        del_btn.setObjectName("deleteBtn")
        del_btn.setFixedSize(50, 24)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.segment_id))
        btn_layout.addWidget(del_btn)

        return btn_layout

    def _apply_emotion_badge_style(self) -> None:
        """应用情感颜色到 emotion_badge."""
        color = self.EMOTION_COLORS.get(self.segment.emotion, "#6366F1")
        self.emotion_badge.setStyleSheet(f"""
            background-color: #1f2c43;
            color: {color};
            border: 1px solid {color};
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            padding: 0 6px;
        """)

    def _load_data(self):
        if self._segment:  # type: ignore[attr-defined]
            self._text_editor.setPlainText(self._segment.text or "")  # type: ignore[attr-defined]

    def _format_time(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    def _truncate(self, text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:  # type: ignore[attr-defined]
            self.clicked.emit(self.segment_id)
        super().mousePressEvent(event)

    def update_segment(self, segment: NarrationSegment):
        """更新片段数据"""
        self.segment = segment
        self.text_preview.setText(self._truncate(segment.text, 80))

        color = self.EMOTION_COLORS.get(segment.emotion, "#6366F1")
        self.emotion_badge.setText(segment.emotion)
        self.emotion_badge.setStyleSheet(f"""
            background-color: #1f2c43;
            color: {color};
            border: 1px solid {color};
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            padding: 0 6px;
        """)


class NarrationEditor(QFrame):
    """
    解说编辑器主组件

    功能:
    - 片段列表展示
    - 编辑解说文本
    - 调节情感风格
    - 实时预览
    - 批量操作
    """

    # 信号
    segment_selected = Signal(str)  # segment_id
    segment_updated = Signal(str, dict)  # segment_id, changes
    segment_deleted = Signal(str)  # segment_id
    emotion_changed = Signal(str, str)  # segment_id, emotion
    playback_requested = Signal(str)  # segment_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments: dict[str, NarrationSegment] = {}
        self.selected_id: str | None = None
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("narrationEditor")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self._create_toolbar())

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)  # type: ignore[attr-defined]
        sep.setObjectName("toolbarSep")
        main_layout.addWidget(sep)

        self._setup_segment_list(main_layout)
        main_layout.addWidget(self._create_editor_panel())

    def _create_toolbar(self) -> QFrame:
        toolbar = QFrame()
        toolbar.setObjectName("editorToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)

        title = QLabel("解说稿")
        title.setObjectName("editorTitle")
        toolbar_layout.addWidget(title)

        toolbar_layout.addStretch()

        self.emotion_filter = QComboBox()
        self.emotion_filter.addItems(["全部", "治愈", "悬疑", "励志", "怀旧", "浪漫"])
        self.emotion_filter.setFixedWidth(100)
        self.emotion_filter.currentTextChanged.connect(self._on_filter_changed)
        toolbar_layout.addWidget(QLabel("筛选:"))
        toolbar_layout.addWidget(self.emotion_filter)

        self.total_duration = QLabel("00:00")
        self.total_duration.setObjectName("totalDuration")
        toolbar_layout.addWidget(QLabel("总时长:"))
        toolbar_layout.addWidget(self.total_duration)

        return toolbar

    def _setup_segment_list(self, parent_layout: QVBoxLayout) -> None:
        self.segment_list = QListWidget()
        self.segment_list.setObjectName("segmentList")
        self.segment_list.itemClicked.connect(self._on_item_clicked)
        self.segment_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        parent_layout.addWidget(self.segment_list, 1)

    def _create_editor_panel(self) -> QFrame:
        self.editor_panel = QFrame()
        self.editor_panel.setObjectName("editorPanel")
        self.editor_panel.setVisible(False)
        editor_layout = QVBoxLayout(self.editor_panel)
        editor_layout.setContentsMargins(12, 12, 12, 12)
        editor_layout.setSpacing(8)

        self._setup_editor_header(editor_layout)
        self._setup_text_edit(editor_layout)
        self._setup_emotion_controls(editor_layout)

        return self.editor_panel

    def _setup_editor_header(self, editor_layout: QVBoxLayout) -> None:
        editor_header = QHBoxLayout()
        editor_header.addWidget(QLabel("编辑解说"))
        editor_header.addStretch()

        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.clicked.connect(self._on_save)
        editor_header.addWidget(self.save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self._on_cancel_edit)
        editor_header.addWidget(cancel_btn)

        editor_layout.addLayout(editor_header)

    def _setup_text_edit(self, editor_layout: QVBoxLayout) -> None:
        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("narrationTextEdit")
        self.text_edit.setPlaceholderText("在此输入解说文本...")
        self.text_edit.setMinimumHeight(100)
        editor_layout.addWidget(self.text_edit)

    def _setup_emotion_controls(self, editor_layout: QVBoxLayout) -> None:
        emotion_row = QHBoxLayout()
        emotion_row.addWidget(QLabel("情感风格:"))

        self.emotion_combo = QComboBox()
        self.emotion_combo.addItems(
            ["healing", "suspense", "motivational", "nostalgic", "romantic"]
        )
        emotion_row.addWidget(self.emotion_combo)

        emotion_row.addStretch()

        self.emotion_intensity = QSlider(Qt.Horizontal)  # type: ignore[attr-defined]
        self.emotion_intensity.setObjectName("emotionIntensity")
        self.emotion_intensity.setRange(0, 100)
        self.emotion_intensity.setValue(50)
        self.emotion_intensity.setFixedWidth(120)
        emotion_row.addWidget(QLabel("强度:"))
        emotion_row.addWidget(self.emotion_intensity)

        editor_layout.addLayout(emotion_row)

    # ─────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────

    def set_segments(self, segments: list[NarrationSegment]) -> None:
        """设置解说片段列表"""
        self.segments = {s.segment_id: s for s in segments}
        self._refresh_list()

    def add_segment(self, segment: NarrationSegment) -> None:
        """添加片段"""
        self.segments[segment.segment_id] = segment
        self._refresh_list()

    def remove_segment(self, segment_id: str) -> None:
        """移除片段"""
        if segment_id in self.segments:
            del self.segments[segment_id]
            if self.selected_id == segment_id:
                self.selected_id = None
                self.editor_panel.setVisible(False)
            self._refresh_list()

    def get_segment(self, segment_id: str) -> NarrationSegment | None:
        """获取片段"""
        return self.segments.get(segment_id)

    def clear(self) -> None:
        """清空所有片段"""
        self.segments.clear()
        self.selected_id = None
        self.editor_panel.setVisible(False)
        self._refresh_list()

    # ─────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────

    def _refresh_list(self):
        """刷新列表"""
        self.segment_list.clear()

        filter_text = self.emotion_filter.currentText()
        filter_map = {
            "全部": None,
            "治愈": "healing",
            "悬疑": "suspense",
            "励志": "motivational",
            "怀旧": "nostalgic",
            "浪漫": "romantic",
        }
        filter_emotion = filter_map.get(filter_text)

        for segment in sorted(self.segments.values(), key=lambda s: s.start_time):
            if filter_emotion and segment.emotion != filter_emotion:
                continue

            item = QListWidgetItem()
            item.setData(Qt.UserRole, segment.segment_id)  # type: ignore[attr-defined]

            widget = NarrationSegmentItem(segment)
            widget.clicked.connect(self._on_segment_clicked)
            widget.edit_requested.connect(self._on_edit_requested)
            widget.delete_requested.connect(self._on_delete_requested)

            item.setSizeHint(widget.sizeHint())
            self.segment_list.addItem(item)
            self.segment_list.setItemWidget(item, widget)

        # 更新总时长
        total = sum(s.duration for s in self.segments.values())
        m, s = divmod(int(total), 60)
        self.total_duration.setText(f"{m:02d}:{s:02d}")

    def _on_segment_clicked(self, segment_id: str):
        self._select_segment(segment_id)

    def _on_item_clicked(self, item):
        segment_id = item.data(Qt.UserRole)  # type: ignore[attr-defined]
        self._select_segment(segment_id)

    def _on_item_double_clicked(self, item):
        segment_id = item.data(Qt.UserRole)  # type: ignore[attr-defined]
        self._open_editor(segment_id)

    def _on_edit_requested(self, segment_id: str):
        self._open_editor(segment_id)

    def _on_delete_requested(self, segment_id: str):
        self.remove_segment(segment_id)
        self.segment_deleted.emit(segment_id)

    def _select_segment(self, segment_id: str):
        """选中片段"""
        self.selected_id = segment_id
        self.segment_selected.emit(segment_id)

        # 更新列表中的选中状态
        for i in range(self.segment_list.count()):
            item = self.segment_list.item(i)
            widget = self.segment_list.itemWidget(item)
            if item.data(Qt.UserRole) == segment_id:  # type: ignore[attr-defined]
                widget.setStyleSheet("""
                    QFrame#narrationSegmentCard {
                        border: 1px solid #6366F1;
                        border-radius: 8px;
                        background-color: #1E1B4B;
                    }
                """)
            else:
                widget.setStyleSheet("")

    def _open_editor(self, segment_id: str):
        """打开编辑器"""
        segment = self.segments.get(segment_id)
        if not segment:
            return

        self.selected_id = segment_id
        self.editor_panel.setVisible(True)
        self.text_edit.setPlainText(segment.text)

        idx = self.emotion_combo.findText(segment.emotion)
        if idx >= 0:
            self.emotion_combo.setCurrentIndex(idx)

    def _on_filter_changed(self, text: str):
        self._refresh_list()

    def _on_save(self):
        """保存编辑"""
        if not self.selected_id:
            return

        new_text = self.text_edit.toPlainText()
        new_emotion = self.emotion_combo.currentText()

        segment = self.segments.get(self.selected_id)
        if segment:
            segment.text = new_text
            segment.emotion = new_emotion

            self.segment_updated.emit(
                self.selected_id,
                {
                    "text": new_text,
                    "emotion": new_emotion,
                },
            )

            self._refresh_list()
            self.editor_panel.setVisible(False)

    def _on_cancel_edit(self):
        """取消编辑"""
        self.selected_id = None
        self.editor_panel.setVisible(False)
        self._refresh_list()
