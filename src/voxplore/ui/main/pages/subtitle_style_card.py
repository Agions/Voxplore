#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字幕样式卡片组件

从 step_export.py 提取 SubtitleStyleCard
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt


# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    "bg_card":    "oklch(0.16 0.01 250)",
    "bg_active":  "oklch(0.17 0.01 250)",
    "border":     "oklch(0.24 0.01 250)",
    "border_h":   "oklch(0.30 0.02 250)",
    "primary":    "oklch(0.65 0.20 250)",
    "text":       "oklch(0.93 0.01 250)",
    "text_sub":   "oklch(0.75 0.01 250)",
}


# ── 字幕样式卡片 ────────────────────────────────────────────
class SubtitleStyleCard(QFrame):
    """
    字幕样式选择卡片 — OKLCH
    选中态: 主色边框发光 + 背景加深
    Hover: 边框微微亮起
    """

    selected = Signal(str)

    _STYLES = {
        "cinematic": ("电影字幕", "黑底白字，居中，适合故事叙述"),
        "minimal":   ("简约白字", "无背景白色文字，适合教程"),
        "dynamic":   ("动感字幕", "打字机效果，适合短内容"),
    }

    def __init__(self, style_id: str, parent=None):
        super().__init__(parent)
        self._style_id = style_id
        self._is_selected = False
        self._setup_ui()

    def _setup_ui(self):
        name, desc = self._STYLES.get(self._style_id, (self._style_id, ""))
        icon = {"cinematic": "🎬", "minimal": "✦", "dynamic": "⚡"}.get(
            self._style_id, "□"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel(icon)
        self.icon_label.setFont(QFont("", 24))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)

        name_label = QLabel(name)
        name_label.setFont(QFont("", 13, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {_T['text']};")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        desc_label = QLabel(desc)
        desc_label.setFont(QFont("", 11))
        desc_label.setStyleSheet(f"color: {_T['text_sub']}; line-height: 1.4;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        self.setMinimumSize(140, 140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

    def select(self):
        self._is_selected = True
        self._apply_style()

    def deselect(self):
        self._is_selected = False
        self._apply_style()

    def _apply_style(self):
        if self._is_selected:
            # OKLCH: 主色发光边框 + 背景加深
            self.setStyleSheet(f"""
                QFrame {{
                    background: {_T['bg_active']};
                    border: 2px solid {_T['primary']};
                    border-radius: 14px;
                    box-shadow: 0 0 16px oklch(0.65 0.20 250 / 0.20);
                }}
            """)
        else:
            # OKLCH: 默认边框
            self.setStyleSheet(f"""
                QFrame {{
                    background: {_T['bg_card']};
                    border: 1px solid {_T['border']};
                    border-radius: 14px;
                }}
                QFrame:hover {{
                    border-color: {_T['primary']}99;
                }}
            """)

    def mousePressEvent(self, event):
        self.selected.emit(self._style_id)
