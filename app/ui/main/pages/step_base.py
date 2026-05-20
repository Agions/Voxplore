#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创作流程页基础组件
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont

from app.ui.theme.ds_tokens import Colors, FontSizes, FontWeights, Spacing, Radii


# ═══════════════════════════════════════════════════════════════
# 步骤指示器
# ═══════════════════════════════════════════════════════════════

class StepIndicator(QFrame):
    """步骤指示器"""

    step_changed = Signal(int)

    STEPS = ["上传", "AI 分析", "剪辑", "导出"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = 0
        self.setFixedHeight(80)
        self.setObjectName("step_indicator")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #step_indicator {{
                background: {Colors.BG_SURFACE};
                border-bottom: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 16, 32, 16)
        layout.setSpacing(0)

        for i, name in enumerate(self.STEPS):
            # 步骤项
            step_item = QFrame()
            step_item_layout = QHBoxLayout(step_item)
            step_item_layout.setSpacing(12)

            # 圆圈数字
            circle = QLabel(str(i + 1))
            circle.setObjectName(f"step_circle_{i}")
            circle.setFixedSize(28, 28)
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
            step_item_layout.addWidget(circle)

            # 步骤名
            label = QLabel(name)
            label.setObjectName(f"step_label_{i}")
            label.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
            step_item_layout.addWidget(label)

            # 连接线
            if i < len(self.STEPS) - 1:
                line = QFrame()
                line.setFixedHeight(2)
                line.setMinimumWidth(60)
                line.setStyleSheet(f"background: {Colors.BORDER_SUBTLE};")
                step_item_layout.addWidget(line)

            layout.addWidget(step_item)

        layout.addStretch()
        self._update_steps(0)

    def _update_steps(self, current: int):
        self._current = current
        for i in range(len(self.STEPS)):
            is_done = i < current
            is_active = i == current
            is_pending = i > current

            circle = self.findChild(QLabel, f"step_circle_{i}")
            label = self.findChild(QLabel, f"step_label_{i}")

            if is_done:
                circle_style = f"""
                    background: {Colors.SUCCESS};
                    color: white;
                    border-radius: 14px;
                """
                label_style = f"color: {Colors.TEXT_SECONDARY};"
            elif is_active:
                circle_style = f"""
                    background: {Colors.PRIMARY_500};
                    color: white;
                    border-radius: 14px;
                """
                label_style = f"color: {Colors.TEXT_PRIMARY}; font-weight: {FontWeights.Bold};"
            else:
                circle_style = f"""
                    background: transparent;
                    color: {Colors.TEXT_MUTED};
                    border: 2px solid {Colors.BORDER_SUBTLE};
                    border-radius: 14px;
                """
                label_style = f"color: {Colors.TEXT_MUTED};"

            circle.setStyleSheet(circle_style)
            label.setStyleSheet(label_style)

    def set_step(self, step: int):
        self._update_steps(step)


# ═══════════════════════════════════════════════════════════════
# 操作区（下一步/上一步）
# ═══════════════════════════════════════════════════════════════

class ActionBar(QFrame):
    """底部操作栏"""

    next_clicked = Signal()
    prev_clicked = Signal()

    def __init__(self, show_prev: bool = True, show_next: bool = True, parent=None):
        super().__init__(parent)
        self._show_prev = show_prev
        self._show_next = show_next
        self.setFixedHeight(72)
        self.setObjectName("action_bar")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #action_bar {{
                background: {Colors.BG_SURFACE};
                border-top: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)

        # 上一步
        if self._show_prev:
            prev_btn = QPushButton("← 上一步")
            prev_btn.setObjectName("btn_secondary")
            prev_btn.setFixedSize(100, 40)
            prev_btn.clicked.connect(self.prev_clicked.emit)
            layout.addWidget(prev_btn)
        else:
            layout.addWidget(QWidget())

        layout.addStretch()

        # 下一步
        if self._show_next:
            next_btn = QPushButton("下一步 →")
            next_btn.setObjectName("btn_primary")
            next_btn.setFixedSize(100, 40)
            next_btn.clicked.connect(self.next_clicked.emit)
            layout.addWidget(next_btn)

        self.setStyleSheets()

    def setStyleSheets(self):
        self.setStyleSheet(f"""
            #action_bar {{
                background: {Colors.BG_SURFACE};
                border-top: 1px solid {Colors.BORDER_SUBTLE};
            }}
            QPushButton#btn_primary {{
                background: {Colors.PRIMARY_500};
                color: white;
                border: none;
                border-radius: {Radii.base};
                font-size: {FontSizes.base}px;
                font-weight: {FontWeights.Medium};
            }}
            QPushButton#btn_primary:hover {{
                background: {Colors.PRIMARY_400};
            }}
            QPushButton#btn_secondary {{
                background: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radii.base};
                font-size: {FontSizes.base}px;
            }}
            QPushButton#btn_secondary:hover {{
                background: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)


# ═══════════════════════════════════════════════════════════════
# 内容卡片
# ═══════════════════════════════════════════════════════════════

class ContentCard(QFrame):
    """通用内容卡片"""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("content_card")
        self._setup_style()
        self._title = title
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #content_card {{
                background: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: {Radii.lg};
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        if self._title:
            title = QLabel(self._title)
            title.setFont(QFont("", FontSizes.md, QFont.Weight.Semibold))
            title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
            layout.addWidget(title)


# ═══════════════════════════════════════════════════════════════
# 步骤页面基类
# ═══════════════════════════════════════════════════════════════

class StepPage(QFrame):
    """步骤页面基类"""

    next_requested = Signal()
    prev_requested = Signal()
    step_changed = Signal(int)

    def __init__(self, step_index: int, parent=None):
        super().__init__(parent)
        self._step_index = step_index
        self.setObjectName(f"step_page_{step_index}")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #step_page_{self._step_index} {{
                background: {Colors.BG_BASE};
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 步骤指示器
        self.step_indicator = StepIndicator()
        layout.addWidget(self.step_indicator)

        # 内容区
        content = QScrollArea()
        content.setWidgetResizable(True)
        content.setStyleSheet("border: none;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 24)
        content_layout.addWidget(self._build_content())
        content_layout.addStretch()
        layout.addWidget(content, 1)

        # 操作栏
        self.action_bar = ActionBar(
            show_prev=self._step_index > 0,
            show_next=self._step_index < 3
        )
        self.action_bar.next_clicked.connect(self._on_next)
        self.action_bar.prev_clicked.connect(self._on_prev)
        layout.addWidget(self.action_bar)

        self.step_indicator.set_step(self._step_index)

    def _build_content(self) -> QWidget:
        """子类实现具体内容"""
        return QWidget()

    def _on_next(self):
        self.step_changed.emit(self._step_index + 1)
        self.next_requested.emit()

    def _on_prev(self):
        self.step_changed.emit(self._step_index - 1)
        self.prev_requested.emit()
