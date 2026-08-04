"""Professional sidebar navigation for the main window."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QVBoxLayout

from app.ui.i18n import t
from app.ui.main.registry import NavItem
from app.ui.theme.ds_tokens import _C, FontSizes, Radii
from app.utils.version import get_version_string

# Translation key for the brand subtitle — referenced both at build time
# and from :py:meth:`Sidebar.retranslate` so the sidebar reflects the
# active UI language without rebuilding the widget tree.
_BRAND_SUBTITLE_KEY = "nav.brand.subtitle"


class SideNavBtn(QToolButton):
    """Sidebar navigation button."""

    def __init__(
        self,
        item_id: str,
        label: str,
        tooltip: str = "",
        *,
        label_key: str | None = None,
        tooltip_key: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._item_id = item_id
        self._label_key = label_key
        self._tooltip_key = tooltip_key
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

    def is_active(self) -> bool:
        """Tell the caller whether this button is the highlighted one.

        The main window's :py:meth:`apply_theme` rebuilds every nav
        button's stylesheet on a palette flip and needs to know the
        current active id so the new colors match the highlighted
        state. Returning the cached active flag is cheap and avoids
        reaching back into the owning :class:`Sidebar`.
        """
        return self._active

    _active: bool = False

    def _apply_style(self, active: bool):
        self._active = active
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

        self._subtitle_label = QLabel(t(_BRAND_SUBTITLE_KEY))
        self._subtitle_label.setFont(QFont("", FontSizes.xs))
        self._subtitle_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        copy_layout.addWidget(self._subtitle_label)

        brand_layout.addWidget(copy, 1)
        layout.addWidget(brand)

        nav_frame = QFrame()
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)

        self._nav_btns = {}
        for item in self._items:
            label = t(item.label_key) if item.label_key else item.label
            tooltip = t(item.tooltip_key) if item.tooltip_key else item.tooltip
            btn = SideNavBtn(
                item.id,
                label,
                tooltip,
                label_key=item.label_key,
                tooltip_key=item.tooltip_key,
            )
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

    def set_active(self, item_id: str) -> None:
        """Public hook for the main window to highlight a nav item.

        Called whenever the user navigates via menu, shortcut, deep-link,
        or any path other than clicking the sidebar itself. Idempotent
        and tolerant of unknown ids (no-op) so call sites don't need to
        check membership first.
        """
        if item_id not in self._nav_btns:
            return
        if item_id == self._current:
            return
        self._current = item_id
        self._set_active(item_id)

    def current(self) -> str | None:
        return self._current

    def _set_active(self, item_id: str):
        for _id, btn in self._nav_btns.items():
            btn.set_active(_id == item_id)

    def retranslate(self) -> None:
        """Refresh translatable text after the active language changes."""
        self._subtitle_label.setText(t(_BRAND_SUBTITLE_KEY))
        for btn in self._nav_btns.values():
            if btn._label_key is not None:
                btn.setText(t(btn._label_key))
            if btn._tooltip_key is not None:
                btn.setToolTip(t(btn._tooltip_key))
