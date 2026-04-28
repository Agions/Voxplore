#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MacCard — REDESIGNED
卡片容器，统一圆角 + 边框样式，frontend-design-pro compliant
"""

from PySide6.QtWidgets import QFrame

from .common_styles import ColorPalette as CP, CardStyles


class MacCard(QFrame):
    """
    标准卡片容器

    REDESIGN:
    - 圆角: 14px (Radius.LG)
    - 背景: BG_RAISED 微渐变
    - 边框: BORDER_SUBTLE
    - Hover: 边框变主色 + translateY(-2px) + 主色阴影
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mac_card")
        self.setStyleSheet(CardStyles.DEFAULT)

    def enterEvent(self, event):
        """REDESIGN: Hover — 边框发光 + 微微上浮"""
        self.setStyleSheet(CardStyles.HOVER)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """REDESIGN: 离开恢复默认"""
        self.setStyleSheet(CardStyles.DEFAULT)
        super().leaveEvent(event)


class MacElevatedCard(QFrame):
    """
    悬浮卡片 — 用于预览/弹出层
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(CardStyles.GLASS)


class MacSection(QFrame):
    """
    区块容器 — 用于设置分组等
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {CP.BG_BASE};
                border-radius: {CP.Radius.LG};
                padding: 16px;
            }}
        """)
