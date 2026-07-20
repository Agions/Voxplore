"""Professional sidebar navigation for the main window."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QVBoxLayout

from scenefab.ui.main.registry import NavItem
from scenefab.ui.theme.ds_tokens import _C, FontSizes, Radii
from scenefab.utils.version import get_version_string


class SideNavBtn(QToolButton):
    """Sidebar navigation button."""

    def __init__(self, item_id: str, label: str, tooltip: str = "", parent=None):
        super().__init__(parent)
        self._item_id = item_id
        self.setText(label)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("side_nav_btn")
        self.setFixedHeight(38)
        if tooltip:
            self.setToolTip(tooltip)
        self._apply_style(False)

    def _apply_style(self, active: bool):
        bg = _C.PRIMARY_LIGHTEST if active else "transparent"
        border = _C.PRIMARY if active else "transparent"
        color = _C.PRIMARY_DARKER if active else _C.TEXT_MUTED
        self.setStyleSheet(f"""
            QToolButton#side_nav_btn {{
                background: {bg};
                border: 1px solid {border};
                border-left: 3px solid {border};
                border-radius: {Radii.base};
                color: {color};
                font-size: {FontSizes.sm}px;
                font-weight: 600;
                padding: 0 13px;
                text-align: left;
            }}
            QToolButton#side_nav_btn:hover {{
                background: {_C.PRIMARY_LIGHTEST};
                color: {_C.TEXT_PRIMARY};
                border-color: {_C.BORDER_DEFAULT};
                border-left-color: {_C.PRIMARY};
            }}
        """)

    def set_active(self, active: bool):
        self._apply_style(active)


class Sidebar(QFrame):
    """Left application navigation."""

    navigated = Signal(str)

    def __init__(self, items: list[NavItem] | tuple[NavItem, ...] | None = None, parent=None):
        super().__init__(parent)
        self.setFixedWidth(188)
        self.setObjectName("sidebar")
        self._items = list(items) if items else []
        self._current = self._items[0].id if self._items else None
        self._setup_style()
        self._setup_ui()
        if self._current is not None:
            self._set_active(self._current)

    def _setup_style(self):
        self.setStyleSheet(f"""
            #sidebar {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {_C.SIDEBAR_TOP},
                    stop:0.55 {_C.SIDEBAR_MID},
                    stop:1 {_C.SIDEBAR_BOTTOM}
                );
                border-right: 1px solid {_C.BORDER_SUBTLE};
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(18)

        brand = QFrame()
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(10)

        mark = QLabel("SF")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(36, 36)
        mark.setFont(QFont("", FontSizes.sm, QFont.Weight.Bold))
        mark.setStyleSheet(f"""
            QLabel {{
                color: {_C.TEXT_INVERSE};
                border-radius: {Radii.base};
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {_C.PRIMARY},
                    stop:1 {_C.PRIMARY_DARKER}
                );
            }}
        """)
        brand_layout.addWidget(mark)

        copy = QFrame()
        copy_layout = QVBoxLayout(copy)
        copy_layout.setContentsMargins(0, 0, 0, 0)
        copy_layout.setSpacing(2)

        title = QLabel("SceneFab")
        title.setFont(QFont("", FontSizes.lg, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        copy_layout.addWidget(title)

        subtitle = QLabel("短剧解说生产台")
        subtitle.setFont(QFont("", FontSizes.xs))
        subtitle.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        copy_layout.addWidget(subtitle)

        brand_layout.addWidget(copy, 1)
        layout.addWidget(brand)

        nav_frame = QFrame()
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)

        self._nav_btns = {}
        for item in self._items:
            btn = SideNavBtn(item.id, item.label, item.tooltip)
            btn.clicked.connect(lambda checked, i=item.id: self._on_nav(i))
            nav_layout.addWidget(btn)
            self._nav_btns[item.id] = btn

        layout.addWidget(nav_frame)
        layout.addStretch()

        build = QLabel(f"v{get_version_string()}")
        build.setFont(QFont("", FontSizes.xs))
        build.setStyleSheet(f"color: {_C.TEXT_DISABLED};")
        layout.addWidget(build)

    def _on_nav(self, item_id: str):
        self._current = item_id
        self._set_active(item_id)
        self.navigated.emit(item_id)

    def _set_active(self, item_id: str):
        for _id, btn in self._nav_btns.items():
            btn.set_active(_id == item_id)
