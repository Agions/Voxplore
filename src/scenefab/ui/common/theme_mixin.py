"""
ThemeAwareMixin - 消除 UI 组件中重复的 update_theme 模式

提供：
- 统一的 is_dark 状态追踪
- 模板方法 _get_theme_stylesheet(is_dark) 供子类覆写
- 常用暗/亮主题颜色常量
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


class ThemeColors:
    """暗/亮主题常用颜色常量"""

    # 背景色
    BG_DARK = "#1a1a1a"
    BG_LIGHT = "#ffffff"
    BG_SURFACE_DARK = "#242424"
    BG_SURFACE_LIGHT = "#f5f5f5"
    BG_ELEVATED_DARK = "#2a2a2a"
    BG_ELEVATED_LIGHT = "#fafafa"

    # 文字色
    TEXT_DARK = "#e8e8e8"
    TEXT_LIGHT = "#212121"
    TEXT_SECONDARY_DARK = "#a8a8a8"
    TEXT_SECONDARY_LIGHT = "#666666"
    TEXT_MUTED_DARK = "#787878"
    TEXT_MUTED_LIGHT = "#999999"

    # 边框色
    BORDER_DARK = "#3a3a3a"
    BORDER_LIGHT = "#d0d0d0"
    BORDER_SUBTLE_DARK = "#2e2e2e"
    BORDER_SUBTLE_LIGHT = "#e0e0e0"


class ThemeAwareMixin:
    """
    主题感知混入类

    用法：
        class MyWidget(QWidget, ThemeAwareMixin):
            def _get_theme_stylesheet(self, is_dark: bool) -> str:
                bg = ThemeColors.BG_DARK if is_dark else ThemeColors.BG_LIGHT
                return f"background-color: {bg};"

        widget = MyWidget()
        widget.update_theme(is_dark=True)  # 自动调用 _get_theme_stylesheet
    """

    _is_dark: bool = True

    def update_theme(self, is_dark: bool = True) -> None:
        """更新主题（子类覆写 _get_theme_stylesheet 即可）"""
        self._is_dark = is_dark
        stylesheet = self._get_theme_stylesheet(is_dark)
        if stylesheet:
            self.setStyleSheet(stylesheet)
        # 递归更新子组件
        for child in self.findChildren(QWidget):
            if hasattr(child, "update_theme") and child is not self:
                child.update_theme(is_dark)

    def _get_theme_stylesheet(self, is_dark: bool) -> str:
        """子类覆写：返回组件的 QSS 样式表"""
        return ""
