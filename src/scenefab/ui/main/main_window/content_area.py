"""Main content area with stacked page views."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QStackedWidget,
    QVBoxLayout,
)

from scenefab.ui.theme.ds_tokens import _C


class ContentArea(QFrame):
    """主内容区域"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("content_area")
        self._setup_style()
        self._stack = QStackedWidget()
        self._page_map = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

    def _setup_style(self):
        self.setStyleSheet(f"""
            #content_area {{
                background: {_C.BG_BASE};
            }}
        """)

    def add_page(self, page_id: str, widget):
        widget.setObjectName(f"page_{page_id}")
        self._page_map[page_id] = widget
        self._stack.addWidget(widget)

    def set_page(self, page_id: str, animated: bool = True):
        if page_id not in self._page_map:
            return
        w = self._page_map[page_id]
        if animated and self._stack.currentWidget() != w:
            w.setWindowOpacity(0)
            self._stack.setCurrentWidget(w)
            self._fade_in(w)
        else:
            self._stack.setCurrentWidget(w)

    def _fade_in(self, widget, duration: int = 180):
        eff = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(eff)
        widget.setWindowOpacity(0)
        anim = QPropertyAnimation(eff, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        anim.start()
        widget._fade_anim = anim
