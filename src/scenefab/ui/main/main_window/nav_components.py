"""Professional sidebar navigation for the main window."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QLabel, QToolButton, QVBoxLayout

from scenefab.ui.theme.ds_tokens import _C, FontSizes, Radii
from scenefab.utils.version import get_version_string

NAV_ITEMS = [
    ("home", "工作台"),
    ("create", "创作流程"),
    ("assets", "项目资产"),
    ("settings", "系统设置"),
]


class SideNavBtn(QToolButton):
    """Sidebar navigation button."""

    def __init__(self, item_id: str, label: str, parent=None):
        super().__init__(parent)
        self._item_id = item_id
        self.setText(label)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("side_nav_btn")
        self.setFixedHeight(38)
        self._apply_style(False)

    def _apply_style(self, active: bool):
        bg = _C.BG_ELEVATED if active else "transparent"
        border = _C.PRIMARY if active else "transparent"
        color = _C.TEXT_PRIMARY if active else _C.TEXT_MUTED
        self.setStyleSheet(f"""
            QToolButton#side_nav_btn {{
                background: {bg};
                border: none;
                border-left: 3px solid {border};
                border-radius: {Radii.sm};
                color: {color};
                font-size: {FontSizes.sm}px;
                font-weight: 600;
                padding: 0 12px;
                text-align: left;
            }}
            QToolButton#side_nav_btn:hover {{
                background: {_C.BG_ELEVATED};
                color: {_C.TEXT_PRIMARY};
            }}
        """)

    def set_active(self, active: bool):
        self._apply_style(active)


class Sidebar(QFrame):
    """Left application navigation."""

    navigated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(188)
        self.setObjectName("sidebar")
        self._current = "home"
        self._setup_style()
        self._setup_ui()
        self._set_active("home")

    def _setup_style(self):
        self.setStyleSheet(f"""
            #sidebar {{
                background: {_C.BG_SURFACE};
                border-right: 1px solid {_C.BORDER_SUBTLE};
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(18)

        brand = QFrame()
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(3)

        title = QLabel("SceneFab")
        title.setFont(QFont("", FontSizes.lg, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        brand_layout.addWidget(title)

        subtitle = QLabel("短剧解说生产台")
        subtitle.setFont(QFont("", FontSizes.xs))
        subtitle.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        brand_layout.addWidget(subtitle)
        layout.addWidget(brand)

        nav_frame = QFrame()
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)

        self._nav_btns = {}
        for item_id, label in NAV_ITEMS:
            btn = SideNavBtn(item_id, label)
            btn.clicked.connect(lambda checked, i=item_id: self._on_nav(i))
            nav_layout.addWidget(btn)
            self._nav_btns[item_id] = btn

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
