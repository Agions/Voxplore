#!/usr/bin/env python3

"""
AnimatedButton & LoadingAnimation — 按钮/加载动画辅助

历史：原位于 scenefab.ui.theme.animation_helper，Phase 3 重构中
拆分为独立模块。
"""
from PySide6.QtCore import Qt, QTimer

from ._animation_helper import AnimationHelper


class AnimatedButton:
    """带动画效果的按钮辅助类"""

    @staticmethod
    def add_ripple_effect(button, color: str = "rgba(255, 255, 255, 0.3)"):
        """为按钮添加波纹效果（需要自定义绘制）"""
        # 这是一个占位实现，实际波纹效果需要重写 paintEvent
        button.setCursor(Qt.CursorShape.PointingHandCursor)

    @staticmethod
    def add_click_animation(button):
        """为按钮添加点击动画

        当系统启用了 prefers-reduced-motion 时：
        - 跳过点击动画
        """
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        if AnimationHelper._prefers_reduced_motion():
            return
        button.clicked.connect(lambda: AnimatedButton._pulse_click(button))

    @staticmethod
    def _pulse_click(button):
        """点击脉冲动画"""
        original_style = button.styleSheet()

        # 临时改变样式模拟按下效果
        button.setStyleSheet(button.styleSheet() + "transform: scale(0.95);")

        # 恢复
        QTimer.singleShot(100, lambda: button.setStyleSheet(original_style))


class LoadingAnimation:
    """加载动画组件"""

    @staticmethod
    def create_loading_dots(parent, count: int = 3, color: str = "#6366F1"):
        """创建加载点动画

        当系统启用了 prefers-reduced-motion 时：
        - 使用静态显示代替动画
        """
        from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

        container = QWidget(parent)
        layout = QHBoxLayout(container)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        dots = []
        for _i in range(count):
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 10px;")
            layout.addWidget(dot)
            dots.append(dot)

        # 根据减少动画偏好决定是否启用动画
        if AnimationHelper._prefers_reduced_motion():
            # reduce motion: 静态显示
            for d in dots:
                d.setStyleSheet(f"color: {color}; font-size: 10px; opacity: 1;")
            return container, None

        # 动画定时器
        def animate():
            for j, d in enumerate(dots):
                delay = (_i + j) % count
                opacity = 0.3 if delay != 0 else 1.0
                d.setStyleSheet(f"color: {color}; font-size: 10px; opacity: {opacity};")

        timer = QTimer(parent)
        timer.timeout.connect(animate)
        timer.start(200)

        return container, timer


__all__ = ["AnimatedButton", "LoadingAnimation"]
