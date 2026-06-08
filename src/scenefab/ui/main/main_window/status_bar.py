"""Lightweight status bar for the bottom of the main window."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from scenefab.ui.theme.ds_tokens import Colors, FontSizes


class StatusBar(QFrame):
    """轻量状态栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setObjectName("statusbar")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #statusbar {{
                background: {Colors.BG_SURFACE};
                border-top: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)

        self._status_label = QLabel("就绪")
        self._status_label.setFont(QFont("", FontSizes.xs))
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        layout.addWidget(self._status_label)

        layout.addStretch()

        self._info_labels = QHBoxLayout()
        self._info_labels.setSpacing(16)
        layout.addLayout(self._info_labels)

    def set_status(self, text: str):
        self._status_label.setText(text)

    def add_info(self, text: str):
        lbl = QLabel(text)
        lbl.setFont(QFont("", FontSizes.xs))
        lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        self._info_labels.addWidget(lbl)

    def clear_info(self):
        while self._info_labels.count():
            item = self._info_labels.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
