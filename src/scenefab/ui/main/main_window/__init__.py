#!/usr/bin/env python3
"""
SceneFab 主窗口包

职责划分(Phase 1 重构后):
- ``MainWindow``  本类 — 仅负责装配 Sidebar / TopBar / ContentArea / StatusBar
  并把信号接起来。无业务、无路由、无托盘。
- ``PageRouter``     — 懒加载 + 页面切换 (ui/main/page_router.py)
- ``SystemTrayController`` — 托盘菜单 + 关闭拦截 (ui/main/system_tray.py)
- ``registry``       — 页面元数据 + 工厂 (ui/main/registry.py)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from scenefab.ui.main.main_window.content_area import ContentArea
from scenefab.ui.main.main_window.nav_components import Sidebar
from scenefab.ui.main.main_window.status_bar import StatusBar
from scenefab.ui.main.main_window.top_bar import TopBar
from scenefab.ui.main.page_router import PageRouter
from scenefab.ui.main.registry import NAV_ITEMS, PAGE_TITLES
from scenefab.ui.main.system_tray import SystemTrayController
from scenefab.ui.theme.ds_tokens import _C, FontSizes, Radii

if TYPE_CHECKING:
    from scenefab.application import Application


class SceneFabMainWindow(QMainWindow):
    """SceneFab 主窗口 — 装配器,只做信号路由。

    Phase 1 之后不直接持有页面、不直接读 services、不直接管托盘。
    注入的 ``application`` 实例在 Phase 2 才会被 ViewModel 消费。
    """

    def __init__(self, application: Application | None = None) -> None:
        super().__init__()
        self._application = application
        self.setWindowTitle("SceneFab")
        self.setMinimumSize(1200, 720)

        # 子组件
        self.sidebar: Sidebar
        self.content: ContentArea
        self.topbar: TopBar
        self.statusbar: StatusBar
        self.router: PageRouter
        self.tray: SystemTrayController

        self._setup_ui()
        self._connect_signals()
        self._apply_global_style()

    # ──────────────────────────────────────────────────────────
    # 装配
    # ──────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        body = QWidget()
        root_layout = QHBoxLayout(body)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar(NAV_ITEMS)
        root_layout.addWidget(self.sidebar)

        self.content = ContentArea()
        self.router = PageRouter(self.content, application=self._application, parent=self)
        root_layout.addWidget(self.content, 1)

        outer.addWidget(body, 1)

        self.topbar = TopBar("工作台")
        self.setMenuWidget(self.topbar)

        self.statusbar = StatusBar()
        outer.addWidget(self.statusbar)

        self.tray = SystemTrayController(self)

    def _connect_signals(self) -> None:
        self.sidebar.navigated.connect(self._on_navigate)
        self.router.page_changed.connect(self._on_page_changed)
        self.topbar.action_triggered.connect(self._on_action)
        self.tray.show_window_requested.connect(self._restore_from_tray)
        self.tray.open_settings_requested.connect(self._open_settings_from_tray)
        self.tray.quit_requested.connect(self._quit_application)

    def _apply_global_style(self) -> None:
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
            QTooltip {{
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

    # ──────────────────────────────────────────────────────────
    # 路由 + 动作
    # ──────────────────────────────────────────────────────────

    def _on_navigate(self, page_id: str) -> None:
        self.router.navigate(page_id)

    def _on_page_changed(self, page_id: str) -> None:
        spec = PAGE_TITLES.get(page_id)
        if spec is None:
            return
        self.topbar.set_title(spec.title, spec.breadcrumb)
        self.statusbar.set_status(f"当前: {spec.title}")

    def navigate_to(self, page_id: str, **_kwargs: object) -> None:
        """公共导航接口(供其他模块从外部跳转)。"""
        self._on_navigate(page_id)

    def _on_action(self, action_id: str) -> None:
        if action_id == "export":
            self._on_navigate("create")
            self.statusbar.set_status("请在创作流程完成后导出成片")

    # ──────────────────────────────────────────────────────────
    # 托盘 / 关闭
    # ──────────────────────────────────────────────────────────

    def _restore_from_tray(self) -> None:
        self.tray.restore_from_tray(self)

    def _open_settings_from_tray(self) -> None:
        self._restore_from_tray()
        self._on_navigate("settings")

    def _quit_application(self) -> None:
        QApplication.instance().quit()  # type: ignore[union-attr]

    def set_minimize_to_tray(self, enabled: bool) -> None:
        """供 SettingsPage 调用的关闭行为开关。"""
        self.tray.set_minimize_to_tray(enabled)

    def closeEvent(self, event) -> None:
        self.tray.handle_close_event(self, event)

    # ──────────────────────────────────────────────────────────
    # 公共便利方法
    # ──────────────────────────────────────────────────────────

    @property
    def app(self) -> QApplication:
        return QApplication.instance()  # type: ignore[return-value]

    @property
    def application(self) -> Application | None:
        return self._application

    def show_message(self, message: str, level: str = "info") -> None:
        if level == "error":
            QMessageBox.critical(self, "错误", message)
        elif level == "warning":
            QMessageBox.warning(self, "警告", message)
        else:
            QMessageBox.information(self, "提示", message)

    def show_loading(self, show: bool = True) -> None:
        self.statusbar.set_status("加载中..." if show else "就绪")


__all__ = ["SceneFabMainWindow"]
