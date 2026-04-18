"""
标签组件 - MacLabel, MacTitleLabel, MacBadge 等
"""

from typing import Optional
from PySide6.QtWidgets import QLabel, QWidget, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class MacLabel(QLabel):
    """macOS 风格标签"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None, css_class: str = "label"):
        super().__init__(text, parent)
        if css_class:
            self.setProperty("class", css_class)


class MacTitleLabel(MacLabel):
    """标题标签"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setFont(QFont("", 18, QFont.Weight.Bold))
        self.setProperty("class", "title")


class MacBadge(QLabel):
    """徽章标签"""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setProperty("class", "badge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class MacStatLabel(QWidget):
    """统计标签"""

    def __init__(self, label: str = "", value: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui(label, value)

    def _setup_ui(self, label: str, value: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.label = MacLabel(label)
        self.label.setProperty("secondary", True)
        
        self.value = MacLabel(value)
        self.value.setFont(QFont("", 14, QFont.Weight.Bold))

        layout.addWidget(self.label)
        layout.addWidget(self.value)

    def set_value(self, value: str):
        self.value.setText(value)
