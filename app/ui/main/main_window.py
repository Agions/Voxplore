#!/usr/bin/env python3
# -*- coding: utf-8 -*

"""
Voxplore 主窗口 — 精致现代专业布局 v4
视觉升级:
  - 渐变玻璃态侧边栏 (左侧紫色光晕)
  - 顶部工具栏磨砂效果
  - 导航项悬浮高亮 + 选中动画条
  - 阴影层次感
  - 快捷操作图标按钮组
  - 更好看的页面标题区
"""

import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QStatusBar, QFrame, QLabel, QPushButton,
    QToolButton, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect, QSize, QTimer
from PySide6.QtGui import QFont, QPainter, QBrush, QPen, QColor, QLinearGradient, QPainterPath

from ...core.application import Application
from ...core.logger import Logger
from app.ui.components.design_system import Colors


# ─── 导航项配置 ─────────────────────────────────────────────
_NAV_ITEMS = [
    ("creator",  "🏠", "创作台",    "Ctrl+N"),
    ("projects", "📁", "项目",      "Ctrl+Shift+O"),
    ("history",  "🕐", "历史",      "Ctrl+H"),
    ("settings", "⚙️", "设置",      "Ctrl+,"),
]

# ─── 快捷工具栏按钮 ────────────────────────────────────────
_TOOLBAR_ACTIONS = [
    ("new_project", "＋", "新建项目"),
    ("undo",       "↩", "撤销"),
    ("redo",       "↪", "重做"),
    ("export",     "↑", "导出"),
]


# ═══════════════════════════════════════════════════════════════
#  自定义组件
# ═══════════════════════════════════════════════════════════════

class GlowSidebar(QFrame):
    """侧边栏 — 紫色渐变玻璃态"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setObjectName("glow_sidebar")
        self._setup_style()

    def _setup_style(self):
        self.setStyleSheet("""
            #glow_sidebar {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(20, 14, 28, 0.98),
                    stop:0.5 rgba(16, 11, 22, 0.99),
                    stop:1 rgba(13, 9, 18, 1.0)
                );
                border-right: 1px solid rgba(255, 255, 255, 0.06);
            }
        """)


class SidebarTopLogo(QFrame):
    """侧边栏顶部 Logo 区域"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        # Logo 图标
        icon_label = QLabel("✦")
        icon_label.setFont(QFont("", 22))
        icon_label.setStyleSheet("color: #A78BFA;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # 文字标签
        name_layout = QVBoxLayout()
        name_layout.setSpacing(0)
        name_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("Voxplore")
        title_label.setFont(QFont("SF Pro Display", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #F1F0F5;")
        name_layout.addWidget(title_label)

        sub_label = QLabel("AI Video Studio")
        sub_label.setFont(QFont("", 9))
        sub_label.setStyleSheet("color: #6B7280; letter-spacing: 0.05em;")
        name_layout.addWidget(sub_label)

        layout.addLayout(name_layout)
        layout.addStretch()


class SidebarNavItem(QPushButton):
    """导航项 — 悬浮+选中态"""

    def __init__(self, icon: str, label: str, shortcut: str = "", parent=None):
        super().__init__(parent)
        self._icon = icon
        self._label = label
        self._shortcut = shortcut
        self._is_active = False
        self.setCheckable(True)
        self.setFixedSize(192, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{label}  {shortcut}" if shortcut else label)
        self._apply_style()

    def set_active(self, active: bool):
        self._is_active = active
        self.setChecked(active)
        self._apply_style()

    def _apply_style(self):
        if self._is_active:
            bg = """
                background: rgba(139, 92, 246, 0.15);
                border-left: 2px solid #A78BFA;
            """
            icon_color = "#A78BFA"
            text_color = "#E2E0FF"
        else:
            bg = """
                background: transparent;
                border-left: 2px solid transparent;
            """
            icon_color = "#6B7280"
            text_color = "#9CA3AF"
        self.setStyleSheet(f"""
            QPushButton {{
                {bg}
                border-radius: 0px;
                text-align: left;
                padding: 0px 14px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.05);
            }}
            QPushButton:!checked:hover {{
                background: rgba(255, 255, 255, 0.04);
                border-left: 2px solid rgba(167, 139, 250, 0.3);
            }}
        """)
        # 用 QSS 无法单独设置图标颜色，用 update 触发 paintEvent
        self._icon_color = icon_color
        self._text_color = text_color

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        # 绘制图标
        icon_rect = rect.adjusted(16, 0, -(rect.width() - 44), 0)
        icon_font = QFont("", 16)
        icon_font.setFamily("Segoe UI Emoji")
        painter.setFont(icon_font)
        painter.setPen(QColor(self._icon_color))
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._icon)

        # 绘制标签
        label_rect = rect.adjusted(44, 0, 0, 0)
        label_font = QFont("", 13)
        label_font.setWeight(QFont.Weight.Medium if self._is_active else QFont.Weight.Normal)
        painter.setFont(label_font)
        painter.setPen(QColor(self._text_color))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._label)

        # 绘制快捷键
        if self._shortcut and not self._is_active:
            shortcut_font = QFont("", 9)
            shortcut_font.setWeight(QFont.Weight.Normal)
            painter.setFont(shortcut_font)
            painter.setPen(QColor("#4B5563"))
            shortcut_rect = rect.adjusted(44, 0, -12, 0)
            fm = painter.fontMetrics()
            shortcut_text = self._shortcut
            shortcut_w = fm.horizontalAdvance(shortcut_text)
            painter.drawText(
                QRect(rect.right() - shortcut_w - 12, rect.top(), shortcut_w + 12, rect.height()),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                shortcut_text
            )


class TopToolbar(QFrame):
    """顶部工具栏 — 磨砂玻璃态"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setObjectName("top_toolbar")
        self.setStyleSheet("""
            #top_toolbar {
                background: rgba(15, 12, 20, 0.85);
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            }
        """)


class ToolbarIconBtn(QPushButton):
    """工具栏图标按钮 — 悬浮放大效果"""

    def __init__(self, icon: str, tip: str, parent=None):
        super().__init__(parent)
        self._icon = icon
        self.setFixedSize(34, 34)
        self.setToolTip(tip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                color: #9CA3AF;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
                color: #E5E7EB;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.04);
                color: #D1D5DB;
            }
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(QFont("", self._icon_to_size()))
        painter.setPen(QColor("#9CA3AF") if not self.isEnabled() else QColor("#E5E7EB"))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._icon)

    def _icon_to_size(self) -> int:
        return 16


class PageTitleBar(QFrame):
    """页面标题栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            background: {Colors.BgBase};
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        """)


class UserAvatarBtn(QPushButton):
    """用户头像按钮"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6366F1, stop:1 #8B5CF6);
                border: none;
                border-radius: 16px;
                font-size: 14px;
                color: white;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #818CF8, stop:1 #A78BFA);
            }
        """)


# ═══════════════════════════════════════════════════════════════
#  主窗口
# ═══════════════════════════════════════════════════════════════

class VoxploreWindow(QMainWindow):
    """主窗口 v4 — 精致现代专业布局"""

    status_updated = Signal(str)

    def __init__(self, application: Application):
        super().__init__()
        self.application = application
        self.logger = application.get_service_by_name("logger") or Logger("VoxploreWindow")
        self.setWindowTitle("Voxplore — AI Video Studio")
        self.resize(1440, 900)
        self.setMinimumSize(1200, 750)

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
        self.logger.info("Voxplore 主窗口初始化完成 (v4 — 精致现代布局)")

    # ─── UI 初始化 ────────────────────────────────────────────

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet(f"background: {Colors.BgBase};")

        # 主垂直布局
        main_vbox = QVBoxLayout(central)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # 顶部工具栏
        self.toolbar = TopToolbar()
        self._build_toolbar()
        main_vbox.addWidget(self.toolbar)

        # 主体区域
        body_hbox = QHBoxLayout()
        body_hbox.setContentsMargins(0, 0, 0, 0)
        body_hbox.setSpacing(0)

        # 侧边栏
        self.sidebar = GlowSidebar()
        self._build_sidebar()
        body_hbox.addWidget(self.sidebar)

        # 内容区
        content_frame = QFrame()
        content_frame.setObjectName("content_area")
        content_frame.setStyleSheet(f"""
            #content_area {{
                background: {Colors.BgBase};
            }}
        """)
        content_vbox = QVBoxLayout(content_frame)
        content_vbox.setContentsMargins(0, 0, 0, 0)
        content_vbox.setSpacing(0)

        # 页面标题栏
        self.title_bar = PageTitleBar()
        self._build_title_bar()
        content_vbox.addWidget(self.title_bar)

        # 页面堆栈
        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("page_stack")
        content_vbox.addWidget(self.page_stack, 1)

        body_hbox.addWidget(content_frame, 1)
        main_vbox.addLayout(body_hbox, 1)

        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.setFixedHeight(28)
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                color: #6B7280;
                font-size: 11px;
                background: rgba(10, 8, 14, 0.98);
                border-top: 1px solid rgba(255, 255, 255, 0.04);
            }}
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def _build_toolbar(self):
        layout = QHBoxLayout(self.toolbar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        # 左侧留白（配合侧边栏宽度偏移）
        layout.addSpacing(220 - 16)

        # 页面标题 (工具栏中央)
        self._toolbar_title = QLabel("创作台")
        self._toolbar_title.setFont(QFont("", 14, QFont.Weight.Medium))
        self._toolbar_title.setStyleSheet("color: #E5E7EB;")
        self._toolbar_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._toolbar_title)
        layout.addStretch()

        # 快捷操作按钮
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(4)
        for action_id, icon, tip in _TOOLBAR_ACTIONS:
            btn = ToolbarIconBtn(icon, tip)
            actions_layout.addWidget(btn)
            setattr(self, f"_btn_{action_id}", btn)

        layout.addLayout(actions_layout)

        # 分隔线
        sep = QFrame()
        sep.setFixedSize(1, 20)
        sep.setStyleSheet("background: rgba(255,255,255,0.08); margin: 0 8px;")
        layout.addWidget(sep)

        # 用户头像
        avatar = UserAvatarBtn()
        avatar.setToolTip("用户设置")
        layout.addWidget(avatar)

    def _build_sidebar(self):
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo 区
        logo = SidebarTopLogo()
        layout.addWidget(logo)

        # 分隔线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.05);")
        layout.addWidget(sep)

        # 导航项
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 12, 0, 12)
        nav_layout.setSpacing(2)

        self.nav_buttons = {}
        for page_id, icon, label, shortcut in _NAV_ITEMS:
            nav_item = SidebarNavItem(icon, label, shortcut)
            nav_item.clicked.connect(lambda _, p=page_id: self._navigate_to(p))
            nav_layout.addWidget(nav_item)
            self.nav_buttons[page_id] = nav_item

        nav_layout.addStretch()
        layout.addWidget(nav_container)

        # 底部: 版本 + 状态点
        bottom = QFrame()
        bottom.setFixedHeight(36)
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(16, 0, 16, 0)

        ver = QLabel("v4.0")
        ver.setFont(QFont("", 9))
        ver.setStyleSheet("color: #4B5563;")
        bottom_layout.addWidget(ver)
        bottom_layout.addStretch()

        dots = QLabel("●  ●  ●")
        dots.setFont(QFont("", 5))
        dots.setStyleSheet("color: rgba(139, 92, 246, 0.4); letter-spacing: 3px;")
        bottom_layout.addWidget(dots)

        layout.addWidget(bottom)

    def _build_title_bar(self):
        layout = QHBoxLayout(self.title_bar)
        layout.setContentsMargins(32, 0, 24, 0)
        layout.setSpacing(16)

        self.page_title_label = QLabel("创作台")
        self.page_title_label.setFont(QFont("", 20, QFont.Weight.SemiBold))
        self.page_title_label.setStyleSheet("color: #F1F0F5;")
        layout.addWidget(self.page_title_label)

        self.page_breadcrumb = QLabel("")
        self.page_breadcrumb.setFont(QFont("", 11))
        self.page_breadcrumb.setStyleSheet("color: #4B5563;")
        layout.addWidget(self.page_breadcrumb)

        layout.addStretch()

        # 页面操作按钮区
        self.page_actions_layout = QHBoxLayout()
        self.page_actions_layout.setSpacing(6)
        layout.addLayout(self.page_actions_layout)

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

        from .pages.base_page import BasePage
        for pid, label in [("projects", "项目"), ("history", "历史")]:
            page = BasePage(pid, label, self.application)
            page.create_content = lambda: None
            self.page_stack.addWidget(page)
            self._pages[pid] = page

    # ─── 导航 ─────────────────────────────────────────────────

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
        page_info = {i[0]: (i[2], j) for i, j in zip(_NAV_ITEMS, ["", "/ 项目列表", "/ 操作历史", "/ 应用设置"])}
        title, breadcrumb = page_info.get(page_id, ("", ""))
        self.page_title_label.setText(title)
        self.page_breadcrumb.setText(breadcrumb)
        self._toolbar_title.setText(title)

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

        for page, end_x, start_x in [
            (old_page, rect.left() - rect.width() // 3, rect.left()),
            (new_page, rect.left(), rect.right()),
        ]:
            anim = QPropertyAnimation(page, b"geometry")
            anim.setDuration(220)
            anim.setStartValue(QRect(start_x, 0, rect.width(), rect.height()))
            anim.setEndValue(QRect(end_x, 0, rect.width(), rect.height()))
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()
            if page is old_page:
                old_anim = anim
            else:
                new_anim = anim

        old_anim.finished.connect(lambda: old_page.setGeometry(rect) if old_page else None)
        new_anim.finished.connect(lambda: setattr(self, '_is_animating', False))

    def _on_page_activated(self):
        pass

    def show_status(self, msg: str):
        self.status_bar.showMessage(msg)


MainWindow = VoxploreWindow
