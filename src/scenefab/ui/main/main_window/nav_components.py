"""Sidebar navigation components for the main window."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QLabel, QToolButton, QVBoxLayout

from scenefab.ui.theme.ds_tokens import Colors, Radii

# ═══════════════════════════════════════════════════════════════════════
# 导航配置
# ═══════════════════════════════════════════════════════════════════════

NAV_ITEMS = [
    ("home", "主界面", "⌂", "Alt+1"),
    ("create", "创作", "＋", "Alt+2"),
    ("projects", "项目", "☰", "Alt+3"),
    ("settings", "设置", "⚙", "Alt+4"),
]


# ═══════════════════════════════════════════════════════════════════════
# 侧边栏导航按钮
# ═══════════════════════════════════════════════════════════════════════


class SideNavBtn(QToolButton):
    """单个侧边栏导航按钮"""

    def __init__(self, item_id: str, icon: str, tooltip: str, parent=None):
        super().__init__(parent)
        self._item_id = item_id
        self._icon = icon
        self.setToolTip(tooltip)
        self.setText(icon)
        self.setIconSize(QSize(20, 20))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("side_nav_btn")
        self._apply_style(False)

    def _apply_style(self, active: bool):
        if active:
            self.setStyleSheet(f"""
                QToolButton#side_nav_btn {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(124, 58, 237, 0.25),
                        stop:1 rgba(124, 58, 237, 0.08)
                    );
                    border-left: 2px solid {Colors.PRIMARY_DARK};
                    color: {Colors.PRIMARY};
                    border-radius: {Radii.base};
                    padding: 10px 14px;
                    font-size: 18px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QToolButton#side_nav_btn {{
                    background: transparent;
                    border-left: 2px solid transparent;
                    color: {Colors.TEXT_MUTED};
                    border-radius: {Radii.base};
                    padding: 10px 14px;
                    font-size: 18px;
                }}
                QToolButton#side_nav_btn:hover {{
                    background: {Colors.BG_ELEVATED};
                    color: {Colors.TEXT_SECONDARY};
                }}
            """)

    def set_active(self, active: bool):
        self._apply_style(active)


# ═══════════════════════════════════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════════════════════════════════


class Sidebar(QFrame):
    """左侧极窄导航栏"""

    navigated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(56)
        self.setObjectName("sidebar")
        self._current = "home"
        self._setup_style()
        self._setup_ui()
        self._set_active("home")

    def _setup_style(self):
        self.setStyleSheet(f"""
            #sidebar {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {Colors.SIDEBAR_TOP},
                    stop:0.5 {Colors.SIDEBAR_MID},
                    stop:1 {Colors.SIDEBAR_BOTTOM}
                );
                border-right: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        # Logo
        logo_frame = QFrame()
        logo_frame.setFixedHeight(48)
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo = QLabel("◆")
        logo.setFont(QFont("", 18, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {Colors.PRIMARY};")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(logo)
        layout.addWidget(logo_frame)

        layout.addSpacing(4)

        # 导航按钮组
        nav_frame = QFrame()
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(4, 0, 4, 0)
        nav_layout.setSpacing(2)

        self._nav_btns = {}
        for item_id, label, icon, shortcut in NAV_ITEMS:
            btn = SideNavBtn(item_id, icon, f"{label}  {shortcut}")
            btn.clicked.connect(lambda checked, i=item_id: self._on_nav(i))
            nav_layout.addWidget(btn)
            self._nav_btns[item_id] = btn

        layout.addWidget(nav_frame)

        layout.addStretch()

        # 底部按钮
        bottom_frame = QFrame()
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(4, 0, 4, 0)
        bottom_layout.setSpacing(2)

        theme_btn = SideNavBtn("theme", "◑", "切换主题")
        theme_btn.setFixedSize(48, 40)
        bottom_layout.addWidget(theme_btn)

        layout.addWidget(bottom_frame)

    def _on_nav(self, item_id: str):
        self._current = item_id
        self._set_active(item_id)
        self.navigated.emit(item_id)

    def _set_active(self, item_id: str):
        for _id, btn in self._nav_btns.items():
            btn.set_active(_id == item_id)
