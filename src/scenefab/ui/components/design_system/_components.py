#!/usr/bin/env python3

"""
SceneFab 组件封装

基于 QPushButton/QLabel/QFrame 等基础控件的 SceneFab 设计系统组件实现。
历史：原位于 scenefab.ui.components.design_system，Phase 3 重构中
拆分为独立模块以隔离组件定义职责。
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGraphicsOpacityEffect
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QWidget,
)

from scenefab.ui.theme.animation import AnimationHelper

from ._style_generator import StyleSheet
from ._tokens import Colors


# ─── 组件封装 ──────────────────────────────────────────────
class CFButton(QPushButton):
    """
    SceneFab 按钮 — 支持多变体

    用法：
        btn = CFButton("保存", variant="primary")
        btn = CFButton("取消", variant="secondary")
        btn = CFButton("删除", variant="danger")
    """

    def __init__(
        self,
        text: str = "",
        variant: str = "primary",
        icon: str = "",
        parent=None,
    ):
        super().__init__(text, parent)
        self.setStyleSheet(StyleSheet.button(variant))
        if icon:
            self.setText(f"{icon} {text}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class CFLabel(QLabel):
    """
    SceneFab 标签

    用法：
        lbl = CFLabel("标题")
        lbl = CFLabel("次要文字", secondary=True)
        lbl = CFLabel("辅助说明", muted=True)
    """

    def __init__(self, text: str = "", secondary: bool = False, muted: bool = False, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(StyleSheet.label(secondary, muted))


class CFCard(QFrame):
    """
    SceneFab 卡片

    用法：
        card = CFCard()
        card = CFCard(elevated=True)  # 带阴影
    """

    def __init__(self, elevated: bool = False, parent=None):
        super().__init__(parent)
        self.setStyleSheet(StyleSheet.card(elevated))


class CFPanel(QWidget):
    """SceneFab 面板"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(StyleSheet.panel())


class CFInput(QLineEdit):
    """
    SceneFab 输入框

    用法：
        input = CFInput(placeholder="请输入...")
        input = CFInput(placeholder="邮箱", error=True)
    """

    def __init__(self, placeholder: str = "", error: bool = False, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet(StyleSheet.input(error))


class CFProgressBar(QProgressBar):
    """SceneFab 进度条"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(StyleSheet.progress_bar())


class CFNavButton(CFButton):
    """
    SceneFab 导航按钮 — 支持选中状态

    用法：
        nav = CFNavButton("首页", icon="🏠", selected=True)
        nav.set_selected(False)
    """

    def __init__(self, text: str = "", icon: str = "", selected: bool = False, parent=None):
        super().__init__(text, variant="ghost", parent=parent)
        self.selected = selected
        if icon:
            self.setText(f"{icon} {text}")
        self._update_style()

    def _update_style(self):
        self.setStyleSheet(StyleSheet.nav_button(self.selected))

    def set_selected(self, selected: bool):
        self.selected = selected
        self._update_style()


# ─── Toast 通知 ────────────────────────────────────────────
class CFToastNotification(QFrame):
    """
    SceneFab Toast 通知组件

    用法：
        toast = CFToastNotification("操作成功", type="success")
        toast.show()

        # 自动消失（默认 3 秒）
        toast = CFToastNotification("文件已保存", type="info", duration=5000)

        # 带操作按钮
        toast = CFToastNotification("确定要删除吗？", type="warning")
        toast.add_action("撤销", lambda: print("撤销"))

    类型：success / warning / error / info
    """

    _active_toasts = []  # 追踪所有活跃的 toast

    def __init__(
        self,
        message: str,
        type: str = "info",
        duration: int = 3000,
        parent=None,
    ):
        super().__init__(parent)
        self.message = message
        self.type = type
        self.duration = duration

        self._setup_ui()
        self._apply_style()
        CFToastNotification._active_toasts.append(self)

    def _setup_ui(self):
        """构建 UI 结构"""
        self._is_animating = False
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(360)
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 图标
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        layout.addWidget(self.icon_label)

        # 消息
        self.message_label = QLabel(self.message)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.message_label, 1)

        # 关闭按钮
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.hide)
        layout.addWidget(self.close_btn)

    def _apply_style(self):
        """应用样式"""
        colors = {
            "success": (Colors.Success, Colors.SuccessSubtle, "✓"),
            "warning": (Colors.Warning, Colors.WarningSubtle, "⚠"),
            "error": (Colors.Error, Colors.ErrorSubtle, "✕"),
            "info": (Colors.Info, Colors.Info, "ℹ"),
        }
        fg_color, bg_subtle, icon = colors.get(self.type, colors["info"])

        self.icon_label.setText(f"<span style='color:{fg_color}; font-size:16px;'>{icon}</span>")
        self.message_label.setStyleSheet(
            f"color: {Colors.TextPrimary}; font-size: 14px; background: transparent; border: none;"
        )
        self.setStyleSheet(f"""
            QFrame {{
                background: {Colors.BgElevated};
                border: 1px solid {Colors.BorderDefault};
                border-left: 3px solid {fg_color};
                border-radius: 8px;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                color: {Colors.TextMuted};
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {Colors.TextPrimary};
            }}
        """)

    def add_action(self, text: str, callback):
        """添加操作按钮"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        btn.clicked.connect(self.hide)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.Primary} / 0.15;
                border: none;
                border-radius: 4px;
                color: {Colors.Primary};
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {Colors.Primary} / 0.25;
            }}
        """)
        self.layout().addWidget(btn)

    def show(self):
        """显示通知并自动隐藏"""
        # 初始化透明效果
        opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(opacity)
        opacity.setOpacity(0)
        self.show()

        # 动画显示
        AnimationHelper.fade_in(self, duration=200)

        # 自动隐藏
        if self.duration > 0:
            QTimer.singleShot(self.duration, self.hide)

    def hide(self):
        """隐藏通知"""
        if self._is_animating:
            return
        self._is_animating = True

        def _on_complete():
            super().hide()
            if self in CFToastNotification._active_toasts:
                CFToastNotification._active_toasts.remove(self)
            self._is_animating = False

        self._is_animating = False
        AnimationHelper.fade_out(self, duration=200, hide_on_complete=False)

        # 延迟关闭
        QTimer.singleShot(200, _on_complete)


__all__ = [
    "CFButton",
    "CFLabel",
    "CFCard",
    "CFPanel",
    "CFInput",
    "CFProgressBar",
    "CFNavButton",
    "CFToastNotification",
]
