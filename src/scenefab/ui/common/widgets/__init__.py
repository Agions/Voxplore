#!/usr/bin/env python3
"""
通用 UI widgets — 分隔符等基础组件

Separator: 水平/垂直分隔线 (QFrame 简单封装)
历史: 原 scenefab.export.export_system 同名类已删, 本文件提供 shim.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame


class Separator(QFrame):
    """水平/垂直分隔线"""

    def __init__(
        self, orientation: Qt.Orientation = Qt.Orientation.Horizontal, parent=None
    ):
        super().__init__(parent)
        if orientation == Qt.Orientation.Horizontal:
            self.setFrameShape(QFrame.Shape.HLine)
            self.setFrameShadow(QFrame.Shadow.Sunken)
        else:
            self.setFrameShape(QFrame.Shape.VLine)
            self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setFixedHeight(
            1
        ) if orientation == Qt.Orientation.Horizontal else self.setFixedWidth(1)


__all__ = ["Separator"]
