#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CreationWizardPage — OKLCH Design Tokens
frontend-design-pro: OKLCH色彩 · OutCubic动效 · 脉冲指示器

架构：
    Step1 (上传配置) → Step2 (Pipeline 执行) → Step3 (预览导出)
    横向进度指示器 + 页面切换滑入动画
"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PySide6.QtGui import QFont

from .base_page import BasePage
from .step_upload import StepUpload
from .step_pipeline import StepPipeline
from .step_export import StepExport
from app.orchestration.pipeline_controller import PipelineController

# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    # Surface
    "bg_indicator": "oklch(0.14 0.01 250)",  # 指示器背景
    # Border
    "border":        "oklch(0.20 0.01 250)",  # 指示器底部边框
    "border_pending":"oklch(0.24 0.01 250)",  # 待完成态
    # Text
    "text":          "oklch(0.93 0.01 250)",  # 主要文字
    "text_muted":    "oklch(0.55 0.01 250)",  # 辅助文字
    # Primary
    "primary":       "oklch(0.65 0.20 250)",  # 主色蓝
    "primary_l":     "oklch(0.70 0.24 250)",  # 脉冲亮色
    # Stage states
    "done":          "oklch(0.65 0.20 250)",  # 完成态（主色）
    # Easing (for reference)
    "ease_out":      "cubic-bezier(0.16, 1, 0.3, 1)",  # OutCubic
}

# ── Animation constants ──────────────────────────────────────
_ANIM_DURATION = 280  # ms — OutCubic page transition
_PULSE_INTERVAL = 800  # ms — active dot pulse


class AnimatedDot(QFrame):
    """
    脉冲动画圆点 — OKLCH
    当前步骤：脉冲发光效果（primary ↔ primary_l 交替）
    已完成：静态主色
    待完成：透明边框
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "pending"  # pending | active | done
        self._anim_toggle = False
        self.setFixedSize(20, 20)

    def set_state(self, state: str):
        self._state = state
        if state == "active":
            self._start_pulse()
        else:
            self._stop_pulse()
            self._apply_style()

    def _apply_style(self):
        if self._state == "done":
            self.setStyleSheet(f"""
                QFrame {{
                    background: {_T['done']};
                    border-radius: 10px;
                }}
            """)
        elif self._state == "active":
            color = _T["primary_l"] if self._anim_toggle else _T["primary"]
            self.setStyleSheet(f"""
                QFrame {{
                    background: {color};
                    border-radius: 10px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background: transparent;
                    border: 2px solid {_T['border_pending']};
                    border-radius: 10px;
                }}
            """)

    def _start_pulse(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._toggle)
        self._timer.start(_PULSE_INTERVAL)

    def _stop_pulse(self):
        if hasattr(self, "_timer"):
            self._timer.stop()

    def _toggle(self):
        self._anim_toggle = not self._anim_toggle
        self._apply_style()


class StepIndicator(QFrame):
    """
    横向步骤指示器 — OKLCH
    [脉冲点 Step1] —— [○ Step2] —— [○ Step3]
    主动画效: OutCubic 缓动（由 QPropertyAnimation 驱动）
    """

    step_clicked = Signal(int)

    _STEPS = ["上传", "创作", "导出"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = 0
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(60)
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {_T['bg_indicator']},
                    stop:1 {_T['bg_indicator']});
                border-bottom: 1px solid {_T['border']};
                border-radius: 0px;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 0, 32, 0)
        layout.setSpacing(8)

        self._dots: list[AnimatedDot] = []

        for i, label_text in enumerate(self._STEPS):
            dot = AnimatedDot()
            self._update_dot(dot, i)
            layout.addWidget(dot)
            self._dots.append(dot)

            lbl = QLabel(label_text)
            lbl.setFont(QFont("", 13, QFont.Weight.Bold if i == 0 else QFont.Weight.Normal))
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            self._update_lbl(lbl, i)
            lbl.mousePressEvent = lambda _, idx=i: self.step_clicked.emit(idx)
            layout.addWidget(lbl)

            if i < len(self._STEPS) - 1:
                # 分隔线 — OKLCH 渐变
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setStyleSheet(f"""
                    border: none;
                    border-top: 2px solid qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 {_T['primary']},
                        stop:1 {_T['border_pending']});
                    margin: 0 8px;
                """)
                layout.addWidget(line, 1)

        layout.addStretch()

    def _update_dot(self, dot: AnimatedDot, index: int):
        if index < self._current:
            dot.set_state("done")
        elif index == self._current:
            dot.set_state("active")
        else:
            dot.set_state("pending")

    def _update_lbl(self, lbl: QLabel, index: int):
        if index <= self._current:
            lbl.setStyleSheet(f"color: {_T['text']}; font-size: 13px; font-weight: 700;")
        else:
            lbl.setStyleSheet(f"color: {_T['text_muted']}; font-size: 13px;")

    def set_current(self, step: int):
        self._current = step
        for i, dot in enumerate(self._dots):
            self._update_dot(dot, i)
            w = self.layout().itemAt(i * 2 + 1).widget()
            if w and isinstance(w, QLabel):
                self._update_lbl(w, i)


class CreationWizardPage(BasePage):
    """
    创作向导主页面 — OKLCH Design Tokens
    页面切换: QPropertyAnimation + OutCubic 缓动（{_ANIM_DURATION}ms）
    """

    def __init__(self, page_id: str, title: str, application):
        super().__init__(page_id, title, application)
        self._controller = PipelineController(self)
        self._is_animating = False
        self._init_ui()
        self._bind_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.step_indicator = StepIndicator()
        layout.addWidget(self.step_indicator)

        self.page_stack = QStackedWidget()

        self._step_upload = StepUpload()
        self._step_pipeline = StepPipeline()
        self._step_export = StepExport()

        self.page_stack.addWidget(self._step_upload)
        self.page_stack.addWidget(self._step_pipeline)
        self.page_stack.addWidget(self._step_export)

        layout.addWidget(self.page_stack, 1)

        self.step_indicator.step_clicked.connect(self._show_step)

    def _bind_signals(self):
        self._step_upload.config_ready.connect(self._start_pipeline)
        self._step_pipeline.bind_controller(self._controller)
        self._step_pipeline.finished.connect(self._on_pipeline_step_finished)
        self._step_export.restart_requested.connect(self._restart_wizard)

    def activate(self) -> None:
        super().activate()

    def _restart_wizard(self):
        self._controller.reset()
        self._show_step(0)

    def _show_step(self, index: int):
        if self._is_animating or index == self.page_stack.currentIndex():
            return
        self._is_animating = True
        old_widget = self.page_stack.currentWidget()
        new_widget = self.page_stack.widget(index)
        rect = self.page_stack.geometry()

        if rect.isNull() or rect.width() == 0:
            self.step_indicator.set_current(index)
            self.page_stack.setCurrentIndex(index)
            self._is_animating = False
            return

        # 滑入动画: OutCubic {_ANIM_DURATION}ms
        if old_widget:
            old_anim = QPropertyAnimation(old_widget, b"pos")
            old_anim.setDuration(_ANIM_DURATION)
            old_anim.setStartValue(old_widget.pos())
            old_anim.setEndValue(old_widget.pos() + QPoint(-rect.width() // 3, 0))
            old_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            old_anim.start()

        new_widget.setGeometry(rect)
        new_widget.move(new_widget.pos() + QPoint(rect.width() // 3, 0))
        self.page_stack.setCurrentIndex(index)
        new_anim = QPropertyAnimation(new_widget, b"pos")
        new_anim.setDuration(_ANIM_DURATION)
        new_anim.setStartValue(new_widget.pos())
        new_anim.setEndValue(new_widget.pos())
        new_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        new_anim.finished.connect(lambda: setattr(self, '_is_animating', False))
        new_anim.start()

        self.step_indicator.set_current(index)

    def _start_pipeline(self, video_path, context, emotion, style, output_dir):
        self._show_step(1)
        self._controller.start_pipeline(
            video_path=video_path,
            context=context,
            emotion=emotion,
            style=style,
            output_dir=output_dir,
        )

    def _on_pipeline_step_finished(self, direction: str):
        if direction == "export":
            self._show_step(2)
            project = self._controller.current_project()
            self._step_export.set_project(project)
            self._step_export.set_source_video(project.source_video)
        elif direction == "back":
            self._show_step(0)

    def get_page_name(self) -> str:
        return "创作向导"

    def get_page_icon(self) -> str:
        return "🎬"
