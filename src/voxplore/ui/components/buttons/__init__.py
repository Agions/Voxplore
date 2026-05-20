#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MacButton — REDESIGNED
统一按钮样式，frontend-design-pro compliant
"""

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt

from .common_styles import ColorPalette as CP, ButtonStyles


class MacButton(QPushButton):
    """
    基础按钮（一般不直接使用，用其子类）
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class MacPrimaryButton(MacButton):
    """
    主按钮 — solid fill + hover scale
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("primary_btn")
        self.setStyleSheet(ButtonStyles.PRIMARY)
        self._mouse_over = False

    def enterEvent(self, event):
        self._mouse_over = True
        self.setStyleSheet(ButtonStyles.PRIMARY_HOVER)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._mouse_over = False
        self.setStyleSheet(ButtonStyles.PRIMARY)
        super().leaveEvent(event)


class MacSecondaryButton(MacButton):
    """
    次要按钮 — transparent + border
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("secondary_btn")
        self.setStyleSheet(ButtonStyles.SECONDARY)

    def enterEvent(self, event):
        self.setStyleSheet(ButtonStyles.SECONDARY_HOVER)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(ButtonStyles.SECONDARY)
        super().leaveEvent(event)


class MacDangerButton(MacButton):
    """
    危险操作按钮 — 红色
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("danger_btn")
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {CP.ERROR};
                border: 1px solid {CP.ERROR};
                border-radius: 10px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {CP.ERROR}20;
            }}
        """)
