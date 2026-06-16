"""Top bar component with title, breadcrumb, and action buttons."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton

from scenefab.ui.theme.ds_tokens import _C, FontSizes


class TopBar(QFrame):
    """顶部栏：标题 + 面包屑 + 操作按钮"""

    action_triggered = Signal(str)

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self.setFixedHeight(56)
        self.setObjectName("topbar")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #topbar {{
                background: {_C.BG_SURFACE};
                border-bottom: 1px solid {_C.BORDER_SUBTLE};
            }}
        """)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 12, 0)
        layout.setSpacing(12)

        # 左侧：标题 + 面包屑
        left_layout = QHBoxLayout()
        left_layout.setSpacing(8)

        self._title_label = QLabel(self._title)
        self._title_label.setFont(QFont("", FontSizes.lg, QFont.Weight.SemiBold))  # type: ignore[attr-defined]
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

        for action_id, icon, tip in [("export", "导出", "导出成片")]:
            btn = QToolButton()
            btn.setObjectName("topbar_action_btn")
            btn.setText(icon)
            btn.setToolTip(tip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(52, 32)
            btn.clicked.connect(
                lambda checked, i=action_id: self.action_triggered.emit(i)
            )
            actions_layout.addWidget(btn)

        layout.addLayout(actions_layout)

    def set_title(self, title: str, breadcrumb: str = ""):
        self._title_label.setText(title)
        self._breadcrumb_label.setText(breadcrumb)
