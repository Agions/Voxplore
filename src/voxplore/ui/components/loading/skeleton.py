#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
骨架屏组件 (Skeleton Screen)
用于内容加载时显示的占位符效果
"""

from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QLinearGradient, QColor


class ShimmerEffect(QWidget):
    """骨架屏闪烁效果"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._opacity = 0.3
        self._gradient_pos = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 启动动画
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_gradient)
        self._timer.start(30)

    def _update_gradient(self):
        self._gradient_pos += 0.02
        if self._gradient_pos > 1.5:
            self._gradient_pos = -0.5
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 创建渐变
        gradient = QLinearGradient(
            self.width() * self._gradient_pos, 0,
            self.width() * (self._gradient_pos + 0.5), 0
        )

        base_color = QColor(48, 54, 61)
        highlight_color = QColor(99, 102, 241)

        gradient.setColorAt(0, base_color)
        gradient.setColorAt(0.3, highlight_color)
        gradient.setColorAt(0.5, base_color)
        gradient.setColorAt(1, base_color)

        painter.fillRect(self.rect(), gradient)


class SkeletonWidget(QFrame):
    """
    骨架屏通用组件
    模拟内容加载状态的占位符
    """

    def __init__(self, width=None, height=20, parent=None):
        super().__init__(parent)
        self._width = width
        self._height = height
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("skeleton")
        if self._width:
            self.setFixedWidth(self._width)
        self.setFixedHeight(self._height)

        # 添加闪烁效果
        self._shimmer = ShimmerEffect(self)
        self._shimmer.setGeometry(self.rect())
        self._shimmer.installEventFilter(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._shimmer.setGeometry(self.rect())


class SkeletonBar(QFrame):
    """
    骨架屏条形组件
    用于模拟文本行或进度条
    """

    def __init__(self, width=None, height=16, parent=None):
        super().__init__(parent)
        self._width = width
        self._height = height
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("skeleton-bar")
        if self._width:
            self.setFixedWidth(self._width)
        self.setFixedHeight(self._height)

        # 添加闪烁效果
        self._shimmer = ShimmerEffect(self)
        self._shimmer.setGeometry(self.rect())
        self._shimmer.installEventFilter(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._shimmer.setGeometry(self.rect())


class SkeletonCircle(QFrame):
    """
    骨架屏圆形组件
    用于模拟头像或图标
    """

    def __init__(self, size=40, parent=None):
        super().__init__(parent)
        self._size = size
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("skeleton-circle")
        self.setFixedSize(self._size, self._size)

        # 添加闪烁效果
        self._shimmer = ShimmerEffect(self)
        self._shimmer.setGeometry(self.rect())
        self._shimmer.installEventFilter(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._shimmer.setGeometry(self.rect())


class SkeletonCard(QFrame):
    """
    骨架屏卡片组件
    模拟卡片布局的加载状态
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("card")
        self.setFixedHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题行：图标 + 标题
        title_layout = QHBoxLayout()
        title_layout.setSpacing(12)

        self.icon_skeleton = SkeletonCircle(40)
        title_layout.addWidget(self.icon_skeleton)

        title_text_layout = QVBoxLayout()
        title_text_layout.setSpacing(6)
        title_text_layout.addWidget(SkeletonBar(height=14))
        title_text_layout.addWidget(SkeletonBar(width=150, height=12))
        title_layout.addWidget(title_text_layout)

        layout.addLayout(title_layout)

        # 内容行
        content_layout = QHBoxLayout()
        content_layout.setSpacing(8)
        content_layout.addWidget(SkeletonBar())
        content_layout.addWidget(SkeletonBar())
        content_layout.addWidget(SkeletonBar())
        layout.addLayout(content_layout)

        # 底部行
        layout.addWidget(SkeletonBar(height=10))


class SkeletonList(QWidget):
    """
    骨架屏列表组件
    模拟列表加载状态
    """

    def __init__(self, rows=5, parent=None):
        super().__init__(parent)
        self._rows = rows
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for _ in range(self._rows):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(12)

            # 圆形图标
            row_layout.addWidget(SkeletonCircle(36))

            # 文本内容
            text_layout = QVBoxLayout()
            text_layout.setSpacing(4)
            text_layout.addWidget(SkeletonBar(height=14))
            text_layout.addWidget(SkeletonBar(width=200, height=12))
            row_layout.addWidget(text_layout)

            row_layout.addStretch()

            # 右侧操作
            row_layout.addWidget(SkeletonBar(width=60, height=24))

            layout.addLayout(row_layout)

        layout.addStretch()
