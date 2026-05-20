#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voxplore 主窗口 — 现代三栏布局 v5
设计原则:
  - 三栏布局: 侧边导航 | 主内容区 | 属性面板(可折叠)
  - 扁平化设计语言，减少视觉噪音
  - 清晰的视觉层级
  - 统一的间距和圆角系统
"""

import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QStatusBar, QFrame, QLabel, QPushButton,
    QSplitter, QToolButton, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QFont, QPainter, QColor, QBrush, QPen

from app.ui.theme.ds_tokens import Colors, FontSizes, FontWeights, Spacing, Radii, Shadows


# ═══════════════════════════════════════════════════════════════
# 导航配置
# ═══════════════════════════════════════════════════════════════

NAV_ITEMS = [
    ("home",      "主界面",    "⌂", "Alt+1"),
    ("create",    "创作台",    "＋", "Alt+2"),
    ("projects",  "项目管理",  "☰", "Alt+3"),
    ("settings",  "设置",      "⚙", "Alt+4"),
]


# ═══════════════════════════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════════════════════════

class Sidebar(QFrame):
    """左侧导航栏"""

    navigated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(64)
        self.setObjectName("sidebar")
        self._setup_style()
        self._current = "home"
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #sidebar {{
                background: {Colors.SIDEBAR_BG_TOP};
                border-right: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(4)

        # Logo
        logo = QLabel("◆")
        logo.setFont(QFont("", 20, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {Colors.PRIMARY_400}; padding: 8px;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedHeight(48)
        layout.addWidget(logo)

        layout.addSpacing(8)

        # 导航项
        self._nav_btns = {}
        for item_id, label, icon, shortcut in NAV_ITEMS:
            btn = NavButton(icon, label, shortcut)
            btn.setFixedSize(48, 48)
            btn.clicked.connect(lambda checked, i=item_id: self._on_nav(i))
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._nav_btns[item_id] = btn

        layout.addStretch()

        # 底部按钮
        theme_btn = NavButton("◑", "深色模式", "")
        theme_btn.setFixedSize(48, 48)
        layout.addWidget(theme_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addSpacing(8)

        # 版本号
        version = QLabel("v2.0")
        version.setFont(QFont("", 9))
        version.setStyleSheet(f"color: {Colors.TEXT_MUTED}; padding: 4px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        self._set_active("home")

    def _on_nav(self, item_id: str):
        self._current = item_id
        self._set_active(item_id)
        self.navigated.emit(item_id)

    def _set_active(self, item_id: str):
        for _id, btn in self._nav_btns.items():
            btn.set_active(_id == item_id)


class NavButton(QPushButton):
    """导航按钮"""

    def __init__(self, icon: str, tooltip: str, shortcut: str):
        super().__init__(icon)
        self.setToolTip(f"{tooltip}  {shortcut}" if shortcut else tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("nav_btn")
        self._is_active = False
        self._setup_style()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #nav_btn {{
                background: transparent;
                border: none;
                border-radius: {Radii.base};
                color: {Colors.TEXT_MUTED};
                font-size: 18px;
                padding: 8px;
            }}
            #nav_btn:hover {{
                background: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
            }}
            #nav_btn[active="true"] {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(139, 92, 246, 0.2),
                    stop:1 transparent
                );
                color: {Colors.PRIMARY_400};
                border-left: 2px solid {Colors.PRIMARY_500};
            }}
        """)

    def set_active(self, active: bool):
        self._is_active = active
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)


# ═══════════════════════════════════════════════════════════════
# 顶部工具栏
# ═══════════════════════════════════════════════════════════════

class TopBar(QFrame):
    """顶部工具栏"""

    action_triggered = Signal(str)

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self.setFixedHeight(52)
        self.setObjectName("topbar")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #topbar {{
                background: {Colors.BG_SURFACE};
                border-bottom: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # 标题
        self._title_label = QLabel(self._title or "Voxplore")
        self._title_label.setFont(QFont("", FontSizes.lg, QFont.Weight.Semibold))
        self._title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(self._title_label)

        layout.addStretch()

        # 快捷操作按钮
        actions = [
            ("undo",   "↩", "撤销"),
            ("redo",   "↪", "重做"),
            ("export", "↑", "导出"),
            ("help",   "?", "帮助"),
        ]
        for _id, icon, tip in actions:
            btn = QPushButton(icon)
            btn.setObjectName("action_btn")
            btn.setFixedSize(32, 32)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda checked, i=_id: self.action_triggered.emit(i))
            layout.addWidget(btn)

        self.setLayout(layout)

    def set_title(self, title: str):
        self._title_label.setText(title)


# ═══════════════════════════════════════════════════════════════
# 内容页面容器
# ═══════════════════════════════════════════════════════════════

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

    def set_page(self, page_id: str):
        if page_id in self._page_map:
            self._stack.setCurrentWidget(self._page_map[page_id])


# ═══════════════════════════════════════════════════════════════
# 属性面板
# ═══════════════════════════════════════════════════════════════

class PropertiesPanel(QFrame):
    """右侧属性面板（可折叠）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setObjectName("props_panel")
        self._collapsed = False
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

        # 折叠按钮
        toggle_btn = QPushButton("◀")
        toggle_btn.setFixedSize(24, 24)
        toggle_btn.clicked.connect(self._toggle)
        layout.addWidget(toggle_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # 内容区
        self._content = QScrollArea()
        self._content.setWidgetResizable(True)
        self._content.setStyleSheet("border: none;")
        layout.addWidget(self._content)

    def _toggle(self):
        self._collapsed = not self._collapsed
        animation = QPropertyAnimation(self, b"maximumWidth")
        animation.setDuration(200)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        if self._collapsed:
            animation.setStartValue(280)
            animation.setEndValue(0)
        else:
            animation.setStartValue(0)
            animation.setEndValue(280)
        animation.start()


# ═══════════════════════════════════════════════════════════════
# 状态栏
# ═══════════════════════════════════════════════════════════════

class StatusBar(QFrame):
    """底部状态栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setObjectName("statusbar")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #statusbar {{
                background: {Colors.BG_SURFACE};
                border-top: 1px solid {Colors.BORDER_SUBTLE};
                color: {Colors.TEXT_MUTED};
                font-size: {FontSizes.xs}px;
            }}
        """)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)

        self._status_label = QLabel("就绪")
        layout.addWidget(self._status_label)
        layout.addStretch()

        self._progress_label = QLabel("")
        layout.addWidget(self._progress_label)

    def set_status(self, text: str):
        self._status_label.setText(text)

    def set_progress(self, text: str):
        self._progress_label.setText(text)


# ═══════════════════════════════════════════════════════════════
# 占位页面
# ═══════════════════════════════════════════════════════════════

class PlaceholderPage(QFrame):
    """占位页面（后续实现具体页面）"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName(f"page_{title.lower()}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("◎")
        icon.setFont(QFont("", 48))
        icon.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        title_label = QLabel(title)
        title_label.setFont(QFont("", FontSizes.xxl, QFont.Weight.Semibold))
        title_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        desc = QLabel("正在开发中...")
        desc.setFont(QFont("", FontSizes.sm))
        desc.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)


# ═══════════════════════════════════════════════════════════════
# 主窗口
# ═══════════════════════════════════════════════════════════════

class VoxploreMainWindow(QMainWindow):
    """Voxplore 主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voxplore")
        self.setMinimumSize(1200, 720)
        self._setup_ui()
        self._connect_signals()
        self._load_stylesheet()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 侧边栏
        self.sidebar = Sidebar()
        root_layout.addWidget(self.sidebar)

        # 主内容区
        self.content = ContentArea()

        # 延迟导入避免循环
        from app.ui.main.pages.home_page import HomePage
        from app.ui.main.pages.settings_page import SettingsPage

        # 添加页面
        self.content.add_page("home",     HomePage())
        self.content.add_page("create",    PlaceholderPage("创作台"))
        self.content.add_page("projects",  PlaceholderPage("项目管理"))
        self.content.add_page("settings",  SettingsPage())

        root_layout.addWidget(self.content, 1)

        # 右侧属性面板
        self.props = PropertiesPanel()
        root_layout.addWidget(self.props)

        # 顶部栏
        self.topbar = TopBar("主界面")
        self.setMenuWidget(self.topbar)

        # 状态栏
        self.statusbar = StatusBar()
        self.setStatusBar(self.statusbar)

    def _connect_signals(self):
        self.sidebar.navigated.connect(self._on_navigate)

    def _on_navigate(self, page_id: str):
        self.content.set_page(page_id)
        titles = {
            "home":     "主界面",
            "create":   "创作台",
            "projects": "项目管理",
            "settings": "设置",
        }
        self.topbar.set_title(titles.get(page_id, "Voxplore"))
        self.statusbar.set_status(f"当前: {titles.get(page_id, page_id)}")

    def _load_stylesheet(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {Colors.BG_BASE};
            }}
            QPushButton {{
                font-family: inherit;
            }}
            QPushButton#action_btn {{
                background: transparent;
                border: none;
                border-radius: {Radii.sm};
                color: {Colors.TEXT_MUTED};
                font-size: 14px;
            }}
            QPushButton#action_btn:hover {{
                background: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
            }}
            QPushButton#btn_primary {{
                background: {Colors.PRIMARY_500};
                color: white;
                border: none;
                border-radius: {Radii.base};
                font-size: {FontSizes.base}px;
                font-weight: {FontWeights.Medium};
                padding: 0 16px;
            }}
            QPushButton#btn_primary:hover {{
                background: {Colors.PRIMARY_400};
            }}
            QPushButton#btn_secondary {{
                background: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radii.base};
                font-size: {FontSizes.base}px;
                padding: 0 16px;
            }}
            QPushButton#btn_secondary:hover {{
                background: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton#browse_btn {{
                background: {Colors.PRIMARY_500};
                color: white;
                border: none;
                border-radius: {Radii.base};
                font-size: {FontSizes.sm};
                font-weight: {FontWeights.Medium};
            }}
            QPushButton#browse_btn:hover {{
                background: {Colors.PRIMARY_400};
            }}
            QToolTip {{
                background: {Colors.BG_OVERLAY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                padding: 4px 8px;
                font-size: {FontSizes.xs}px;
            }}
        """)


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = VoxploreMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
