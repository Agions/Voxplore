"""Collapsible properties panel for the right side of the main window."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QLabel, QToolButton, QVBoxLayout

from scenefab.ui.theme.ds_tokens import Colors, FontSizes


class PropertiesPanel(QFrame):
    """右侧属性面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(0)  # 初始折叠
        self.setObjectName("props_panel")
        self._expanded = False
        self._content_width = 280
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #props_panel {{
                background: {Colors.BG_SURFACE};
                border-left: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # 折叠/展开按钮
        toggle_btn = QToolButton()
        toggle_btn.setObjectName("prop_toggle_btn")
        toggle_btn.setText("◀")
        toggle_btn.setToolTip("展开属性面板")
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_btn.setFixedSize(24, 24)
        toggle_btn.clicked.connect(self._toggle)
        layout.addWidget(toggle_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # 占位
        layout.addSpacing(8)

        # 内容提示
        placeholder = QLabel("选择项目后\n在此查看属性")
        placeholder.setFont(QFont("", FontSizes.sm))
        placeholder.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder)

        self._toggle_btn = toggle_btn

    def _toggle(self):
        self._expanded = not self._expanded
        target = self._content_width if self._expanded else 0
        btn_text = "▶" if self._expanded else "◀"
        self._toggle_btn.setText(btn_text)

        anim = QPropertyAnimation(self, b"maximumWidth")
        anim.setDuration(220)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.setStartValue(self.maximumWidth())
        anim.setEndValue(target)
        anim.start()
        self._width_anim_target = target

    def showEvent(self, event):
        super().showEvent(event)
        if self.maximumWidth() == 0:
            self.setFixedWidth(0)
