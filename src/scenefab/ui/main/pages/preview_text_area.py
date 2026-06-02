#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预览文本区组件

从 step_preview.py 提取 PreviewTextArea
包含完整解说文案预览区 + 分段编辑功能
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .narration_segment_card import NarrationSegmentCard

# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    "bg_card":     "oklch(0.16 0.01 250)",
    "bg_input":    "oklch(0.13 0.01 250)",
    "bg_active":   "oklch(0.17 0.01 250)",
    "border":      "oklch(0.24 0.01 250)",
    "border_h":    "oklch(0.30 0.02 250)",
    "primary":     "oklch(0.65 0.20 250)",
    "primary_l":   "oklch(0.70 0.24 250)",
    "text":        "oklch(0.93 0.01 250)",
    "text_sub":    "oklch(0.75 0.01 250)",
    "text_muted":  "oklch(0.55 0.01 250)",
}


# ── 预览文本区（带标签预览）────────────────────────────────
class PreviewTextArea(QFrame):
    """
    完整解说文案预览区
    显示所有分段，带标签装饰（开场/高潮/结尾等）
    """
    text_changed = Signal(str)  # 整个文案变更

    def __init__(self, parent=None):
        super().__init__(parent)
        self._segments = []  # list of (time_range, text, emotion)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {_T['bg_card']};
                border: 1px solid {_T['border']};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 头部
        header = QHBoxLayout()
        title = QLabel("解说文案预览")
        title.setFont(QFont("", 13, QFont.Weight.SemiBold))
        title.setStyleSheet(f"color: {_T['text']};")
        header.addWidget(title)

        self._word_count_label = QLabel("0 字")
        self._word_count_label.setStyleSheet(f"color: {_T['text_muted']}; font-size: 11px;")
        header.addWidget(self._word_count_label)
        header.addStretch()

        # 全量编辑开关
        self._bulk_edit_cb = QCheckBox("全量编辑")
        self._bulk_edit_cb.setStyleSheet(f"""
            QCheckBox {{
                color: {_T['text_sub']};
                font-size: 11px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 3px;
            }}
        """)
        self._bulk_edit_cb.toggled.connect(self._on_bulk_edit_toggled)
        header.addWidget(self._bulk_edit_cb)
        layout.addLayout(header)

        # 分段列表（可滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {_T['bg_input']};
                border-radius: 4px;
                width: 6px;
                margin: 2px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {_T['border_h']};
                border-radius: 3px;
            }}
        """)
        self._segments_container = QWidget()
        self._segments_layout = QVBoxLayout(self._segments_container)
        self._segments_layout.setSpacing(12)
        self._segments_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self._segments_container)
        layout.addWidget(scroll, stretch=1)

        # 全量编辑文本区（默认隐藏）
        self._bulk_text_edit = QTextEdit()
        self._bulk_text_edit.setFont(QFont("", 13))
        self._bulk_text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {_T['bg_input']};
                color: {_T['text']};
                border: 1px solid {_T['border']};
                border-radius: 8px;
                padding: 12px;
                line-height: 1.8;
            }}
            QTextEdit:focus {{ border-color: {_T['primary']}; }}
        """)
        self._bulk_text_edit.setVisible(False)
        self._bulk_text_edit.textChanged.connect(self._on_bulk_text_changed)
        layout.addWidget(self._bulk_text_edit, stretch=1)

        # ── 分段预览标签（段落摘要横条）────────────────────
        self._segment_tabs = QTabWidget()
        self._segment_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {_T['border']};
                border-radius: 8px;
                background: {_T['bg_input']};
            }}
            QTabBar::tab {{
                background: transparent;
                color: {_T['text_muted']};
                padding: 6px 14px;
                font-size: 11px;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {_T['primary']};
                border-bottom-color: {_T['primary']};
            }}
        """)
        self._segment_tabs.setVisible(False)
        layout.addWidget(self._segment_tabs)

    def load_segments(self, segments: list):
        """
        加载分段列表
        segments: [(time_range, text, emotion), ...]
        """
        self._segments = segments

        # 清空现有分段
        while self._segments_layout.count():
            item = self._segments_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加分段卡片
        for i, (t_range, text, emotion) in enumerate(segments):
            card = NarrationSegmentCard(i, t_range, text, emotion)
            card.content_changed.connect(self._on_segment_changed)
            self._segments_layout.addWidget(card)

        self._update_word_count()
        self._update_segment_tabs()

    def get_segments(self) -> list:
        """获取所有分段的 (time_range, text, emotion)"""
        result = []
        for i in range(self._segments_layout.count()):
            card = self._segments_layout.itemAt(i).widget()
            if isinstance(card, NarrationSegmentCard):
                result.append((
                    card._time_range,
                    card.get_text(),
                    card._emotion
                ))
        return result

    def _on_segment_changed(self, text: str):
        self._update_word_count()

    def _on_bulk_edit_toggled(self, checked: bool):
        if checked:
            # 切换到全量编辑模式
            self._bulk_text_edit.setVisible(True)
            self._bulk_text_edit.setPlainText("\n\n".join(
                f"[{s[0]}] {s[1]}" for s in self._segments
            ))
            # 隐藏分段卡片
            self._segments_container.setVisible(False)
            self._segment_tabs.setVisible(False)
        else:
            self._bulk_text_edit.setVisible(False)
            self._segments_container.setVisible(True)
            self._segment_tabs.setVisible(False)

    def _on_bulk_text_changed(self):
        self._update_word_count()

    def _update_word_count(self):
        if self._bulk_edit_cb.isChecked():
            text = self._bulk_text_edit.toPlainText()
        else:
            text = "\n".join(s[1] for s in self._segments)
        count = len(text.replace(" ", "").replace("\n", ""))
        self._word_count_label.setText(f"{count} 字")

    def _update_segment_tabs(self):
        """更新段落摘要标签页"""
        self._segment_tabs.clear()
        for i, (t_range, text, emotion) in enumerate(self._segments):
            snippet = text[:60] + ("…" if len(text) > 60 else "")
            self._segment_tabs.addTab(QWidget(), f"[{t_range}] {snippet}")
