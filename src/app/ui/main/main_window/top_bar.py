"""Top bar component with title, breadcrumb, and action buttons."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton

from app.ui.i18n import t
from app.ui.theme.ds_tokens import _C, FontSizes

# Top-bar action: (action_id, icon, icon_key, tooltip_key)
_TOPBAR_ACTIONS = (
    ("export", "导出", "topbar.export.button", "topbar.export.tooltip"),
)


class TopBar(QFrame):
    """顶部栏：标题 + 面包屑 + 操作按钮"""

    action_triggered = Signal(str)

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        # Translation keys for the *currently displayed* title / breadcrumb.
        # ``retranslate()`` uses them to repaint the labels with the
        # active language, so a language flip in the middle of a session
        # doesn't leave stale Chinese text on the chrome.
        self._title_key: str | None = None
        self._breadcrumb_key: str | None = None
        self._breadcrumb = ""
        self.setFixedHeight(56)
        self.setObjectName("topbar")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #topbar {{
                background: {_C.BG_ELEVATED};
                border-bottom: 1px solid {_C.BORDER_SUBTLE};
            }}
        """)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 16, 0)
        layout.setSpacing(12)

        # 左侧：标题 + 面包屑
        left_layout = QHBoxLayout()
        left_layout.setSpacing(8)

        self._title_label = QLabel(self._title)
        self._title_label.setFont(
            QFont("", FontSizes.lg, QFont.Weight.DemiBold))
        self._title_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        left_layout.addWidget(self._title_label)

        # 面包屑
        self._breadcrumb_label = QLabel("")
        self._breadcrumb_label.setFont(QFont("", FontSizes.sm))
        self._breadcrumb_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        left_layout.addWidget(self._breadcrumb_label)

        layout.addLayout(left_layout, 1)

        # 右侧：操作按钮组
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(4)

        self._action_btns: dict[str, QToolButton] = {}
        for action_id, _icon, icon_key, tip_key in _TOPBAR_ACTIONS:
            btn = QToolButton()
            btn.setObjectName("topbar_action_btn")
            btn.setText(t(icon_key))
            btn.setToolTip(t(tip_key))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(52, 32)
            btn.clicked.connect(
                lambda checked, i=action_id: self.action_triggered.emit(i)
            )
            actions_layout.addWidget(btn)
            self._action_btns[action_id] = (btn, icon_key, tip_key)

        layout.addLayout(actions_layout)

    def set_title(self, title: str, breadcrumb: str = ""):
        """Update title/breadcrumb text.

        ``title_key`` and ``breadcrumb_key`` are i18n keys for the
        current values; when provided, :py:meth:`retranslate` will use
        them to refresh the chrome after a language flip. Callers that
        pass plain strings without keys (rare) still get the same
        behavior as before — the labels just stay on the language they
        were given in.
        """
        self._title_key = None
        self._breadcrumb_key = None
        self._title = title
        self._breadcrumb = breadcrumb
        self._title_label.setText(title)
        self._breadcrumb_label.setText(breadcrumb)

    def set_title_keys(
        self,
        title: str,
        breadcrumb: str = "",
        *,
        title_key: str | None = None,
        breadcrumb_key: str | None = None,
    ) -> None:
        """Update title/breadcrumb and remember the i18n keys for retranslate."""
        self._title_key = title_key
        self._breadcrumb_key = breadcrumb_key
        self._title = title
        self._breadcrumb = breadcrumb
        self._title_label.setText(title)
        self._breadcrumb_label.setText(breadcrumb)

    def retranslate(self) -> None:
        """Refresh translatable text after the active language changes."""
        for btn, icon_key, tip_key in self._action_btns.values():
            btn.setText(t(icon_key))
            btn.setToolTip(t(tip_key))
        # Refresh the title / breadcrumb only when the caller passed an
        # i18n key — without one we have no way to know which entry of
        # the catalog to fetch, and the explicit string is left intact.
        if self._title_key is not None:
            self._title_label.setText(t(self._title_key))
        if self._breadcrumb_key is not None:
            self._breadcrumb_label.setText(t(self._breadcrumb_key))
