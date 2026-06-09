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
from ...theme.ds_tokens import Colors, FontSizes, Radii


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
                background: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: {Radii.lg};
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # 时间标签
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("00:00"))
        time_row.addStretch()
        time_row.addWidget(QLabel("05:32"))
        layout.addLayout(time_row)

        # 时间线轨道
        track = QFrame()
        track.setFixedHeight(40)
        track.setStyleSheet(f"""
            background: {Colors.BG_ELEVATED};
            border-radius: {Radii.sm};
        """)
        track_layout = QHBoxLayout(track)
        track_layout.setContentsMargins(4, 4, 4, 4)

        # 片段1
        seg1 = QFrame()
        seg1.setStyleSheet(f"""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {Colors.PRIMARY_600},
                stop:1 {Colors.PRIMARY_400}
            );
            border-radius: 3px;
        """)
        seg1_layout = QHBoxLayout(seg1)
        seg1_layout.setContentsMargins(4, 0, 4, 0)
        label1 = QLabel("🎙️ 语音1")
        label1.setFont(QFont("", 9))
        label1.setStyleSheet("color: white;")
        seg1_layout.addWidget(label1)
        seg1.setFixedWidth(180)
        track_layout.addWidget(seg1)

        # 片段2
        seg2 = QFrame()
        seg2.setStyleSheet(f"""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {Colors.ACCENT_600},
                stop:1 {Colors.ACCENT_400}
            );
            border-radius: 3px;
        """)
        seg2_layout = QHBoxLayout(seg2)
        seg2_layout.setContentsMargins(4, 0, 4, 0)
        label2 = QLabel("🎬 精彩片段")
        label2.setFont(QFont("", 9))
        label2.setStyleSheet("color: white;")
        seg2_layout.addWidget(label2)
        seg2.setFixedWidth(120)
        track_layout.addWidget(seg2)

        track_layout.addStretch()
        layout.addWidget(track)

        # 播放控制
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
                    background: {Colors.BG_ELEVATED};
                    border-radius: {Radii.sm};
                }}
            """)
            controls.addWidget(btn)

        controls.addStretch()
        layout.addLayout(controls)


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
        self.setStyleSheet(f"""
            #clip_card {{
                background: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: {Radii.base};
            }}
            #clip_card:hover, #clip_card.selected {{
                border-color: {Colors.PRIMARY_500};
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
        title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        info_layout.addWidget(title_label)

        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(8)
        type_label = QLabel(clip_type)
        type_label.setFont(QFont("", FontSizes.xs))
        type_label.setStyleSheet(f"color: {Colors.PRIMARY_400};")
        meta_layout.addWidget(type_label)

        duration_label = QLabel(duration)
        duration_label.setFont(QFont("", FontSizes.xs))
        duration_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        meta_layout.addWidget(duration_label)
        info_layout.addLayout(meta_layout)

        layout.addLayout(info_layout, 1)

        action_btn = QPushButton("✂")
        action_btn.setObjectName("action_btn")
        action_btn.setFixedSize(32, 32)
        action_btn.setStyleSheet(f"""
            QPushButton#action_btn {{
                background: {Colors.BG_ELEVATED};
                border: none;
                border-radius: {Radii.sm};
                color: {Colors.TEXT_MUTED};
                font-size: 14px;
            }}
            QPushButton#action_btn:hover {{
                color: {Colors.PRIMARY_400};
            }}
        """)
        layout.addWidget(action_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self._clip_id)


class StepEditPage(StepPage):
    """剪辑步骤页 (step 2)"""

    def __init__(self, parent=None):
        super().__init__(2, parent)

    def _build_content(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(24)

        # 预览区
        preview_label = QLabel("剪辑预览")
        preview_label.setFont(QFont("", FontSizes.md, QFont.Weight.Semibold))
        preview_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(preview_label)

        timeline = TimelinePreview()
        layout.addWidget(timeline)

        # 剪辑列表
        clips_label = QLabel("待处理片段")
        clips_label.setFont(QFont("", FontSizes.md, QFont.Weight.Semibold))
        clips_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
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
                background: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                padding: 4px 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        sub_row.addWidget(style_combo)
        sub_layout.addLayout(sub_row)

        layout.addWidget(subtitle_card)

        layout.addStretch()
        return container
