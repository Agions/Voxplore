#!/usr/bin/env python3

"""
PageTransition — 页面切换动画管理器

历史：原位于 scenefab.ui.theme.animation_helper，Phase 3 重构中
拆分为独立模块。
"""
from PySide6.QtCore import (
    QEasingCurve,
    QGraphicsOpacityEffect,
    QPropertyAnimation,
    QTimer,
)
from PySide6.QtWidgets import QWidget

from ._animation_helper import AnimationHelper


class PageTransition:
    """页面切换动画管理器"""

    def __init__(self, stacked_widget):
        self.stacked_widget = stacked_widget

    def switch_page(self, index: int, animation_type: str = "fade"):
        """切换页面并播放动画

        Args:
            index: 目标页面索引
            animation_type: 动画类型 ("fade", "slide", "scale")

        当系统启用了 prefers-reduced-motion 时：
        - 直接切换，无动画效果
        """
        if index < 0 or index >= self.stacked_widget.count():
            return

        # 如果启用 reduce motion，直接切换
        if AnimationHelper._prefers_reduced_motion():
            self.stacked_widget.setCurrentIndex(index)
            return

        current_widget = self.stacked_widget.currentWidget()
        target_widget = self.stacked_widget.widget(index)

        _TRANSITION_MAP = {
            "fade": self._fade_transition,
            "slide": self._slide_transition,
            "scale": self._scale_transition,
        }
        transition = _TRANSITION_MAP.get(animation_type)
        if transition:
            transition(current_widget, target_widget)
        else:
            self.stacked_widget.setCurrentIndex(index)

    def _fade_transition(self, from_widget: QWidget, to_widget: QWidget):
        """淡入淡出切换"""
        # 淡出当前页面
        self.fade_out(from_widget, duration=200)

        # 切换到目标页面并淡入
        QTimer.singleShot(200, lambda: [
            self.stacked_widget.setCurrentWidget(to_widget),
            self.fade_in(to_widget, duration=200)
        ])

    def _slide_transition(self, from_widget: QWidget, to_widget: QWidget):
        """滑动切换"""
        # 获取宽度
        _ = self.stacked_widget.width()  # needed to compute transition

        # 淡出当前页面
        self.fade_out(from_widget, duration=150)

        # 切换并淡入目标页面
        QTimer.singleShot(150, lambda: [
            self.stacked_widget.setCurrentWidget(to_widget),
            self.fade_in(to_widget, duration=150)
        ])

    def _scale_transition(self, from_widget: QWidget, to_widget: QWidget):
        """缩放切换"""
        self.scale_out(from_widget, duration=150)

        QTimer.singleShot(150, lambda: [
            self.stacked_widget.setCurrentWidget(to_widget),
            self.scale_in(to_widget, duration=150)
        ])

    def fade_in(self, widget: QWidget, duration: int = 200):
        """淡入"""
        actual_duration = AnimationHelper._get_reduced_duration(duration)
        if actual_duration < 10:
            widget.show()
            return

        opacity = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(opacity)

        animation = QPropertyAnimation(opacity, b"opacity")
        animation.setDuration(actual_duration)
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.start()

    def fade_out(self, widget: QWidget, duration: int = 200):
        """淡出"""
        actual_duration = AnimationHelper._get_reduced_duration(duration)
        if actual_duration < 10:
            widget.hide()
            return

        opacity = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(opacity)

        animation = QPropertyAnimation(opacity, b"opacity")
        animation.setDuration(actual_duration)
        animation.setStartValue(1)
        animation.setEndValue(0)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.start()

    def scale_in(self, widget: QWidget, duration: int = 150):
        """缩放入场"""
        actual_duration = AnimationHelper._get_reduced_duration(duration)
        if actual_duration < 10:
            widget.show()
            return

        opacity = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(opacity)

        # 透明度动画
        opacity_anim = QPropertyAnimation(opacity, b"opacity")
        opacity_anim.setDuration(actual_duration)
        opacity_anim.setStartValue(0)
        opacity_anim.setEndValue(1)

        # 大小动画
        size_anim = QPropertyAnimation(widget, b"size")
        size_anim.setDuration(actual_duration)
        size_anim.setStartValue(int(widget.width() * 0.9), int(widget.height() * 0.9))
        size_anim.setEndValue(widget.width(), widget.height())
        size_anim.setEasingCurve(QEasingCurve.Type.OutBack)

        opacity_anim.start()
        size_anim.start()

    def scale_out(self, widget: QWidget, duration: int = 150):
        """缩放退场"""
        actual_duration = AnimationHelper._get_reduced_duration(duration)
        if actual_duration < 10:
            widget.hide()
            return

        opacity = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(opacity)

        # 透明度动画
        opacity_anim = QPropertyAnimation(opacity, b"opacity")
        opacity_anim.setDuration(actual_duration)
        opacity_anim.setStartValue(1)
        opacity_anim.setEndValue(0)

        # 大小动画
        size_anim = QPropertyAnimation(widget, b"size")
        size_anim.setDuration(actual_duration)
        size_anim.setStartValue(widget.width(), widget.height())
        size_anim.setEndValue(int(widget.width() * 0.9), int(widget.height() * 0.9))
        size_anim.setEasingCurve(QEasingCurve.Type.InBack)

        opacity_anim.start()
        size_anim.start()


__all__ = ["PageTransition"]
