"""
动效工具类 - 提供各种动画效果
支持 prefers-reduced-motion 系统偏好检测
frontend-design-pro 规范 · 2026-04-13
"""

import platform
import logging
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QTimer, Qt, QSettings
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

        reduced = False

        # macOS AppleReduceMotion
        if platform.system() == "Darwin":
            try:
                # 尝试通过 Qt 访问 macOS 系统偏好
                from PySide6.QtGui import QGuiApplication
                app = QGuiApplication.instance()
                if app:
                    style = app.style()
                    # QStyle.SH_ReducedAnimation = 44
                    reduced = style.styleHint(44) == 1
            except (RuntimeError, AttributeError, TypeError) as e:
                logger.warning(f"macOS reduced motion detection failed: {e}")

        # Windows: 检查 EaseOfAccess 设置
        elif platform.system() == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"SOFTWARE\Microsoft\Ease of Access Details",
                    0
                )
                # "Show animation" DWORD value: 1 = on, 0 = off
                value, _ = winreg.QueryValueEx(key, "ShowAnimation")
                reduced = value == 0
                winreg.CloseKey(key)
            except (OSError, FileNotFoundError) as e:
                logger.warning(f"Windows reduced motion detection failed: {e}")

        # Linux: 检查 GTK 和 Qt 减少动画设置
        elif platform.system() == "Linux":
            try:
                gtk_settings = QSettings(
                    "org.gnome.desktop.interface",
                    QSettings.Format.NativeFormat
                )
                reduced = not gtk_settings.value("enable-animations", True, bool)
            except (TypeError, RuntimeError) as e:
                logger.warning("Linux GTK reduced motion detection failed: %s", e)
            if not reduced:
                try:
                    # KDE 设置
                    kwin_settings = QSettings(
                        "KDE Animation Speed",
                        QSettings.Format.NativeFormat
                    )
                    reduced = kwin_settings.value("AnimationSpeedMultiplier", 1.0) == 0.0
                except (TypeError, RuntimeError) as e:
                    logger.warning("Linux KDE reduced motion detection failed: %s", e)

        cls._reduced_motion_cache = reduced
        return reduced

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
        if direction == "left":
            widget.move(original_geometry.x() - original_geometry.width(), original_geometry.y())
        elif direction == "right":
            widget.move(original_geometry.x() + original_geometry.width(), original_geometry.y())
        elif direction == "top":
            widget.move(original_geometry.x(), original_geometry.y() - original_geometry.height())
        elif direction == "bottom":
            widget.move(original_geometry.x(), original_geometry.y() + original_geometry.height())

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

        if animation_type == "fade":
            self._fade_transition(current_widget, target_widget)
        elif animation_type == "slide":
            self._slide_transition(current_widget, target_widget)
        elif animation_type == "scale":
            self._scale_transition(current_widget, target_widget)
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
        _width = self.stacked_widget.width()

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
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

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
