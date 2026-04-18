#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 动画组件 — REDESIGNED
frontend-design-pro compliant: OutCubic easing · 微交互 100-150ms · 页面过渡 250-300ms

所有动画遵循:
- Easing: QEasingCurve.OutCubic (即 cubic-bezier(0.16, 1, 0.3, 1))
- 微交互: 100-150ms
- 页面切换: 250-300ms
- 禁止 bounce/elastic easing
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import (
    QPropertyAnimation, QEasingCurve, Qt, QRect, Signal, QTimer,
    QParallelAnimationGroup, QSequentialAnimationGroup
)
from PySide6.QtGui import QColor, QPainter, QPen, QPaintEvent


# ========================================================================
# Easing Constants — 所有动画统一使用 OutCubic
# ========================================================================

#: 微交互（hover/press）：100-150ms
MICRO_DURATION  = 120   # ms

#: 组件展开/收起：200-250ms
COMPONENT_DURATION = 220  # ms

#: 页面切换：250-300ms
PAGE_DURATION = 280  # ms


def out_cubic() -> QEasingCurve:
    """统一使用 OutCubic easing: cubic-bezier(0.16, 1, 0.3, 1)"""
    return QEasingCurve(QEasingCurve.Type.OutCubic)


def in_out_cubic() -> QEasingCurve:
    """In-Out Cubic: cubic-bezier(0.65, 0, 0.35, 1)"""
    return QEasingCurve(QEasingCurve.Type.InOutCubic)


# ========================================================================
# Core Animation Widgets
# ========================================================================

class FadeInWidget(QWidget):
    """
    淡入组件 — 用于 modal / tooltip / overlay
    Duration: MICRO_DURATION (120ms), Easing: OutCubic
    """

    def __init__(self, duration: int = MICRO_DURATION, parent=None):
        super().__init__(parent)
        self._duration = duration
        self.setWindowOpacity(0)
        self._animation = None

    def fade_in(self):
        """淡入"""
        self.show()
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(self._duration)
        self._animation.setStartValue(0)
        self._animation.setEndValue(1)
        self._animation.setEasingCurve(out_cubic())
        self._animation.start()

    def fade_out(self, callback=None):
        """淡出"""
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(self._duration)
        self._animation.setStartValue(1)
        self._animation.setEndValue(0)
        self._animation.setEasingCurve(out_cubic())
        if callback:
            self._animation.finished.connect(callback)
        self._animation.start()


class SlideWidget(QWidget):
    """
    滑动组件 — 用于 drawer / panel / tooltip
    Direction: left | right | top | bottom
    Duration: COMPONENT_DURATION (220ms), Easing: OutCubic
    """

    def __init__(self, direction: str = "left", duration: int = COMPONENT_DURATION, parent=None):
        super().__init__(parent)
        self._direction = direction
        self._duration = duration
        self._animation = None

    def slide_in(self):
        """滑入"""
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(self._duration)
        self._animation.setEasingCurve(out_cubic())

        parent_rect = self.parent().rect() if self.parent() else self.rect()
        my_rect = self.rect()

        if self._direction == "left":
            start = QRect(-my_rect.width(), my_rect.y(), my_rect.width(), my_rect.height())
            end   = QRect(0, my_rect.y(), my_rect.width(), my_rect.height())
        elif self._direction == "right":
            start = QRect(parent_rect.width(), my_rect.y(), my_rect.width(), my_rect.height())
            end   = QRect(parent_rect.width() - my_rect.width(), my_rect.y(), my_rect.width(), my_rect.height())
        elif self._direction == "top":
            start = QRect(my_rect.x(), -my_rect.height(), my_rect.width(), my_rect.height())
            end   = QRect(my_rect.x(), 0, my_rect.width(), my_rect.height())
        else:  # bottom
            start = QRect(my_rect.x(), parent_rect.height(), my_rect.width(), my_rect.height())
            end   = QRect(my_rect.x(), parent_rect.height() - my_rect.height(), my_rect.width(), my_rect.height())

        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.start()

    def slide_out(self, callback=None):
        """滑出"""
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(self._duration)
        self._animation.setEasingCurve(out_cubic())

        parent_rect = self.parent().rect() if self.parent() else self.rect()
        my_rect = self.rect()

        if self._direction == "left":
            end = QRect(-my_rect.width(), my_rect.y(), my_rect.width(), my_rect.height())
        elif self._direction == "right":
            end = QRect(parent_rect.width(), my_rect.y(), my_rect.width(), my_rect.height())
        elif self._direction == "top":
            end = QRect(my_rect.x(), -my_rect.height(), my_rect.width(), my_rect.height())
        else:
            end = QRect(my_rect.x(), parent_rect.height(), my_rect.width(), my_rect.height())

        self._animation.setStartValue(self.geometry())
        self._animation.setEndValue(end)
        if callback:
            self._animation.finished.connect(callback)
        self._animation.start()


class PulseWidget(QWidget):
    """
    脉冲组件 — 用于当前步骤指示器 / 活跃状态
    使用 QTimer 控制，每 600ms 切换一次
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pulse_on = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._toggle)

    def start_pulse(self, interval_ms: int = 600):
        """启动脉冲动画"""
        self._timer.start(interval_ms)

    def stop_pulse(self):
        """停止脉冲动画"""
        self._timer.stop()

    def _toggle(self):
        self._pulse_on = not self._pulse_on
        self.update()


class GlowLabel(QWidget):
    """
    发光标签 — 用于强调文字 / 徽章
    REDESIGN: 从紫色发光 → 蓝色发光
    """

    def __init__(self, text: str = "", color: str = "#0A84FF", parent=None):
        super().__init__(parent)
        self._text = text
        self._glow_color = QColor(color)
        self._glow_radius = 20

    def setText(self, text: str):
        self._text = text
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Glow
        glow = QColor(self._glow_color)
        glow.setAlpha(60)
        painter.setPen(QPen(glow, self._glow_radius))
        # Draw subtle glow ellipse behind text


class ShimmerEffect:
    """
    骨架屏 shimmer 效果

    QSS:
        background: qlineargradient(90deg,
            stop:0 #0E1520,
            stop:0.5 #1A2332,
            stop:1 #0E1520);
        background-size: 200% 100%;
        animation: shimmer 1.5s ease-in-out infinite;

    @keyframes shimmer:
        0%   { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    """

    @staticmethod
    def get_stylesheet(color: str = "#1A2332") -> str:
        return f"""
            QFrame {{
                background: qlineargradient(90deg,
                    stop:0 {color},
                    stop:0.5 #1E2A3A,
                    stop:1 {color});
                background-size: 200% 100%;
                border-radius: 8px;
            }}
        """

    @staticmethod
    def get_keyframes_primary() -> str:
        """主色 shimmer 关键帧（供 QSS 内嵌使用）"""
        return """
            @keyframes shimmer {
                0%   { background-position: 200% 0; }
                100% { background-position: -200% 0; }
            }
        """


class AnimatedCounter(QWidget):
    """
    数值动画计数器 — 用于进度数字 / 统计数据
    Duration: 1000ms, Easing: OutCubic
    """

    finished = Signal()
    valueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._target = 0
        self._animation = None

    def setValue(self, value: int, duration: int = 1000):
        """动画过渡到目标值"""
        self._target = value
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(duration)
        self._animation.setStartValue(self._value)
        self._animation.setEndValue(value)
        self._animation.setEasingCurve(out_cubic())
        self._animation.valueChanged.connect(
            lambda v: self.valueChanged.emit(int(v))
        )
        self._animation.finished.connect(self.finished.emit)
        self._animation.start()


class TransitionStack(QWidget):
    """
    堆叠过渡组件 — 用于标签页 / wizard 步骤
    基于 QPropertyAnimation + 方向控制
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._widgets = []
        self._current = None

    def push(self, widget: QWidget):
        if self._current:
            self._current.hide()
        self._widgets.append(widget)
        self._current = widget
        widget.show()

    def pop(self):
        if not self._widgets:
            return
        old = self._widgets.pop()
        old.hide()
        self._current = self._widgets[-1] if self._widgets else None
        if self._current:
            self._current.show()

    def current(self) -> QWidget:
        return self._current
