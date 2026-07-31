#!/usr/bin/env python3
"""Reusable controls shared across pages.

Widgets here are referenced by 2+ pages or have a generic "form control"
shape. Settings-only helpers stay inside their owning page.
"""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QFrame

from app.ui.theme.ds_tokens import _C


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


class ComboBox(QComboBox):
    """QComboBox with a thin chevron indicator that rotates on open.

    Drop-in replacement for ``QComboBox``. Hides the native arrow and
    paints a 1.6px round-cap chevron instead; the chevron rotates 180°
    with an eased 180ms transition when the popup opens/closes, and
    deepens on hover/focus — matching the scene-fab design language.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._arrow_angle = 0.0
        self._arrow_anim = QPropertyAnimation(self, b"arrowAngle", self)
        self._arrow_anim.setDuration(180)
        self._arrow_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        # Hide the native arrow; this widget paints its own chevron in
        # paintEvent so there is never a double indicator.
        self.setStyleSheet(
            "QComboBox::down-arrow { image: none; width: 0; height: 0; }")

    def _get_arrow_angle(self) -> float:
        return self._arrow_angle

    def _set_arrow_angle(self, value: float) -> None:
        self._arrow_angle = value
        self.update()

    arrowAngle = Property(float, _get_arrow_angle, _set_arrow_angle)

    def showPopup(self) -> None:
        self._animate_arrow(180.0)
        super().showPopup()

    def hidePopup(self) -> None:
        self._animate_arrow(0.0)
        super().hidePopup()

    def _animate_arrow(self, target: float) -> None:
        self._arrow_anim.stop()
        self._arrow_anim.setStartValue(self._arrow_angle)
        self._arrow_anim.setEndValue(target)
        self._arrow_anim.start()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = self.rect()
            center_x = rect.width() - 13
            center_y = rect.height() / 2
            active = self.underMouse() or self.hasFocus() or self._arrow_angle > 90
            color = _C.TEXT_SECONDARY if active else _C.TEXT_MUTED
            pen = QPen(QColor(color))
            pen.setWidthF(1.6)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.save()
            painter.translate(center_x, center_y)
            painter.rotate(self._arrow_angle)
            r, h = 3.2, 3.2
            painter.drawLine(QPointF(-r, -h), QPointF(0.0, h))
            painter.drawLine(QPointF(0.0, h), QPointF(r, -h))
            painter.restore()
        finally:
            if painter.isActive():
                painter.end()


__all__ = ["ComboBox", "ToggleSwitch"]
