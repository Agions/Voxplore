#!/usr/bin/env python3
# -*- coding: utf-8 -*

"""
Voxplore 主窗口 — 现代专业工具布局 v3
REDESIGNED:
  - 顶部工具栏 (48px)
  - 左侧导航加宽至 200px (图标+文字标签)
  - 页面标题区
  - 玻璃态渐变导航
  - 保留滑入动画
"""

import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QStatusBar, QFrame, QLabel, QPushButton,
    QToolButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect, QSize
from PySide6.QtGui import QFont, QIcon, QPainter, QPixmap, QPainterPath

from ...core.application import Application
from ...core.logger import Logger
from app.ui.components.design_system import Colors


# ─── Nav Item Config ──────────────────────────────────────────
_NAV_ITEMS = [
    ("creator",  "🏠", "创作台",   "Ctrl+N"),
    ("projects", "📁", "项目",     "Ctrl+Shift+O"),
    ("history",  "🕐", "历史",     "Ctrl+H"),
    ("settings", "⚙️", "设置",     "Ctrl+,"),
]


class GlassSidebar(QFrame):
    """玻璃态侧边栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self.setObjectName("glass_sidebar")
        self.setStyleSheet(f"""
            #glass_sidebar {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {Colors.BgSurface},
                    stop:1 {Colors.BgBase}
                );
                border-right: 1px solid {Colors.BorderDefault};
            }}
        """)


class NavItem(QPushButton):
    """导航项 — 图标+文字+快捷键提示"""

    def __init__(self, icon: str, label: str, shortcut: str = "", parent=None):
        super().__init__(parent)
        self._icon = icon
        self._label = label
        self._shortcut = shortcut
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(self._style(False))
        self.setToolTip(f"{label}  {shortcut}" if shortcut else label)

    def set_active(self, active: bool):
        self.setChecked(active)
        self.setStyleSheet(self._style(active))

    def _style(self, checked: bool) -> str:
        if checked:
            bg = f"""
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.PrimarySubtle},
                    stop:1 transparent
                );
                border-left: 2px solid {Colors.Primary};
            """
        else:
            bg = "background: transparent; border-left: 2px solid transparent;"
        return f"""
            QPushButton {{
                {bg}
                border-radius: 0px;
                text-align: left;
                padding: 0px 16px;
                font-size: 13px;
                color: {Colors.TextSecondary};
            }}
            QPushButton:hover {{
                background: {Colors.BgElevated};
                color: {Colors.TextPrimary};
            }}
            QPushButton:checked {{
                background: {Colors.PrimarySubtle};
                color: {Colors.Primary};
            }}
        """

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setFont(QFont("", 16))
        # 绘制图标
        icon_rect = self.rect().adjusted(12, 0, -self.width() + 44, 0)
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._icon)
        # 绘制文字
        label_rect = self.rect().adjusted(44, 0, 0, 0)
        painter.setFont(QFont("", 13))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._label)


class VoxploreWindow(QMainWindow):
    """主窗口 v3 — 现代专业工具布局"""

    status_updated = Signal(str)

    def __init__(self, application: Application):
        super().__init__()
        self.application = application
        self.logger = application.get_service_by_name("logger") or Logger("VoxploreWindow")
        self.setWindowTitle("Voxplore — AI First-Person Video Narrator")
        self.resize(1400, 900)
        self.setMinimumSize(1100, 700)

        qss_path = os.path.join(os.path.dirname(__file__), "../theme/narrafiilm.qss")
        if os.path.exists(qss_path):
            with open(qss_path) as f:
                self.setStyleSheet(f.read())

        self._pages = {}
        self._current_page = None
        self._is_animating = False
        self._init_ui()
        self._load_pages()
        self._navigate_to("creator")
        self.logger.info("Voxplore 主窗口初始化完成 (v3 — 现代布局)")

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet(f"background: {Colors.BgBase};")

        # ── 主垂直布局 ──────────────────────────────────────
        main_vbox = QVBoxLayout(central)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # ── 顶部工具栏 ──────────────────────────────────────
        self._build_top_bar(main_vbox)

        # ── 主体区域（导航 + 内容）──────────────────────────
        body_hbox = QHBoxLayout()
        body_hbox.setContentsMargins(0, 0, 0, 0)
        body_hbox.setSpacing(0)

        # 左侧导航栏
        self.sidebar = GlassSidebar()
        self._build_nav()
        body_hbox.addWidget(self.sidebar)

        # 右侧内容区
        content_frame = QFrame()
        content_frame.setObjectName("content_frame")
        content_frame.setStyleSheet(f"""
            #content_frame {{
                background: {Colors.BgBase};
            }}
        """)
        content_vbox = QVBoxLayout(content_frame)
        content_vbox.setContentsMargins(0, 0, 0, 0)
        content_vbox.setSpacing(0)

        # 页面标题栏
        self.page_title_bar = QFrame()
        self.page_title_bar.setFixedHeight(52)
        self.page_title_bar.setStyleSheet(f"""
            background: {Colors.BgBase};
            border-bottom: 1px solid {Colors.BorderDefault};
        """)
        title_bar_layout = QHBoxLayout(self.page_title_bar)
        title_bar_layout.setContentsMargins(24, 0, 24, 0)
        title_bar_layout.setSpacing(12)

        self.page_title_label = QLabel("创作台")
        self.page_title_label.setFont(QFont("", 18, QFont.Weight.Bold))
        self.page_title_label.setStyleSheet(f"color: {Colors.TextPrimary};")
        title_bar_layout.addWidget(self.page_title_label)
        title_bar_layout.addStretch()

        # 页面描述
        self.page_desc_label = QLabel("")
        self.page_desc_label.setFont(QFont("", 12))
        self.page_desc_label.setStyleSheet(f"color: {Colors.TextMuted};")
        title_bar_layout.addWidget(self.page_desc_label)

        content_vbox.addWidget(self.page_title_bar)

        # 页面堆栈
        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("page_stack")
        content_vbox.addWidget(self.page_stack, 1)

        body_hbox.addWidget(content_frame, 1)
        main_vbox.addLayout(body_hbox, 1)

        # ── 状态栏 ─────────────────────────────────────────
        self.status_bar = QStatusBar()
        self.status_bar.setFixedHeight(26)
        self.status_bar.setStyleSheet(
            f"QStatusBar {{ color: {Colors.TextMuted}; font-size: 11px; background: {Colors.BgBase}; border-top: 1px solid {Colors.BorderDefault}; }}"
        )
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def _build_top_bar(self, parent_layout: QVBoxLayout):
        """顶部工具栏"""
        toolbar = QFrame()
        toolbar.setFixedHeight(48)
        toolbar.setObjectName("top_toolbar")
        toolbar.setStyleSheet(f"""
            #top_toolbar {{
                background: {Colors.BgSurface};
                border-bottom: 1px solid {Colors.BorderDefault};
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 0, 16, 0)
        toolbar_layout.setSpacing(12)

        # Logo 区
        logo_layout = QHBoxLayout()
        logo_layout.setSpacing(8)
        logo_icon = QLabel("🎬")
        logo_icon.setFont(QFont("", 18))
        logo_text = QLabel("Voxplore")
        logo_text.setFont(QFont("", 13, QFont.Weight.Bold))
        logo_text.setStyleSheet(f"color: {Colors.Primary};")
        logo_layout.addWidget(logo_icon)
        logo_layout.addWidget(logo_text)
        toolbar_layout.addLayout(logo_layout)

        toolbar_layout.addStretch()

        # 快捷操作按钮
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(4)

        self._toolbar_buttons = {}
        toolbar_actions = [
            ("new_project", "✏️", "新建项目"),
            ("undo", "↩️", "撤销"),
            ("redo", "↪️", "重做"),
            ("export", "📤", "导出"),
        ]
        for action_id, icon, tip in toolbar_actions:
            btn = QPushButton(icon)
            btn.setObjectName(f"toolbar_btn_{action_id}")
            btn.setFixedSize(36, 36)
            btn.setToolTip(tip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 8px;
                    font-size: 16px;
                }}
                QPushButton:hover {{
                    background: {Colors.BgElevated};
                }}
            """)
            actions_layout.addWidget(btn)
            self._toolbar_buttons[action_id] = btn

        toolbar_layout.addLayout(actions_layout)

        # 用户头像区
        avatar_btn = QPushButton("👤")
        avatar_btn.setFixedSize(36, 36)
        avatar_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.PrimarySubtle};
                border: none;
                border-radius: 18px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background: {Colors.Primary};
            }}
        """)
        avatar_btn.setToolTip("用户设置")
        toolbar_layout.addWidget(avatar_btn)

        parent_layout.addWidget(toolbar)

    def _build_nav(self):
        """构建左侧导航"""
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(0)

        # Logo 区域
        logo_area = QFrame()
        logo_area.setFixedHeight(60)
        logo_layout = QVBoxLayout(logo_area)
        logo_layout.setContentsMargins(16, 8, 16, 8)
        logo_layout.setSpacing(2)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        logo_icon = QLabel("🎬")
        logo_icon.setFont(QFont("", 24))
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(logo_icon)

        logo_text = QLabel("Voxplore")
        logo_text.setFont(QFont("", 10, QFont.Weight.Bold))
        logo_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_text.setStyleSheet(f"color: {Colors.TextMuted}; letter-spacing: 0.1em;")
        logo_layout.addWidget(logo_text)

        layout.addWidget(logo_area)
        layout.addSpacing(8)

        # 分隔线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {Colors.BorderDefault}; margin: 0 12px;")
        layout.addWidget(sep)
        layout.addSpacing(12)

        # 导航项
        self.nav_buttons = {}
        for page_id, icon, label, shortcut in _NAV_ITEMS:
            nav_item = NavItem(icon, label, shortcut)
            nav_item.clicked.connect(lambda _, p=page_id: self._navigate_to(p))
            layout.addWidget(nav_item)
            self.nav_buttons[page_id] = nav_item

        layout.addStretch()

        # 版本信息
        ver_layout = QHBoxLayout()
        ver_layout.setContentsMargins(16, 0, 16, 0)
        ver_layout.setSpacing(8)
        ver = QLabel("v3.3")
        ver.setFont(QFont("", 9))
        ver.setStyleSheet(f"color: {Colors.TextMuted};")
        ver_layout.addWidget(ver)
        ver_layout.addStretch()
        dots = QLabel("● ●")
        dots.setFont(QFont("", 6))
        dots.setStyleSheet(f"color: {Colors.BorderDefault}; letter-spacing: 4px;")
        ver_layout.addWidget(dots)
        layout.addLayout(ver_layout)

    def _load_pages(self):
        from .pages.creation_wizard_page import CreationWizardPage
        creator = CreationWizardPage("creator", "创作台", self.application)
        creator.create_content()
        creator.page_activated.connect(self._on_page_activated)
        self.page_stack.addWidget(creator)
        self._pages["creator"] = creator

        from .pages.settings_page import SettingsPage
        settings = SettingsPage("settings", "设置", self.application)
        settings.create_content()
        settings.page_activated.connect(self._on_page_activated)
        self.page_stack.addWidget(settings)
        self._pages["settings"] = settings

        # Projects 页面占位（后续实现）
        from .pages.base_page import BasePage
        projects = BasePage("projects", "项目", self.application)
        projects.create_content = lambda: None  # 临时空实现
        self.page_stack.addWidget(projects)
        self._pages["projects"] = projects

        # History 页面占位（后续实现）
        history = BasePage("history", "历史", self.application)
        history.create_content = lambda: None
        self.page_stack.addWidget(history)
        self._pages["history"] = history

    def _navigate_to(self, page_id: str):
        if page_id not in self._pages or self._is_animating or page_id == self._current_page:
            return

        # 更新导航选中态
        for pid, btn in self.nav_buttons.items():
            btn.set_active(pid == page_id)

        self._is_animating = True
        old_page = self._pages.get(self._current_page)
        new_page = self._pages[page_id]
        rect = self.page_stack.geometry()

        # 更新标题
        self.page_title_label.setText(_NAV_ITEMS[[i[0] for i in _NAV_ITEMS].index(page_id)][2])
        page_descs = {
            "creator": "创建和管理你的视频创作",
            "projects": "浏览和管理所有项目",
            "history": "查看历史操作记录",
            "settings": "配置应用偏好设置",
        }
        self.page_desc_label.setText(page_descs.get(page_id, ""))

        if rect.isNull() or rect.width() == 0:
            new_page.setGeometry(rect)
            self.page_stack.setCurrentWidget(new_page)
            self._is_animating = False
        else:
            new_page.setGeometry(rect.right(), 0, rect.width(), rect.height())
            self.page_stack.setCurrentWidget(new_page)
            self._slide_animation(old_page, new_page, rect)

        self._current_page = page_id
        if hasattr(new_page, 'activate'):
            new_page.activate()

    def _slide_animation(self, old_page, new_page, rect):
        if old_page is None:
            new_page.setGeometry(rect)
            self._is_animating = False
            return
        old_anim = QPropertyAnimation(old_page, b"geometry")
        old_anim.setDuration(250)
        old_anim.setStartValue(rect)
        old_anim.setEndValue(QRect(rect.left() - rect.width() // 2, 0, rect.width(), rect.height()))
        old_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        new_anim = QPropertyAnimation(new_page, b"geometry")
        new_anim.setDuration(250)
        new_anim.setStartValue(QRect(rect.right(), 0, rect.width(), rect.height()))
        new_anim.setEndValue(rect)
        new_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        old_anim.start()
        new_anim.start()
        old_anim.finished.connect(lambda: old_page.setGeometry(rect) if old_page else None)
        new_anim.finished.connect(lambda: setattr(self, '_is_animating', False))

    def _on_page_activated(self):
        pass

    def show_status(self, msg: str):
        self.status_bar.showMessage(msg)


MainWindow = VoxploreWindow
