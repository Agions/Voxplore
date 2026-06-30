#!/usr/bin/env python3
"""Reusable controls shared across pages.

Widgets here are referenced by 2+ pages or have a generic "form control"
shape. Settings-only helpers stay inside their owning page.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame

from scenefab.ui.theme.ds_tokens import _C


class ToggleSwitch(QFrame):
    """Small binary setting control.

    Emits ``toggled(bool)`` when the user clicks the widget. The QSS
    responds to the ``checked`` Qt property so the same instance can
    flip visually without rebuilding the style.
    """

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(42, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("checked", checked)
        self._setup_style()

    def _setup_style(self) -> None:
        self.setStyleSheet(f"""
            QFrame {{
                background: {_C.BG_ELEVATED};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: 11px;
            }}
            QFrame[checked="true"] {{
                background: {_C.PRIMARY};
                border-color: {_C.PRIMARY};
            }}
        """)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            self.toggled.emit(self._checked)
        super().mousePressEvent(event)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        self._checked = checked
        self.setProperty("checked", checked)
        self.style().unpolish(self)
        self.style().polish(self)


__all__ = ["ToggleSwitch"]
