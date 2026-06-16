"""
SceneFab 主窗口包

专业生产工作台布局:
- 左侧文本导航
- 顶部操作栏
- 中央生产页面
- 底部状态栏
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QWidget,
)

from scenefab.ui.theme.ds_tokens import _C, FontSizes, Radii

from .content_area import ContentArea
from .nav_components import Sidebar
from .status_bar import StatusBar
from .top_bar import TopBar


class SceneFabMainWindow(QMainWindow):
    """SceneFab 主窗口"""

    PAGE_TITLES = {
        "home": ("工作台", ""),
        "create": ("创作流程", ""),
        "assets": ("项目资产", ""),
        "settings": ("设置", ""),
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SceneFab")
        self.setMinimumSize(1200, 720)
        self._tray = None
        self._minimize_to_tray_enabled = False
        self._quitting = False
        self._setup_ui()
        self._connect_signals()
        self._apply_global_style()
        self._init_tray()

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
        self._lazy_load_pages()
        root.addWidget(self.content, 1)

        # 顶部栏
        self.topbar = TopBar("工作台")
        self.setMenuWidget(self.topbar)

        # 状态栏
        self.statusbar = StatusBar()
        self.setStatusBar(self.statusbar)  # type: ignore[arg-type]

    def _lazy_load_pages(self):
        from scenefab.ui.main.pages.assets_page import AssetsPage
        from scenefab.ui.main.pages.home_page import HomePage
        from scenefab.ui.main.pages.production_page import ProductionPage
        from scenefab.ui.main.pages.settings_page import SettingsPage

        home = HomePage()
        home.create_project.connect(lambda: self._on_navigate("create"))
        home.navigate.connect(self._on_navigate)

        production = ProductionPage()
        production.start_requested.connect(lambda: self.statusbar.set_status("创作流程已就绪"))

        assets = AssetsPage()
        assets.import_requested.connect(lambda: self.statusbar.set_status("请选择需要导入的素材"))

        self.content.add_page("home", home)
        self.content.add_page("create", production)
        self.content.add_page("assets", assets)
        self.content.add_page("settings", SettingsPage())

    def _connect_signals(self):
        self.sidebar.navigated.connect(self._on_navigate)
        self.topbar.action_triggered.connect(self._on_action)

    # ══════════════════════════════════════════════════════════════
    # 系统托盘集成
    # ══════════════════════════════════════════════════════════════

    def _init_tray(self):
        """初始化系统托盘（始终可用，是否激活由设置决定）"""
        try:
            from scenefab.ui.main.tray_manager import get_tray_manager

            self._tray = get_tray_manager()
            self._tray.show_window_requested.connect(self._restore_from_tray)
            self._tray.open_settings_requested.connect(self._open_settings_from_tray)
            self._tray.quit_requested.connect(self._quit_application)
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Tray init failed: {e}")
            self._tray = None

    def set_minimize_to_tray(self, enabled: bool):
        """设置是否启用"关闭窗口时最小化到托盘" """
        self._minimize_to_tray_enabled = bool(enabled)
        if enabled and self._tray is not None and not self._tray.is_enabled:
            self._tray.enable(self.windowTitle())
        elif not enabled and self._tray is not None and self._tray.is_enabled:
            self._tray.disable()

    def _restore_from_tray(self):
        """从托盘恢复窗口"""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _open_settings_from_tray(self):
        """从托盘菜单打开设置页"""
        self._restore_from_tray()
        self._on_navigate("settings")

    def _quit_application(self):
        """真正退出应用（绕过托盘拦截）"""
        self._quitting = True
        if self._tray is not None:
            self._tray.disable()
        self.close()
        QApplication.instance().quit()  # type: ignore[union-attr]

    def closeEvent(self, event):
        """窗口关闭事件"""
        if self._quitting:
            event.accept()
            return
        if (
            self._minimize_to_tray_enabled
            and self._tray is not None
            and self._tray.is_enabled
            and self._tray.is_available
        ):
            event.ignore()
            self.hide()
            if not hasattr(self, "_tray_hint_shown"):
                self._tray.show_notification(
                    "SceneFab",
                    "应用已最小化到系统托盘。双击图标或右键菜单可恢复窗口。",
                )
                self._tray_hint_shown = True
            return
        if self._tray is not None:
            self._tray.disable()
        event.accept()

    def _on_navigate(self, page_id: str):
        self.content.set_page(page_id)
        title, breadcrumb = self.PAGE_TITLES.get(page_id, (page_id, ""))
        self.topbar.set_title(title, breadcrumb)
        self.statusbar.set_status(f"当前: {title}")

    def navigate_to(self, page_id: str, **kwargs):
        """导航到指定页面（公共接口）"""
        self._on_navigate(page_id)

    @property
    def app(self):
        """获取 QApplication 实例"""
        return QApplication.instance()

    def show_message(self, message: str, level: str = "info"):
        """显示消息提示"""
        from PySide6.QtWidgets import QMessageBox

        if level == "error":
            QMessageBox.critical(self, "错误", message)
        elif level == "warning":
            QMessageBox.warning(self, "警告", message)
        else:
            QMessageBox.information(self, "提示", message)

    def show_loading(self, show: bool = True):
        """显示/隐藏加载状态"""
        self.statusbar.set_status("加载中..." if show else "就绪")

    def _on_action(self, action_id: str):
        if action_id == "export":
            self._on_navigate("create")
            self.statusbar.set_status("请在创作流程完成后导出成片")

    def _apply_global_style(self):
        self.setStyleSheet(f"""  # type: ignore[attr-defined]
            QMainWindow {{
                background: {_C.BG_BASE};
                outline: none;
            }}
            QToolButton#topbar_action_btn {{
                background: {_C.BG_SURFACE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
                color: {_C.TEXT_MUTED};
                font-size: {FontSizes.xs}px;
                font-weight: 600;
            }}
            QToolButton#topbar_action_btn:hover {{
                background: {_C.BG_ELEVATED};
                color: {_C.TEXT_SECONDARY};
                border-color: {_C.BORDER_DEFAULT};
            }}
            QToolTip {{
                background: {_C.BG_OVERLAY};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                padding: 6px 10px;
                font-size: {FontSizes.xs}px;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {_C.BORDER_DEFAULT};
                border-radius: 3px;
                min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {_C.BORDER_STRONG};
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
                background: {_C.BORDER_DEFAULT};
                border-radius: 3px;
                min-width: 40px;
            }}
            * {{
                selection-background-color: {_C.PRIMARY};
                selection-color: {_C.TEXT_INVERSE};
            }}
        """)


__all__ = ["SceneFabMainWindow"]
