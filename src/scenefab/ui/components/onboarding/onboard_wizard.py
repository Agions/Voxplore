#!/usr/bin/env python3

"""
Onboarding 向导组件

提供新用户首次使用的引导流程界面，包含欢迎页和功能介绍。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from scenefab.ui.theme.ds_tokens import _C

# Re-export step classes for wizard's internal use
from .onboard_steps import (
    AIProviderStep,
    CompletionStep,
    PreferencesStep,
    StepIndicator,
    WelcomeStep,
)


# 渐变按钮 QSS — 复用 feature_tour._gradient_btn 模式
_GRADIENT_BTN_QSS = (
    "QPushButton {{"
    "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
    "    stop:0 {c1}, stop:1 {c2});"
    "  color: white; border: none; border-radius: 10px;"
    "  font-size: 13px; font-weight: 600;}}"
    "QPushButton:hover {{"
    "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
    "    stop:0 {h1}, stop:1 {c2});}}"
    "QPushButton:pressed {{"
    "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
    "    stop:0 {_C.PRIMARY_DARKEST}, stop:1 {_C.PRIMARY_DARKER});}}"
)


class OnboardingWizard(QWidget):
    """首次使用引导向导"""

    # 信号定义
    finished = Signal(dict)  # 完成信号，传递配置数据
    skipped = Signal()  # 跳过信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_step = 0
        self._setup_ui()

    def _setup_ui(self):
        """设置 UI — 组装各子区域"""
        self.setFixedSize(550, 500)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 主容器
        main_widget = QWidget(self)
        main_widget.setFixedSize(550, 500)
        main_widget.setStyleSheet(
            f"QWidget {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"  stop:0 {_C.BG_BASE}, stop:0.5 {_C.BG_SURFACE}, stop:1 {_C.BG_BASE});"
            f"  border: 1px solid {_C.BORDER_DEFAULT}; border-radius: 20px; }}"
        )

        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        # 步骤指示器
        self.step_indicator = StepIndicator(["欢迎", "AI 配置", "偏好设置"])
        layout.addWidget(self.step_indicator)

        # 分隔线
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background: {_C.BORDER_DEFAULT};")
        layout.addWidget(separator)

        # 步骤内容区域
        self.content_stack = QWidget()
        self.content_layout = QVBoxLayout(self.content_stack)
        self.content_layout.setContentsMargins(16, 16, 16, 16)

        self.steps = [WelcomeStep(), AIProviderStep(), PreferencesStep(), CompletionStep()]
        for step in self.steps:
            self.content_layout.addWidget(step)

        self._show_step(0)
        layout.addWidget(self.content_stack)

        # 按钮区域
        layout.addLayout(self._build_button_bar())

    def _build_button_bar(self) -> QHBoxLayout:
        """底部按钮栏: 上一步 + 跳过 + 下一步"""
        bar = QHBoxLayout()
        bar.setSpacing(12)

        # 上一步
        self.prev_btn = QPushButton("上一步")
        self.prev_btn.setFixedHeight(40)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHand)  # type: ignore[attr-defined]
        self.prev_btn.setStyleSheet(
            f"QPushButton {{ background-color: {_C.BG_SURFACE}; color: {_C.TEXT_SECONDARY};"
            f"  border: 1px solid {_C.BORDER_DEFAULT}; border-radius: 10px;"
            f"  font-size: 13px; font-weight: 500; }}"
            f"QPushButton:hover {{ background-color: {_C.BG_ELEVATED};"
            f"  border-color: {_C.PRIMARY}; color: {_C.TEXT_PRIMARY}; }}"
        )
        self.prev_btn.clicked.connect(self._prev_step)
        bar.addWidget(self.prev_btn)
        bar.addStretch()

        # 跳过
        self.skip_btn = QPushButton("跳过")
        self.skip_btn.setCursor(Qt.CursorShape.PointingHand)  # type: ignore[attr-defined]
        self.skip_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_C.TEXT_MUTED};"
            f"  border: none; font-size: 13px; }}"
            f"QPushButton:hover {{ color: {_C.TEXT_SECONDARY}; }}"
        )
        self.skip_btn.clicked.connect(self._on_skip)
        bar.addWidget(self.skip_btn)

        # 下一步/完成
        self.next_btn = QPushButton("下一步")
        self.next_btn.setFixedHeight(40)
        self.next_btn.setFixedWidth(120)
        self.next_btn.setCursor(Qt.CursorShape.PointingHand)  # type: ignore[attr-defined]
        self.next_btn.setStyleSheet(
            _GRADIENT_BTN_QSS.format(
                c1=_C.PRIMARY_DARK, c2=_C.PRIMARY, h1=_C.PRIMARY_LIGHT, _C=_C
            )
        )
        self.next_btn.clicked.connect(self._next_step)
        bar.addWidget(self.next_btn)

        return bar

    def _show_step(self, step_index: int):
        """显示指定步骤"""
        for i, step in enumerate(self.steps):
            step.setVisible(i == step_index)

        self.prev_btn.setVisible(0 < step_index < len(self.steps) - 1)

        if step_index == len(self.steps) - 1:
            self.next_btn.setText("开始使用")
            self.skip_btn.setVisible(False)
        else:
            self.next_btn.setText("下一步")
            self.skip_btn.setVisible(True)

    def _next_step(self):
        """下一步"""
        if self._current_step < len(self.steps) - 1:
            self._current_step += 1
            self._show_step(self._current_step)
        else:
            self._collect_and_finish()

    def _prev_step(self):
        """上一步"""
        if self._current_step > 0:
            self._current_step -= 1
            self._show_step(self._current_step)

    def _on_skip(self):
        """跳过引导"""
        self.skipped.emit()

    def _collect_and_finish(self):
        """收集数据并完成"""
        all_data = {}
        for step in self.steps:
            if hasattr(step, "get_values"):
                all_data.update(step.get_values())
        self.finished.emit(all_data)
