"""Main content area with stacked page views and placeholder pages."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
)

from scenefab.ui.theme.ds_tokens import Colors, FontSizes


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
                background: {Colors.BG_BASE};
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
            # 淡入淡出切换
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
        # 保持引用防止被 GC 回收
        widget._fade_anim = anim


class PlaceholderPage(QFrame):
    """占位页面"""

    def __init__(self, title: str, icon: str = "◎", parent=None):
        super().__init__(parent)
        self.setObjectName(f"page_{title.lower()}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("", 52))
        icon_lbl.setStyleSheet(f"color: {Colors.BORDER_STRONG};")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("", FontSizes.xxl, QFont.Weight.SemiBold))  # type: ignore[attr-defined]
        title_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        desc_lbl = QLabel("功能开发中...")
        desc_lbl.setFont(QFont("", FontSizes.sm))
        desc_lbl.setStyleSheet(f"color: {Colors.TEXT_DISABLED};")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_lbl)
