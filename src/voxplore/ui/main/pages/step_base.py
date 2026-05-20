#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创作流程页面基类 v6 — 统一的步骤指示器 + 流畅页面切换
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QGraphicsOpacityEffect, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QPainter

from voxplore.ui.theme.ds_tokens import Colors, FontSizes, FontWeights, Spacing, Radii


# ═══════════════════════════════════════════════════════════════════════
# 步骤指示器
# ═══════════════════════════════════════════════════════════════════════

class StepIndicator(QFrame):
    """优雅的步骤指示器"""

    step_changed = Signal(int)

    STEPS = ["上传", "AI 分析", "剪辑", "导出"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = 0
        self.setFixedHeight(72)
        self.setObjectName("step_indicator")
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 0, 32, 0)
        layout.setSpacing(0)

        for i, name in enumerate(self.STEPS):
            step_layout = QHBoxLayout()
            step_layout.setSpacing(10)
            step_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

            # 圆圈
            circle = QLabel()
            circle.setObjectName(f"step_circle_{i}")
            circle.setFixedSize(32, 32)
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setFont(QFont("", FontSizes.sm, QFont.Weight.SemiBold))
            step_layout.addWidget(circle)

            # 标签
            label = QLabel(name)
            label.setObjectName(f"step_label_{i}")
            label.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
            step_layout.addWidget(label)

            layout.addLayout(step_layout)

            # 连接线
            if i < len(self.STEPS) - 1:
                line = QFrame()
                line.setObjectName(f"step_line_{i}")
                line.setFixedHeight(2)
                line.setMinimumWidth(40)
                line.setMaximumWidth(100)
                line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                layout.addWidget(line)

        layout.addStretch()
        self._apply_state(0)

    def _apply_state(self, current: int):
        for i, name in enumerate(self.STEPS):
            is_done  = i < current
            is_active = i == current
            is_pending = i > current  # noqa: F841  # used in style branch below
            _ = is_pending  # suppress unused warning

            circle: QLabel = self.findChild(QLabel, f"step_circle_{i}")
            label: QLabel = self.findChild(QLabel, f"step_label_{i}")

            if is_done:
                circle.setText("✓")
                circle.setStyleSheet(f"""
                    background: {Colors.SUCCESS};
                    color: white;
                    border-radius: 16px;
                    font-size: 14px;
                """)
                label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
            elif is_active:
                circle.setText(str(i + 1))
                circle.setStyleSheet(f"""
                    background: {Colors.PRIMARY_DARK};
                    color: white;
                    border-radius: 16px;
                    font-weight: bold;
                """)
                label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: {FontWeights.SemiBold};")
            else:
                circle.setText(str(i + 1))
                circle.setStyleSheet(f"""
                    background: transparent;
                    color: {Colors.TEXT_DISABLED};
                    border: 2px solid {Colors.BORDER_DEFAULT};
                    border-radius: 16px;
                """)
                label.setStyleSheet(f"color: {Colors.TEXT_DISABLED};")

            line: QFrame = self.findChild(QFrame, f"step_line_{i}")
            if line:
                if is_done:
                    line.setStyleSheet(f"background: {Colors.SUCCESS}; border: none;")
                else:
                    line.setStyleSheet(f"background: {Colors.BORDER_DEFAULT}; border: none;")

    def set_step(self, step: int):
        self._apply_state(step)


# ═══════════════════════════════════════════════════════════════════════
# 底部操作栏
# ═══════════════════════════════════════════════════════════════════════

class ActionBar(QFrame):
    """底部操作栏"""

    next_clicked = Signal()
    prev_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self, show_cancel: bool = True, show_prev: bool = True,
                 show_next: bool = True, parent=None):
        super().__init__(parent)
        self._show_cancel = show_cancel
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

        if self._show_cancel:
            cancel_btn = QPushButton("取消")
            cancel_btn.setObjectName("btn_cancel")
            cancel_btn.setFixedSize(90, 38)
            cancel_btn.clicked.connect(self.cancel_clicked.emit)
            layout.addWidget(cancel_btn)
        else:
            layout.addWidget(QWidget())

        layout.addStretch()

        if self._show_prev:
            prev_btn = QPushButton("← 上一步")
            prev_btn.setObjectName("btn_secondary")
            prev_btn.setFixedSize(100, 38)
            prev_btn.clicked.connect(self.prev_clicked.emit)
            layout.addWidget(prev_btn)

        if self._show_next:
            next_btn = QPushButton("下一步 →")
            next_btn.setObjectName("btn_primary")
            next_btn.setFixedSize(110, 38)
            next_btn.clicked.connect(self.next_clicked.emit)
            layout.addWidget(next_btn)

    def set_next_enabled(self, enabled: bool):
        next_btn = self.findChild(QPushButton, "btn_primary")
        if next_btn:
            next_btn.setEnabled(enabled)


# ═══════════════════════════════════════════════════════════════════════
# 内容卡片容器
# ═══════════════════════════════════════════════════════════════════════

class ContentCard(QFrame):
    """通用内容卡片"""

    def __init__(self, title: str = "", icon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("content_card")
        self._setup_style()
        self._setup_ui(title, icon)

    def _setup_style(self):
        self.setStyleSheet(f"""
            QFrame#content_card {{
                background: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: {Radii.xl};
            }}
        """)

    def _setup_ui(self, title: str, icon: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        if title:
            header_layout = QHBoxLayout()
            header_layout.setSpacing(10)

            if icon:
                icon_lbl = QLabel(icon)
                icon_lbl.setFont(QFont("", 16))
                icon_lbl.setStyleSheet(f"color: {Colors.PRIMARY};")
                header_layout.addWidget(icon_lbl)

            title_lbl = QLabel(title)
            title_lbl.setFont(QFont("", FontSizes.md, QFont.Weight.SemiBold))
            title_lbl.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
            header_layout.addWidget(title_lbl)
            header_layout.addStretch()
            layout.addLayout(header_layout)


# ═══════════════════════════════════════════════════════════════════════
# 步骤页面基类
# ═══════════════════════════════════════════════════════════════════════

class StepPage(QFrame):
    """步骤页面基类，支持淡入动画"""

    next_requested = Signal()
    prev_requested = Signal()
    step_changed = Signal(int)
    finished = Signal()

    # 子类覆盖
    STEP_INDEX = 0
    STEP_TITLE = ""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName(f"step_page_{self.STEP_INDEX}")
        self._setup_ui()
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(f"""
            #step_page_{self.STEP_INDEX} {{
                background: {Colors.BG_BASE};
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 步骤指示器
        indicator = StepIndicator()
        layout.addWidget(indicator)

        # 内容区
        content_scroll = QScrollArea()
        content_scroll.setWidgetResizable(True)
        content_scroll.setStyleSheet("border: none; background: transparent;")
        content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 28, 40, 24)
        content_layout.setSpacing(24)
        content_layout.addWidget(self._build_content())
        content_layout.addStretch()

        content_scroll.setWidget(content_widget)
        layout.addWidget(content_scroll, 1)

        # 操作栏
        action_bar = ActionBar(show_cancel=True)
        action_bar.next_clicked.connect(self._on_next)
        action_bar.prev_clicked.connect(self._on_prev)
        action_bar.cancel_clicked.connect(self._on_cancel)
        layout.addWidget(action_bar)
        self._action_bar = action_bar

    def _build_content(self) -> QWidget:
        """子类实现"""
        w = QWidget()
        w.setFixedHeight(300)
        return w

    def _on_next(self):
        if self.STEP_INDEX < 3:
            self.step_changed.emit(self.STEP_INDEX + 1)
        self.next_requested.emit()

    def _on_prev(self):
        if self.STEP_INDEX > 0:
            self.step_changed.emit(self.STEP_INDEX - 1)
        self.prev_requested.emit()

    def _on_cancel(self):
        self.finished.emit()

    def showEvent(self, event):
        super().showEvent(event)
        self._fade_in()

    def _fade_in(self, duration: int = 200):
        """淡入效果"""
        eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(eff)
        eff.setOpacity(0)
        anim = QPropertyAnimation(eff, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        anim.finished.connect(lambda: self.setGraphicsEffect(None))
