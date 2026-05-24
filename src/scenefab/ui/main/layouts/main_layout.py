"""
主窗口布局 - 负责管理主窗口的整体布局
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout
)
from PySide6.QtCore import Qt


class MainLayout(QVBoxLayout):
    """主窗口布局"""

    def __init__(self, parent: QWidget):
        super().__init__(parent)

        self.navigation_bar = None
        self.content_widget = None

        self._setup_layout()

    def _setup_layout(self) -> None:
        """设置布局"""
        # 设置布局属性
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)

        # 导航栏区域
        self.navigation_bar_layout = QHBoxLayout()
        self.navigation_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.navigation_bar_layout.setSpacing(0)

        # 添加导航栏占位符
        self.addLayout(self.navigation_bar_layout)

        # 添加分隔线
        self.addLayout(self._create_separator())

        # 内容区域
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 添加内容区域
        self.addLayout(self.content_layout)

        # 设置内容区域为可伸缩
        self.addStretch()

    def _create_separator(self) -> QHBoxLayout:
        """创建分隔线"""
        separator_layout = QHBoxLayout()
        separator_layout.setContentsMargins(0, 0, 0, 0)
        separator_layout.setSpacing(0)

        from ...common.widgets.separator import Separator
        separator = Separator(orientation=Qt.Orientation.Horizontal)
        separator_layout.addWidget(separator)

        return separator_layout

    def set_navigation_bar(self, navigation_bar) -> None:
        """设置导航栏"""
        # 清除现有的导航栏
        while self.navigation_bar_layout.count():
            item = self.navigation_bar_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加新的导航栏
        if navigation_bar:
            self.navigation_bar_layout.addWidget(navigation_bar)
            self.navigation_bar = navigation_bar

    def set_content_widget(self, widget: QWidget) -> None:
        """设置内容窗口部件"""
        # 清除现有的内容窗口部件
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加新的内容窗口部件
        if widget:
            self.content_layout.addWidget(widget)
            self.content_widget = widget

    def get_navigation_bar(self):
        """获取导航栏"""
        return self.navigation_bar

    def get_content_widget(self) -> QWidget:
        """获取内容窗口部件"""
        return self.content_widget