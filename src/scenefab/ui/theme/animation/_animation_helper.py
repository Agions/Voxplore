#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AnimationHelper — 通用动画辅助类

提供：
- prefers-reduced-motion 系统偏好检测（跨平台）
- 淡入 / 淡出 / 滑入 / 缩放 / 脉冲 动画
- 动画时长自动适配（减少动画时缩短至 10ms 内）
"""
import platform
import logging
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QSettings

logger = logging.getLogger(__name__)


class AnimationHelper:
    """动画辅助类"""

    # 类级别缓存，避免重复查询系统设置
    _reduced_motion_cache: bool | None = None

    @classmethod
    def _prefers_reduced_motion(cls) -> bool:
        """检测系统是否启用了减少动画偏好

        检测优先级：
        1. 类缓存（避免重复查询）
        2. Qt QSettings（跨平台）
        3. macOS: AppleReduceMotion
        4. Windows: EaseOfAccess 显示动画选项
        5. Linux: GTK/Qt 减少动画设置
        """
        if cls._reduced_motion_cache is not None:
            return cls._reduced_motion_cache

        # 平台检测函数映射表
        _PLATFORM_DETECTORS: dict[str, callable] = {
            "Darwin": cls._detect_macos_reduced_motion,
            "Windows": cls._detect_windows_reduced_motion,
            "Linux": cls._detect_linux_reduced_motion,
        }

        system = platform.system()
        detector = _PLATFORM_DETECTORS.get(system)
        reduced = detector() if detector else False

        cls._reduced_motion_cache = reduced
        return reduced

    # ── 平台专用检测逻辑 ──────────────────────────────────────────

    @classmethod
    def _detect_macos_reduced_motion(cls) -> bool:
        """macOS: 通过 QStyle.SH_ReducedAnimation 检测"""
        try:
            from PySide6.QtGui import QGuiApplication
            app = QGuiApplication.instance()
            if app:
                # QStyle.SH_ReducedAnimation = 44
                return app.style().styleHint(44) == 1
        except (RuntimeError, AttributeError, TypeError) as e:
            logger.warning("macOS reduced motion detection failed: %s", e)
        return False

    @classmethod
    def _detect_windows_reduced_motion(cls) -> bool:
        """Windows: 检查 EaseOfAccess ShowAnimation 注册表项"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Ease of Access Details",
                0
            )
            # "Show animation" DWORD: 1 = on, 0 = off
            value, _ = winreg.QueryValueEx(key, "ShowAnimation")
            reduced = value == 0
            winreg.CloseKey(key)
            return reduced
        except (OSError, FileNotFoundError) as e:
            logger.warning("Windows reduced motion detection failed: %s", e)
        return False

    @classmethod
    def _detect_linux_reduced_motion(cls) -> bool:
        """Linux: 检查 GNOME gtk-enable-animations / KDE AnimationSpeedMultiplier"""
        # GNOME GTK
        try:
            gtk_settings = QSettings(
                "org.gnome.desktop.interface",
                QSettings.Format.NativeFormat
            )
            if not gtk_settings.value("enable-animations", True, bool):
                return True
        except (TypeError, RuntimeError) as e:
            logger.warning("Linux GTK reduced motion detection failed: %s", e)

        # KDE
        try:
            kwin_settings = QSettings(
                "KDE Animation Speed",
                QSettings.Format.NativeFormat
            )
            return kwin_settings.value("AnimationSpeedMultiplier", 1.0) == 0.0
        except (TypeError, RuntimeError) as e:
            logger.warning("Linux KDE reduced motion detection failed: %s", e)
        return False

    @classmethod
    def _get_reduced_duration(cls, duration: int) -> int:
        """根据减少动画偏好返回合适的时长

        Args:
            duration: 原始动画时长(毫秒)

        Returns:
            减少后的时长（通常为 1-10ms，保持过渡感但几乎无动画）
        """
        if cls._prefers_reduced_motion():
            return min(duration // 30, 10)  # 最多 10ms
        return duration

    @staticmethod
    def fade_in(widget: QWidget, duration: int = 300, easing: QEasingCurve.Type = QEasingCurve.Type.InOutQuad):
        """淡入动画

        当系统启用了 prefers-reduced-motion 时：
        - 动画时长缩短至 10ms 以内
        - 保持最终状态，仅提供最小过渡
        """
        actual_duration = AnimationHelper._get_reduced_duration(duration)

        # 如果是 reduce motion，直接设置最终状态
        if actual_duration < 10:
            opacity = QGraphicsOpacityEffect(widget)
            opacity.setOpacity(1)
            widget.setGraphicsEffect(opacity)
            widget.show()
            return None

        opacity = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(opacity)

        animation = QPropertyAnimation(opacity, b"opacity")
        animation.setDuration(actual_duration)
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.setEasingCurve(easing)
        animation.start()

        return animation

    @staticmethod
    def fade_out(widget: QWidget, duration: int = 300, easing: QEasingCurve.Type = QEasingCurve.Type.InOutQuad,
                 hide_on_complete: bool = True):
        """淡出动画

        当系统启用了 prefers-reduced-motion 时：
        - 动画时长缩短至 10ms 以内
        """
        actual_duration = AnimationHelper._get_reduced_duration(duration)

        if actual_duration < 10:
            opacity = QGraphicsOpacityEffect(widget)
            opacity.setOpacity(0)
            widget.setGraphicsEffect(opacity)
            if hide_on_complete:
                widget.hide()
            return None

        opacity = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(opacity)

        animation = QPropertyAnimation(opacity, b"opacity")
        animation.setDuration(actual_duration)
        animation.setStartValue(1)
        animation.setEndValue(0)
        animation.setEasingCurve(easing)

        if hide_on_complete:
            animation.finished.connect(widget.hide)

        animation.start()
        return animation

    @staticmethod
    def slide_in(widget: QWidget, direction: str = "left", duration: int = 300):
        """滑入动画

        Args:
            widget: 目标控件
            direction: 方向 ("left", "right", "top", "bottom")
            duration: 动画时长(毫秒)

        当系统启用了 prefers-reduced-motion 时：
        - 直接显示在最终位置，无滑动动画
        """
        actual_duration = AnimationHelper._get_reduced_duration(duration)

        # 保存原始位置
        original_geometry = widget.geometry()

        # 设置起始位置
        _DIR_OFFSET = {
            "left": lambda g: (g.x() - g.width(), g.y()),
            "right": lambda g: (g.x() + g.width(), g.y()),
            "top": lambda g: (g.x(), g.y() - g.height()),
            "bottom": lambda g: (g.x(), g.y() + g.height()),
        }
        if direction in _DIR_OFFSET:
            nx, ny = _DIR_OFFSET[direction](original_geometry)
            widget.move(nx, ny)

        widget.show()

        # reduce motion: 直接跳到最终位置
        if actual_duration < 10:
            widget.move(original_geometry.x(), original_geometry.y())
            return None

        # 创建位置动画
        animation = QPropertyAnimation(widget, b"geometry")
        animation.setDuration(actual_duration)
        animation.setStartValue(widget.geometry())
        animation.setEndValue(original_geometry)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start()

        return animation

    @staticmethod
    def scale_in(widget: QWidget, duration: int = 250):
        """缩放入场动画

        当系统启用了 prefers-reduced-motion 时：
        - 直接显示在最终大小，无缩放动画
        """
        actual_duration = AnimationHelper._get_reduced_duration(duration)

        # 保存原始大小
        original_size = widget.size()

        # reduce motion: 直接显示最终大小
        if actual_duration < 10:
            widget.resize(original_size)
            widget.show()
            return None

        # 从小到大
        widget.resize(0, 0)
        widget.show()

        animation = QPropertyAnimation(widget, b"size")
        animation.setDuration(actual_duration)
        animation.setStartValue(widget.size())
        animation.setEndValue(original_size)
        animation.setEasingCurve(QEasingCurve.Type.OutBack)
        animation.start()

        return animation

    @staticmethod
    def pulse(widget: QWidget, duration: int = 150):
        """脉冲动画 - 用于按钮点击反馈

        当系统启用了 prefers-reduced-motion 时：
        - 跳过脉冲效果
        """
        if AnimationHelper._prefers_reduced_motion():
            return None

        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(1)
        animation.setEndValue(0.8)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.start()

        # 返回动画
        reverse = QPropertyAnimation(widget, b"windowOpacity")
        reverse.setDuration(duration)
        reverse.setStartValue(0.8)
        reverse.setEndValue(1)
        reverse.setEasingCurve(QEasingCurve.Type.InOutQuad)
        reverse.setStartTime(duration)
        reverse.start()

        return animation

    @classmethod
    def invalidate_cache(cls):
        """清除减少动画偏好的缓存

        当系统设置改变时调用此方法强制重新检测
        """
        cls._reduced_motion_cache = None


__all__ = ["AnimationHelper"]
