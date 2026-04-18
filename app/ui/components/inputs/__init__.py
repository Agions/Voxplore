"""
输入组件 - SearchBox 等
"""

from typing import Optional
from PySide6.QtWidgets import QWidget, QLineEdit
from PySide6.QtCore import Signal


class MacSearchBox(QWidget):
    """搜索框"""

    search_signal = Signal(str)
    searchRequested = search_signal  # Alias for compatibility

    def __init__(self, placeholder: str = "搜索...", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.placeholder = placeholder
        self._setup_ui()

    def _setup_ui(self):
        from PySide6.QtWidgets import QVBoxLayout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.input = QLineEdit()
        self.input.setPlaceholderText(self.placeholder)
        self.input.setProperty("class", "search-input")
        self.input.textChanged.connect(self._on_text_changed)

        layout.addWidget(self.input)

    def _on_text_changed(self, text: str):
        self.search_signal.emit(text)

    def text(self) -> str:
        return self.input.text()

    def clear(self):
        self.input.clear()
