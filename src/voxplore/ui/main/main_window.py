#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voxplore 主窗口 — 现代极简布局 v6
设计改进:
  - 极窄侧边栏(56px)+图标+悬浮提示
  - 顶部工具栏与页面标题融为一体
  - 内容区无边框，更沉浸
  - 属性面板滑入/滑出动画
  - 底部状态栏更轻量
  - 全局快捷键支持
"""

import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QStatusBar, QFrame, QLabel, QPushButton,
    QToolButton, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, QEasingCurve, QTimer, QRect
from PySide6.QtGui import QFont, QKeySequence, QAction

from voxplore.ui.theme.ds_tokens import Colors, FontSizes, FontWeights, Spacing, Radii, Shadows


# ═══════════════════════════════════════════════════════════════════════
# 导航配置
# ═══════════════════════════════════════════════════════════════════════

NAV_ITEMS = [
    ("home",      "主界面",   "⌂",  "Alt+1"),
    ("create",    "创作",     "＋",  "Alt+2"),
    ("projects",  "项目",     "☰",  "Alt+3"),
    ("settings",  "设置",     "⚙",  "Alt+4"),
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


# ═══════════════════════════════════════════════════════════════════════
# 顶部栏（融合标题+工具操作）
# ═══════════════════════════════════════════════════════════════════════

class TopBar(QFrame):
    """顶部栏：标题 + 面包屑 + 操作按钮"""

    action_triggered = Signal(str)

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self._breadcrumb = []
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
        layout.setContentsMargins(20, 0, 12, 0)
        layout.setSpacing(12)

        # 左侧：标题 + 面包屑
        left_layout = QHBoxLayout()
        left_layout.setSpacing(8)

        self._title_label = QLabel(self._title)
        self._title_label.setFont(QFont("", FontSizes.lg, QFont.Weight.SemiBold))
        self._title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        left_layout.addWidget(self._title_label)

        # 面包屑
        self._breadcrumb_label = QLabel("")
        self._breadcrumb_label.setFont(QFont("", FontSizes.sm))
        self._breadcrumb_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        left_layout.addWidget(self._breadcrumb_label)

        layout.addLayout(left_layout, 1)

        # 右侧：操作按钮组
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(4)

        for _id, icon, tip in [
            ("undo",   "↩", "撤销 (Ctrl+Z)"),
            ("redo",   "↪", "重做 (Ctrl+Y)"),
            ("export", "↑", "导出 (Ctrl+E)"),
            ("search", "🔍", "搜索 (Ctrl+F)"),
        ]:
            btn = QToolButton()
            btn.setObjectName("topbar_action_btn")
            btn.setText(icon)
            btn.setToolTip(tip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(32, 32)
            btn.clicked.connect(lambda checked, i=_id: self.action_triggered.emit(i))
            actions_layout.addWidget(btn)

        layout.addLayout(actions_layout)

    def set_title(self, title: str, breadcrumb: str = ""):
        self._title_label.setText(title)
        self._breadcrumb_label.setText(breadcrumb)


# ═══════════════════════════════════════════════════════════════════════
# 内容区页面栈
# ═══════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════
# 属性面板（可折叠）
# ═══════════════════════════════════════════════════════════════════════

class PropertiesPanel(QFrame):
    """右侧属性面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(0)   # 初始折叠
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


# ═══════════════════════════════════════════════════════════════════════
# 底部状态栏
# ═══════════════════════════════════════════════════════════════════════

class StatusBar(QFrame):
    """轻量状态栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setObjectName("statusbar")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #statusbar {{
                background: {Colors.BG_SURFACE};
                border-top: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)

        self._status_label = QLabel("就绪")
        self._status_label.setFont(QFont("", FontSizes.xs))
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        layout.addWidget(self._status_label)

        layout.addStretch()

        self._info_labels = QHBoxLayout()
        self._info_labels.setSpacing(16)
        layout.addLayout(self._info_labels)

    def set_status(self, text: str):
        self._status_label.setText(text)

    def add_info(self, text: str):
        lbl = QLabel(text)
        lbl.setFont(QFont("", FontSizes.xs))
        lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        self._info_labels.addWidget(lbl)

    def clear_info(self):
        while self._info_labels.count():
            item = self._info_labels.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


# ═══════════════════════════════════════════════════════════════════════
# 占位页面
# ═══════════════════════════════════════════════════════════════════════

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
        title_lbl.setFont(QFont("", FontSizes.xxl, QFont.Weight.SemiBold))
        title_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        desc_lbl = QLabel("功能开发中...")
        desc_lbl.setFont(QFont("", FontSizes.sm))
        desc_lbl.setStyleSheet(f"color: {Colors.TEXT_DISABLED};")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_lbl)


# ═══════════════════════════════════════════════════════════════════════
# 主窗口
# ═══════════════════════════════════════════════════════════════════════

class VoxploreMainWindow(QMainWindow):
    """Voxplore 主窗口"""

    # 公共信号
    navigate = Signal(str)

    PAGE_TITLES = {
        "home":     ("主界面",   ""),
        "create":   ("创作台",   ""),
        "projects": ("项目管理", ""),
        "settings": ("设置",     ""),
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voxplore")
        self.setMinimumSize(1100, 680)
        self._setup_ui()
        self._connect_signals()
        self._apply_global_style()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 侧边栏
        self.sidebar = Sidebar()
        root.addWidget(self.sidebar)

        # 主内容
        self.content = ContentArea()

        # 延迟加载页面避免循环导入
        self._lazy_load_pages()

        root.addWidget(self.content, 1)

        # 属性面板（初始隐藏）
        self.props = PropertiesPanel()
        root.addWidget(self.props)

        # 顶部栏（作为 MenuWidget）
        self.topbar = TopBar("主界面")
        self.setMenuWidget(self.topbar)

        # 状态栏
        self.statusbar = StatusBar()
        self.setStatusBar(self.statusbar)

    def _lazy_load_pages(self):
        from voxplore.ui.main.pages.home_page import HomePage
        from voxplore.ui.main.pages.settings_page import SettingsPage

        self.content.add_page("home",     HomePage())
        self.content.add_page("create",   PlaceholderPage("创作台", "＋"))
        self.content.add_page("projects", PlaceholderPage("项目管理", "☰"))
        self.content.add_page("settings",  SettingsPage())

    def _connect_signals(self):
        self.sidebar.navigated.connect(self._on_navigate)
        self.topbar.action_triggered.connect(self._on_action)

    def _on_navigate(self, page_id: str):
        self.content.set_page(page_id)
        title, breadcrumb = self.PAGE_TITLES.get(page_id, (page_id, ""))
        self.topbar.set_title(title, breadcrumb)
        self.statusbar.set_status(f"当前: {title}")

    def _on_action(self, action_id: str):
        handlers = {
            "undo": self._handle_undo,
            "redo": self._handle_redo,
            "export": self._handle_export,
            "search": self._handle_search,
        }
        handler = handlers.get(action_id)
        if handler:
            handler()
        # 未知的 action_id 静默忽略（topbar 可能发送框架级 action）

    def _handle_undo(self):
        # TODO: 实现撤销功能
        pass

    def _handle_redo(self):
        # TODO: 实现重做功能
        pass

    def _handle_export(self):
        # TODO: 实现导出功能
        pass

    def _handle_search(self):
        # TODO: 实现搜索功能
        pass

    def _apply_global_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {Colors.BG_BASE};
                outline: none;
            }}
            QToolButton#topbar_action_btn {{
                background: transparent;
                border: none;
                border-radius: {Radii.sm};
                color: {Colors.TEXT_MUTED};
                font-size: 14px;
            }}
            QToolButton#topbar_action_btn:hover {{
                background: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_SECONDARY};
            }}
            QToolButton#prop_toggle_btn {{
                background: {Colors.BG_ELEVATED};
                border: none;
                border-radius: {Radii.sm};
                color: {Colors.TEXT_MUTED};
                font-size: 12px;
            }}
            QToolButton#prop_toggle_btn:hover {{
                background: {Colors.BG_OVERLAY};
                color: {Colors.TEXT_SECONDARY};
            }}
            QToolTip {{
                background: {Colors.BG_OVERLAY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                padding: 6px 10px;
                font-size: {FontSizes.xs}px;
            }}
            /* 全局滚动条 */
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {Colors.BORDER_DEFAULT};
                border-radius: 3px;
                min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {Colors.BORDER_STRONG};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 6px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: {Colors.BORDER_DEFAULT};
                border-radius: 3px;
                min-width: 40px;
            }}
            /* 全局选择颜色 */
            * {{
                selection-background-color: {Colors.PRIMARY_DARK};
                selection-color: {Colors.TEXT_PRIMARY};
            }}
        """)


# ═══════════════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════════════

def main():
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = VoxploreMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
