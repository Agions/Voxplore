#!/usr/bin/env python3
"""
剪辑步骤页面
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...main.pages.step_base import ContentCard, StepPage
from ...theme.ds_tokens import _C, FontSizes, Radii


class TimelinePreview(QFrame):
    """简易时间线预览"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setObjectName("timeline")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #timeline {{
                background: {_C.BG_SURFACE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.lg};
            }}
        """)

    def _setup_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 12, 16, 12)
        self._layout.setSpacing(8)

        self._setup_time_row()
        self._setup_track()
        self._setup_controls()

    def _setup_time_row(self):
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("00:00"))
        time_row.addStretch()
        time_row.addWidget(QLabel("05:32"))
        self._layout.addLayout(time_row)

    def _create_segment(self, color_start, color_end, label_text, width):
        seg = QFrame()
        seg.setStyleSheet(f"""  # type: ignore[attr-defined]
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {color_start},
                stop:1 {color_end}
            );
            border-radius: 3px;
        """)
        seg_layout = QHBoxLayout(seg)
        seg_layout.setContentsMargins(4, 0, 4, 0)
        label = QLabel(label_text)
        label.setFont(QFont("", 9))
        label.setStyleSheet("color: white;")
        seg_layout.addWidget(label)
        seg.setFixedWidth(width)
        return seg

    def _setup_track(self):
        track = QFrame()
        track.setFixedHeight(40)
        track.setStyleSheet(f"""
            background: {_C.BG_ELEVATED};
            border-radius: {Radii.sm};
        """)
        track_layout = QHBoxLayout(track)
        track_layout.setContentsMargins(4, 4, 4, 4)

        track_layout.addWidget(self._create_segment(
            _C.PRIMARY_600, _C.PRIMARY_400, "🎙️ 语音1", 180))
        track_layout.addWidget(self._create_segment(
            _C.ACCENT_600, _C.ACCENT_400, "🎬 精彩片段", 120))

        track_layout.addStretch()
        self._layout.addWidget(track)

    def _setup_controls(self):
        controls = QHBoxLayout()
        controls.addStretch()

        for icon in ["⏮", "▶", "⏭", "🔊", "⚙"]:
            btn = QPushButton(icon)
            btn.setFixedSize(32, 32)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    font-size: 16px;
                }}
                QPushButton:hover {{
                    background: {_C.BG_ELEVATED};
                    border-radius: {Radii.sm};
                }}
            """)
            controls.addWidget(btn)

        controls.addStretch()
        self._layout.addLayout(controls)


class ClipCard(QFrame):
    """剪辑片段卡片"""

    selected = Signal(str)

    def __init__(
        self,
        clip_id: str,
        icon: str,
        title: str,
        duration: str,
        clip_type: str,
        parent=None,
    ):
        super().__init__(parent)
        self._clip_id = clip_id
        self.setFixedHeight(72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("clip_card")
        self._selected = False
        self._setup_style()
        self._setup_ui(icon, title, duration, clip_type)

    def _setup_style(self):
        self.setStyleSheet(f"""  # type: ignore[attr-defined]
            #clip_card {{
                background: {_C.BG_SURFACE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.base};
            }}
            #clip_card:hover, #clip_card.selected {{
                border-color: {_C.PRIMARY_500};
            }}
        """)

    def _setup_ui(self, icon: str, title: str, duration: str, clip_type: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        icon_label = QLabel(icon)
        icon_label.setFont(QFont("", 24))
        icon_label.setFixedWidth(40)
        layout.addWidget(icon_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
        title_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        info_layout.addWidget(title_label)

        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(8)
        type_label = QLabel(clip_type)
        type_label.setFont(QFont("", FontSizes.xs))
        type_label.setStyleSheet(f"color: {_C.PRIMARY_400};")  # type: ignore[attr-defined]
        meta_layout.addWidget(type_label)

        duration_label = QLabel(duration)
        duration_label.setFont(QFont("", FontSizes.xs))
        duration_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        meta_layout.addWidget(duration_label)
        info_layout.addLayout(meta_layout)

        layout.addLayout(info_layout, 1)

        action_btn = QPushButton("✂")
        action_btn.setObjectName("action_btn")
        action_btn.setFixedSize(32, 32)
        action_btn.setStyleSheet(f"""  # type: ignore[attr-defined]
            QPushButton#action_btn {{
                background: {_C.BG_ELEVATED};
                border: none;
                border-radius: {Radii.sm};
                color: {_C.TEXT_MUTED};
                font-size: 14px;
            }}
            QPushButton#action_btn:hover {{
                color: {_C.PRIMARY_400};
            }}
        """)
        layout.addWidget(action_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self._clip_id)


class StepEditPage(StepPage):
    """剪辑步骤页 (step 2)"""

    def __init__(self, parent=None):
        super().__init__(2, parent)  # type: ignore[call-arg]

    def _build_content(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(24)

        # 预览区
        preview_label = QLabel("剪辑预览")
        preview_label.setFont(QFont("", FontSizes.md, QFont.Weight.Semibold))  # type: ignore[attr-defined]
        preview_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        layout.addWidget(preview_label)

        timeline = TimelinePreview()
        layout.addWidget(timeline)

        # 剪辑列表
        clips_label = QLabel("待处理片段")
        clips_label.setFont(QFont("", FontSizes.md, QFont.Weight.Semibold))  # type: ignore[attr-defined]
        clips_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        layout.addWidget(clips_label)

        clips_layout = QGridLayout()
        clips_layout.setSpacing(12)

        clips = [
            ("1", "🎙️", "开场白", "0:00 - 0:32", "语音"),
            ("2", "🎬", "精彩镜头A", "0:32 - 1:05", "画面"),
            ("3", "🎙️", "自我介绍", "1:05 - 2:10", "语音"),
            ("4", "✨", "高光时刻", "2:10 - 2:45", "AI识别"),
            ("5", "🎬", "精彩镜头B", "2:45 - 3:20", "画面"),
            ("6", "🎙️", "总结陈词", "3:20 - 4:00", "语音"),
        ]
        for i, (cid, icon, title, dur, ctype) in enumerate(clips):
            card = ClipCard(cid, icon, title, dur, ctype)
            row, col = i // 2, i % 2
            clips_layout.addWidget(card, row, col)

        layout.addLayout(clips_layout)

        # 字幕设置
        subtitle_card = ContentCard("字幕设置")
        sub_layout = subtitle_card.layout()

        sub_row = QHBoxLayout()
        sub_row.addWidget(QLabel("字幕样式"))
        sub_row.addStretch()

        style_combo = QComboBox()
        style_combo.addItems(["默认", "时尚", "简约", "动感"])
        style_combo.setFixedWidth(120)
        style_combo.setStyleSheet(f"""
            QComboBox {{
                background: {_C.BG_ELEVATED};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                padding: 4px 8px;
                color: {_C.TEXT_PRIMARY};
            }}
        """)
        sub_row.addWidget(style_combo)
        sub_layout.addLayout(sub_row)  # type: ignore[union-attr]

        layout.addWidget(subtitle_card)

        layout.addStretch()
        return container