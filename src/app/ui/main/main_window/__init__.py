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

import logging
import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Qt, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from app.ui.i18n import get_translator, t
from app.ui.i18n.message_keys import MessageKey
from app.ui.main.main_window.assets_io import AssetsIOController
from app.ui.main.main_window.chrome import (
    NAV_CREATE,
    NAV_HOME,
    NAV_SETTINGS,
    MainWindowChrome,
)
from app.ui.main.main_window.content_area import ContentArea
from app.ui.main.main_window.drop_zone import MainWindowDropZone
from app.ui.main.main_window.exporter import ExportController
from app.ui.main.main_window.nav_components import Sidebar
from app.ui.main.main_window.production_runner import (
    DEFAULT_CONTEXT,
    DEFAULT_EMOTIONS,
    ProductionRunner,
)
from app.ui.main.main_window.project_io import ProjectIOController
from app.ui.main.main_window.status_bar import StatusBar
from app.ui.main.main_window.theme_controller import ThemeController
from app.ui.main.main_window.top_bar import TopBar
from app.ui.main.page_router import PageRouter
from app.ui.main.registry import NAV_ITEMS, PAGE_TITLES
from app.ui.main.system_tray import SystemTrayController
from app.ui.theme import ThemeAwareMixin
from app.ui.theme.ds_tokens import (
    _C,
    FontSizes,
    QSSComponents,
    Radii,
)
from app.ui.theme.theme_manager import ThemeManager
from app.ui.viewmodels import DashboardViewModel
from app.ui.viewmodels.home_viewmodel import HomePageViewModel


def _tr(key: str, *, default: str | None = None) -> str:
    """``t(key)`` 的便捷封装，未命中时返回 ``default`` 而非 ``[key]``。

    用于命令标题等「缺翻译时也要有合理 fallback」的场景，避免命令面板
    显示 ``[help.panel.title]`` 这种丑陋字面量。
    """
    text = t(key)
    if text == f"[{key}]" and default is not None:
        return default
    return text


logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from app.application import Application

# 默认视频扩展名仍保留在 main_window，因为外部 import 路径历史依赖。
_VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")


class SceneFabMainWindow(QMainWindow, ThemeAwareMixin):
    """SceneFab 主窗口 — 装配器,只做信号路由。

    Phase 1 之后不直接持有页面、不直接读 services、不直接管托盘。
    注入的 ``application`` 实例在 Phase 2 才会被 ViewModel 消费。
    """

    def __init__(self, application: Application | None = None) -> None:
        super().__init__()
        self._application = application
        self.setWindowTitle("SceneFab")
        self.setMinimumSize(1200, 720)
        self.setAcceptDrops(True)
        # macOS native look-and-feel — no-op on Windows/Linux.
        # Unified titlebar collapses the toolbar into the titlebar so
        # traffic-light buttons sit flush with the rest of the chrome.
        # DocumentMode removes the visual frame between the toolbar and
        # the content area, matching modern native macOS apps.
        self.setUnifiedTitleAndToolBarOnMac(True)
        self.setDocumentMode(True)
        self._quitting = False
        self._last_project = None
        self._theme_manager = ThemeManager(self)
        self._theme_manager.apply_persisted()

        ThemeAwareMixin.__init__(self)
        self.setStyleSheet(self.build_global_stylesheet())

        self._setup_ui()

        # 恢复窗口几何
        settings = QSettings("SceneFab", "Application")
        geometry = settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1200, 720)

        # 系统托盘控制器（必须在 _connect_signals 之前创建，
        # 后者会连接 self.tray 的信号）
        self.tray = SystemTrayController(self)

        self._connect_signals()

    def _setup_ui(self) -> None:
        # Menu bar must be built *before* setStyleSheet because the
        # QMenuBar created here participates in the global QSS.
        self.chrome = MainWindowChrome(
            self,
            on_new_project=lambda: self._on_navigate(NAV_CREATE),
            on_open_project=self._on_open_project,
            on_save_project=self._on_save_project,
            on_import_assets=self._on_import_assets,
            on_export=self._run_export,
            on_quit=self._quit_application,
            on_navigate=self._on_navigate,
            on_open_settings=lambda: self._on_navigate(NAV_SETTINGS),
            on_check_updates=self._on_check_updates,
        )
        central = QWidget()
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 顶部栏
        # Initial display title; overridden by ``_on_page_changed`` once a
        # page is mounted. Kept as a translated string for the brief moment
        # between window construction and the first navigation.
        self.topbar = TopBar(t("home.header.title"))
        outer.addWidget(self.topbar)

        body = QWidget()
        root_layout = QHBoxLayout(body)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar(NAV_ITEMS)
        root_layout.addWidget(self.sidebar)

        self.content = ContentArea()
        self.router = PageRouter(
            self.content, application=self._application, parent=self
        )
        root_layout.addWidget(self.content, 1)

        self._lazy_load_pages()

        outer.addWidget(body, 1)

        self.statusbar = StatusBar()
        outer.addWidget(self.statusbar)

        self._cancel_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._cancel_shortcut.activated.connect(self._on_cancel_production)

        # Phase 2 · 系统资源监控（1Hz psutil 采样 → system.metric 事件）
        # 和 Cmd+K 命令面板。集中安装避免污染 _setup_ui 上半部分。
        self._install_phase2_services()

        # Drop zone, production runner and exporter controllers are
        # created here so they're owned by the window and live for
        # its full lifetime.
        self.drop_zone = MainWindowDropZone(
            self,
            on_drop=lambda path: self._start_production_with_video(path),
        )
        self.production_runner = ProductionRunner(self)
        self.exporter = ExportController(
            self,
            get_project=lambda: self._last_project,
            on_no_project=lambda: QMessageBox.warning(
                self,
                t("error.export_failed"),
                t("production.dialog.no_project"),
            ),
        )
        self.exporter.exported.connect(self._on_export_succeeded)
        self.project_io = ProjectIOController(
            self,
            get_project_manager=lambda: getattr(self, "_project_manager", None),
            get_last_project=lambda: self._last_project,
            set_last_project=lambda p: self._set_last_project(p),
            get_production_page=lambda: getattr(self, "_production_page", None),
            navigate_to_create=lambda: self._on_navigate("create"),
            show_status=lambda msg: self.statusbar.set_status(msg),
            show_message=lambda msg, level: self.show_message(msg, level=level),
        )
        self.assets_io = AssetsIOController(
            self,
            get_project_manager=lambda: getattr(self, "_project_manager", None),
            get_assets_page=lambda: getattr(self, "_assets_page", None),
            show_status=lambda msg: self.statusbar.set_status(msg),
        )
        # ThemeController bridges ThemeManager → 主题主题回调注入。
        # 创建在 router 之后，apply_persisted 会在主机窗口构造期被调用。
        self.theme_ctrl = ThemeController(
            self._theme_manager,
            router=self.router,
            hook=self.apply_theme,
        )
        # ThemeController was created after the main window's QSS
        # stack, so it connects to ``palette_changed`` only once the
        # chromium is on screen. The early ``apply_persisted`` call in
        # main_window.__init__ already restored the user's mode, but
        # the persisted language hasn't been applied yet. Do that here
        # so the first frame already renders in the right language.
        self._apply_persisted_language()
        self.production_runner.step_status_changed.connect(self._on_step_status_changed)
        self.production_runner.progress_message.connect(
            self._on_production_progress_msg
        )
        self.production_runner.finished.connect(self._on_production_finished)
        self.production_runner.failed.connect(self._on_production_failed)
        self.production_runner.cancelled.connect(self._on_production_cancelled)

    def _lazy_load_pages(self):
        from app.ui.main.pages.assets_page import AssetsPage
        from app.ui.main.pages.home_page import HomePage
        from app.ui.main.pages.production_page import ProductionPage
        from app.ui.main.pages.settings_page import SettingsPage

        project_manager = None
        settings_manager = None
        if self._application is not None:
            project_manager = self._application.get_service_by_name("project_manager")
            settings_manager = self._application.get_service_by_name("settings_manager")

        # HomePageViewModel is the single source of truth for the home
        # dashboard — pages consume *_changed signals and re-read VM
        # properties instead of being poked from the outside.
        home_vm = HomePageViewModel(self._application, self)
        if self._application is not None:
            home_vm.bind()

        home = HomePage(viewmodel=home_vm)
        home.create_project.connect(lambda: self._on_navigate("create"))
        home.open_project.connect(self._on_open_project)
        home.navigate.connect(self._on_navigate)
        self._home_page = home
        self._home_vm = home_vm

        production = ProductionPage()
        production.start_requested.connect(self._on_start_production)
        production.cancel_requested.connect(self._on_cancel_production)
        self._production_page = production

        assets = AssetsPage(project_manager=project_manager)
        assets.import_requested.connect(self._on_import_assets)
        assets.navigate.connect(self._on_navigate)
        self._assets_page = assets
        self._project_manager = project_manager

        settings = SettingsPage(
            settings_manager=settings_manager,
            theme_manager=self._theme_manager,
            project_manager=project_manager,
        )
        # Keep a direct reference so the language/theme flip handlers
        # in ``_on_language_changed`` can call ``retranslate()`` without
        # walking the router's page map (the router only carries pages
        # that have actually been visited; the settings page is built
        # at startup but never registered before the user clicks it).
        self._settings_page = settings

        self.router.register_page("home", home)
        self.router.register_page("create", production)
        self.router.register_page("assets", assets)
        self.router.register_page("settings", settings)

        # 页面挂载到窗口后重新加载设置，确保托盘等窗口级状态同步
        if settings_manager is not None:
            settings.load_settings()

        # 初始进入工作台主页 (避免打开呈现空白)
        # The ``_connect_signals`` pass wires ``page_changed`` →
        # ``_on_page_changed`` which in turn pushes the topbar /
        # statusbar title for the new page. Triggering navigation here
        # would silently drop the title update because the listener
        # isn't connected yet — we instead replay the navigation once
        # the connection is in place, just below.
        self._initial_page_id = "home"

        # Phase 3 · 内嵌帮助面板 (右侧 dock + Cmd+K 中的 help.open 命令 +
        # SettingsPage 帮助中心 button 的调度)。必须放在 _settings_page
        # 之后，否则信号连接不上。
        self._install_phase3_help()

        # Phase 4 · 可观测性：注入 settings_store 门面 + 把 metrics
        # 绑到 event_bus，让 help.copy_diagnostics / audit / metrics 真正可用。
        # 必须在 _setup_ui 末尾、_connect_signals 之前调用。
        self._install_phase4_observability()

    def _connect_signals(self) -> None:
        self.sidebar.navigated.connect(self._on_navigate)
        self.router.page_changed.connect(self._on_page_changed)
        self.topbar.action_triggered.connect(self._on_action)
        self.tray.show_window_requested.connect(self._restore_from_tray)
        self.tray.open_settings_requested.connect(self._open_settings_from_tray)
        self.tray.quit_requested.connect(self._quit_application)
        # theme_ctrl 在 ThemeController.__init__ 中已自身接线
        # palette_changed 信号，所以这里不需要再手动 connect。
        # 语言变化时调度 chrome 重译所有菜单与动作文本。
        get_translator().language_changed.connect(self._on_language_changed)

        # Replay the initial navigation now that ``page_changed`` is
        # connected — without this the topbar / statusbar keep the
        # placeholder title set during ``_setup_ui`` and a later
        # language switch won't see the right ``title_key`` to refresh.
        if getattr(self, "_initial_page_id", None):
            self._on_navigate(self._initial_page_id)
            self._initial_page_id = None

    def _on_page_changed(self, page_id: str) -> None:
        spec = PAGE_TITLES.get(page_id)
        if spec is None:
            return
        title = t(spec.title_key) if spec.title_key else spec.title
        breadcrumb = t(spec.breadcrumb_key) if spec.breadcrumb_key else spec.breadcrumb
        # Forward the i18n keys so a later language flip can re-paint
        # the title/breadcrumb without re-resolving the spec.
        self.topbar.set_title_keys(
            title,
            breadcrumb,
            title_key=spec.title_key,
            breadcrumb_key=spec.breadcrumb_key,
        )
        status_key = "statusbar.current_page"
        self.statusbar.set_status(t(status_key).format(page=title), key=status_key)

    def _set_last_project(self, project: object) -> None:
        """Set the most recently produced / loaded ``MonologueProject``."""
        self._last_project = project

    def _apply_persisted_language(self) -> None:
        """Restore the persisted UI language at startup.

        The translator defaults to ``zh-CN`` (the only language baked
        into the i18n catalog bootstrap). Without this hook the very
        first frame would render in Chinese even if the user picked
        English in a previous session. Best-effort: a missing /
        unrecognised value is silently ignored so a bad config file
        cannot prevent the window from opening.
        """
        try:
            from app.config.manager import ProjectSettingsManager
            from app.ui.i18n import set_language as _set_language

            sm = None
            if self._application is not None:
                sm = self._application.get_service_by_name("settings_manager")
            if sm is None or not isinstance(sm, ProjectSettingsManager):
                return
            lang = sm.get_setting("ui.language")
            if lang:
                _set_language(str(lang))
        except Exception:  # pragma: no cover — defensive
            logger.debug("持久化语言恢复失败", exc_info=True)

    def _on_language_changed(self, language: str) -> None:
        """Re-translate every chrome-managed menu and widget."""
        # Order matters: chrome owns the QMenuBar tree; sidebar / topbar /
        # statusbar / tray own their own retranslate entry points.
        for owner_attr in (
            "chrome",
            "sidebar",
            "topbar",
            "statusbar",
            "tray",
        ):
            owner = getattr(self, owner_attr, None)
            if owner is None:
                continue
            retranslate = getattr(owner, "retranslate", None)
            if callable(retranslate):
                try:
                    retranslate()
                except Exception:
                    logger.debug("%s.retranslate failed", owner_attr, exc_info=True)
        # Lazy-loaded pages also expose retranslate() — refactor them after
        # language changes so freshly-mounted forms stay in sync.
        for page_attr in (
            "_home_page",
            "_production_page",
            "_assets_page",
            "_settings_page",
        ):
            page = getattr(self, page_attr, None)
            if page is None:
                continue
            retranslate = getattr(page, "retranslate", None)
            if callable(retranslate):
                try:
                    retranslate()
                except Exception:
                    logger.debug("%s.retranslate failed", page_attr, exc_info=True)

    def _on_open_project(self, project_path: str = "") -> None:
        """Open a .scenefab project — delegated to ``ProjectIOController``."""
        self.project_io.open_project(project_path)

    def _on_check_updates(self) -> None:
        """Help → 检查更新…：后台检查并用弹窗反馈，不打开更新页面。"""
        if getattr(self, "_update_check_in_progress", False):
            return

        service = None
        if self._application is not None:
            service = self._application.get_service_by_name("updater_service")
        if service is None:
            try:
                from app.updater import UpdaterService

                service = UpdaterService.from_settings()
            except Exception:
                logger.debug("无法创建更新服务", exc_info=True)
                QMessageBox.warning(
                    self,
                    t("update.menu.popup.check_failed.title"),
                    t(
                        "update.menu.popup.check_failed.message",
                        error=t("common.unknown"),
                    ),
                )
                return

        signals = getattr(service, "signals", None)
        if signals is None:
            QMessageBox.warning(
                self,
                t("update.menu.popup.check_failed.title"),
                t(
                    "update.menu.popup.check_failed.message",
                    error=t("common.unknown"),
                ),
            )
            return

        self._update_check_in_progress = True

        def disconnect_handlers() -> None:
            for signal, handler in handlers:
                try:
                    signal.disconnect(handler)
                except (AttributeError, RuntimeError, TypeError):
                    pass
            self._update_check_in_progress = False

        def on_update_available(manifest: object) -> None:
            disconnect_handlers()
            version = str(getattr(manifest, "version", "") or "")
            notes = str(getattr(manifest, "release_notes", "") or "")
            current = self._current_app_version()
            url = "https://github.com/Agions/scene-fab/releases/tag/v" + version
            QMessageBox.information(
                self,
                t("update.menu.popup.new_version.title"),
                t(
                    "update.menu.popup.new_version.message",
                    latest=version,
                    current=current,
                    notes=notes or t("common.unknown"),
                    url=url,
                ),
            )

        def on_update_unavailable() -> None:
            disconnect_handlers()
            QMessageBox.information(
                self,
                t("update.menu.popup.up_to_date.title"),
                t(
                    "update.menu.popup.up_to_date.message",
                    current=self._current_app_version(),
                ),
            )

        def on_error(_code: str, message: str) -> None:
            disconnect_handlers()
            QMessageBox.warning(
                self,
                t("update.menu.popup.check_failed.title"),
                t(
                    "update.menu.popup.check_failed.message",
                    error=message or t("common.unknown"),
                ),
            )

        handlers = [
            (getattr(signals, "update_available", None), on_update_available),
            (getattr(signals, "update_unavailable", None), on_update_unavailable),
            (getattr(signals, "error_occurred", None), on_error),
        ]
        handlers = [(signal, handler) for signal, handler in handlers if signal]
        try:
            for signal, handler in handlers:
                signal.connect(handler)
        except (AttributeError, RuntimeError, TypeError):
            disconnect_handlers()
            logger.debug("更新信号连接失败", exc_info=True)
            QMessageBox.warning(
                self,
                t("update.menu.popup.check_failed.title"),
                t(
                    "update.menu.popup.check_failed.message",
                    error=t("common.unknown"),
                ),
            )
            return

        def check_in_background() -> None:
            try:
                service.check(timeout=10.0)
            except Exception as exc:  # pragma: no cover - 防御性兜底
                logger.warning("更新检查失败: %s", exc)

        threading.Thread(
            target=check_in_background,
            name="scenefab-menu-update-check",
            daemon=True,
        ).start()

    @staticmethod
    def _current_app_version() -> str:
        from app.utils.version import get_version_string

        return get_version_string()

    def show_message(self, message: str, level: str = "info"):
        """显示消息提示"""
        title_key = {
            "error": "common.error",
            "warning": "common.warning",
            "info": "common.info",
        }.get(level, "common.info")
        title = t(title_key)
        if level == "error":
            QMessageBox.critical(self, title, message)
        elif level == "warning":
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    @Slot(str, str)
    def show_message_safe(self, message: str, level: str = "info") -> None:
        """线程安全的 ``show_message`` 包装（Phase 1 · TD-11）。

        当 :class:`app.updater.UpdaterService` 在后台线程里推送新版本时，
        其信号默认走 ``Qt.AutoConnection``，会在主线程上派发，调用此槽。
        额外提供 ``Slot`` 装饰，使得从非主线程 ``QMetaObject.invokeMethod``
        也能被 Qt 路由到主线程。
        """
        self.show_message(message, level=level)

    def show_loading(self, show: bool = True):
        """显示/隐藏加载状态"""
        # Use the same key the initial render uses so retranslate can
        # rebuild the active label when language flips.
        if show:
            self.statusbar.set_status(t("common.loading"), key="common.loading")
        else:
            self.statusbar.set_status(t("common.ready"), key="common.ready")

    # ══════════════════════════════════════════════════════════════
    # 拖放支持 (delegated to MainWindowDropZone)
    # ══════════════════════════════════════════════════════════════

    def dragEnterEvent(self, event):
        self.drop_zone.handle_drag_enter(event)

    def dropEvent(self, event):
        self.drop_zone.handle_drop(event)

    def _on_save_project(self) -> None:
        """Save the current project — delegated to ``ProjectIOController``."""
        self.project_io.save_project()

    def _on_import_assets(self) -> None:
        """Import media assets — delegated to ``AssetsIOController``."""
        self.assets_io.import_assets()

    def build_global_stylesheet(self) -> str:
        """Return the QApplication-level stylesheet using current _C values."""
        prefix = f"""
            QMainWindow {{
                background: {_C.BG_BASE};
                outline: none;
            }}
            QToolButton#topbar_action_btn {{
                background: {_C.BG_SURFACE};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.base};
                color: {_C.TEXT_SECONDARY};
                font-size: {FontSizes.xs}px;
                font-weight: 600;
            }}
            QToolButton#topbar_action_btn:hover {{
                background: {_C.PRIMARY_LIGHTEST};
                color: {_C.PRIMARY_DARKER};
                border-color: {_C.PRIMARY};
            }}
            QTooltip {{
                background: {_C.BG_OVERLAY};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                padding: 6px 10px;
                font-size: {FontSizes.xs}px;
            }}
        """
        suffix = f"""
            * {{
                selection-background-color: {_C.PRIMARY};
                selection-color: {_C.TEXT_INVERSE};
            }}
        """
        return prefix + QSSComponents.scrollbar() + QSSComponents.combobox() + suffix

    # ThemeAwareMixin hook: route _build_stylesheet to the live builder above
    def _build_stylesheet(self) -> str:
        return self.build_global_stylesheet()

    def apply_theme(self, palette: str = "") -> str:
        """ThemeAwareMixin override that also refreshes chrome.

        The default mixin only reissues ``self.setStyleSheet(qss)`` on
        the receiving widget. The main window owns a small set of
        chrome widgets (sidebar / topbar / statusbar / nav buttons) that
        each build their own QSS from ``_C.*`` at construction time.
        Once a palette flip rebinds ``_C``, those child widgets keep
        their frozen QSS unless we explicitly tell them to rebuild.

        The optional ``palette`` argument matches the signature used by
        :class:`ThemeController._on_palette_changed` — the controller
        forwards the new palette name (e.g. ``"dark"``) so hooks that
        care about the exact transition can react. We don't need it
        here (the rebinding of ``_C`` already happened upstream) but we
        must accept it or the controller's call would raise ``TypeError``
        and silently drop the entire chrome refresh.

        Each chrome component exposes ``_setup_style`` (the same
        idempotent builder used at construction) so we simply call it
        after applying the main window's own stylesheet. Errors are
        swallowed per-widget so a single chrome failure cannot break
        the rest of the palette switch.
        """
        qss = self.build_global_stylesheet()
        self.setStyleSheet(qss)
        # Sidebar / topbar / statusbar sit as direct attributes; nav
        # buttons live on the sidebar and need to rebuild their own
        # per-button stylesheet when ``_C`` changes.
        for owner_attr in ("sidebar", "topbar", "statusbar"):
            owner = getattr(self, owner_attr, None)
            setup = getattr(owner, "_setup_style", None)
            if callable(setup):
                try:
                    setup()
                except Exception:  # pragma: no cover — defensive
                    logger.debug(
                        "%s._setup_style 失败",
                        owner_attr,
                        exc_info=True,
                    )
        sidebar = getattr(self, "sidebar", None)
        if sidebar is not None:
            for btn in getattr(sidebar, "_nav_btns", {}).values():
                apply_style = getattr(btn, "_apply_style", None)
                if callable(apply_style):
                    try:
                        # ``_apply_style`` re-reads the active state to
                        # re-pick colors that depend on the new palette.
                        apply_style(btn._item_id == sidebar.current())
                    except Exception:  # pragma: no cover
                        logger.debug(
                            "SideNavBtn._apply_style 失败",
                            exc_info=True,
                        )
        return qss

    # ──────────────────────────────────────────────────────────
    # 路由 + 动作
    # ──────────────────────────────────────────────────────────

    def _on_navigate(self, page_id: str) -> None:
        self.sidebar.set_active(page_id)
        self.router.navigate(page_id)

    def navigate_to(self, page_id: str, **_kwargs: object) -> None:
        """公共导航接口(供其他模块从外部跳转)。"""
        self._on_navigate(page_id)

    def _on_action(self, action_id: str) -> None:
        if action_id == "export":
            self._on_navigate("create")
            self.statusbar.set_status(t("statusbar.export_hint"))

    # ──────────────────────────────────────────────────────────
    # 生产流程接线（ProductionRunner → 主窗口）
    # ──────────────────────────────────────────────────────────

    def _on_start_production(self) -> None:
        """Start a new production run via the menu / TopBar path.

        Asks the user for a video file, then hands off to
        ``_start_production_with_video`` which is also called by the
        drop zone.
        """
        from PySide6.QtWidgets import QFileDialog

        video_path, _ = QFileDialog.getOpenFileName(
            self,
            t("production.browse_dialog_title"),
            "",
            t("production.video_filter"),
        )
        if not video_path:
            return
        self._start_production_with_video(video_path)

    def _start_production_with_video(
        self, video_path: str, context: str = "", emotion: str = ""
    ) -> None:
        """Run the production flow with a known video path.

        Prompting for missing context/emotion happens here so the
        menu, drop-zone, and inline form paths all share the same UX.
        """
        if not context or not context.strip():
            from PySide6.QtWidgets import QInputDialog

            context, ok = QInputDialog.getText(
                self,
                t("production.dialog.title"),
                t("production.dialog.context"),
                text=DEFAULT_CONTEXT,
            )
            if not ok or not context.strip():
                return

        if not emotion:
            from PySide6.QtWidgets import QInputDialog

            emotion, ok = QInputDialog.getItem(
                self,
                t("production.dialog.title"),
                t("production.dialog.emotion"),
                list(DEFAULT_EMOTIONS),
                0,
                False,
            )
            if not ok:
                return

        self.statusbar.set_status(t("step.progress.processing").format(path=video_path))
        self.show_loading(True)
        if hasattr(self, "_production_page"):
            self._production_page.reset_steps()
            self._production_page.set_running(True)
            # Note: step name ("素材导入") is a runtime key matching
            # production_runner._ALL_PRODUCTION_STEPS — it needs separate
            # i18n alignment with the VM layer.
            self._production_page.update_step_status(
                "素材导入", t("step.status.active"), _C.PRIMARY
            )

        if not self.production_runner.start(video_path, context, emotion):
            # 已经有一个生产在跑，提示用户取消后再来。
            self.statusbar.set_status(t("main.task_running"))

    def _start_production_with_videos(
        self,
        video_paths: list[str],
        context: str = "",
        emotion: str = "",
        strategy: str = "batch",
        series_context=None,
    ) -> None:
        """多视频生产入口（v2.5.0）。

        Args:
            video_paths: 2+ 视频路径
            context: 主题/情境
            emotion: 情感基调
            strategy: ``"single"``/``"concat"``/``"batch"``/``"series"``
            series_context: :class:`SeriesContext` 实例（仅 series 生效）

        Behavior: 与 ``_start_production_with_video`` 一样负责补齐
        缺失的 context/emotion，然后调用 ``production_runner.start_batch``。
        """
        if not context or not context.strip():
            from PySide6.QtWidgets import QInputDialog

            context, ok = QInputDialog.getText(
                self,
                t("production.dialog.title"),
                t("production.dialog.context"),
                text=DEFAULT_CONTEXT,
            )
            if not ok or not context.strip():
                return

        if not emotion:
            from PySide6.QtWidgets import QInputDialog

            emotion, ok = QInputDialog.getItem(
                self,
                t("production.dialog.title"),
                t("production.dialog.emotion"),
                list(DEFAULT_EMOTIONS),
                0,
                False,
            )
            if not ok:
                return

        self.statusbar.set_status(
            t("step.progress.processing").format(path=video_paths[0])
        )
        self.show_loading(True)
        if hasattr(self, "_production_page"):
            self._production_page.reset_steps()
            self._production_page.set_running(True)
            self._production_page.update_step_status(
                "素材导入", t("step.status.active"), _C.PRIMARY
            )

        if not self.production_runner.start_batch(
            list(video_paths),
            context,
            emotion,
            strategy=strategy,
            series_context=series_context,
        ):
            self.statusbar.set_status(t("main.task_running"))

    def _on_step_status_changed(self, step_name: str, status: str, color: str) -> None:
        if hasattr(self, "_production_page"):
            self._production_page.update_step_status(step_name, status, color)

    def _on_production_progress_msg(
        self, current: int, total: int, message: str
    ) -> None:
        self.statusbar.set_status(
            t("step.progress.format").format(
                current=current, total=total, message=message
            )
        )
        self.statusbar.show_progress(current, total)

    def _on_production_finished(self, project, project_path: str) -> None:
        self.show_loading(False)
        self.statusbar.hide_progress()
        if hasattr(self, "_production_page"):
            self._production_page.set_running(False)

        self._last_project = project
        self.statusbar.set_status(t("production.result.success"))

        # Refresh HomePage dashboard stats after production.
        if hasattr(self, "_home_page"):
            self._home_page.refresh_from_viewmodel()

        msg = t("production.cancelled_dialog.success_text")
        if project_path:
            msg += t("main.run_complete.saved").format(path=project_path)

        box = QMessageBox(self)
        box.setWindowTitle(t("production.cancelled_dialog.title"))
        box.setText(msg)
        export_btn = box.addButton(
            t("production.action.export"),
            QMessageBox.ButtonRole.ActionRole,
        )
        save_btn = box.addButton(
            t("production.action.save_project"),
            QMessageBox.ButtonRole.ActionRole,
        )
        box.addButton(t("common.close"), QMessageBox.ButtonRole.RejectRole)
        box.exec()

        clicked = box.clickedButton()
        if clicked == export_btn:
            self._run_export()
        elif clicked == save_btn:
            self._on_save_project()

    def _on_production_failed(self, error_msg: str) -> None:
        self.show_loading(False)
        self.statusbar.hide_progress()
        if hasattr(self, "_production_page"):
            self._production_page.set_running(False)
        self.statusbar.set_status(t("production.result.failed") + f": {error_msg}")
        self.show_message(
            t("error.production_failed").format(error=error_msg),
            level="error",
        )

    def _on_cancel_production(self) -> None:
        """Request cancellation (cancel button / Escape)."""
        if self.production_runner.cancel():
            self.statusbar.set_status(t("production.result.cancelling"))

    def _on_production_cancelled(self) -> None:
        self.show_loading(False)
        self.statusbar.hide_progress()
        if hasattr(self, "_production_page"):
            self._production_page.set_running(False)
        self.statusbar.set_status(t("production.result.cancelled"))

    # ──────────────────────────────────────────────────────────
    # 导出接线（ExportController → 主窗口）
    # ──────────────────────────────────────────────────────────

    def _run_export(self) -> None:
        self.exporter.run()

    def _on_export_succeeded(self, output_dir: str) -> None:
        self.statusbar.set_status(t("error.export_success"))
        if hasattr(self, "_home_page"):
            self._home_page.mark_export_status(t("step.status.done"))

    # ──────────────────────────────────────────────────────────
    # 托盘 / 关闭
    # ──────────────────────────────────────────────────────────

    def _restore_from_tray(self) -> None:
        self.tray.restore_from_tray(self)

    def _open_settings_from_tray(self) -> None:
        self._restore_from_tray()
        self._on_navigate("settings")

    def _quit_application(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def set_minimize_to_tray(self, enabled: bool) -> None:
        """供 SettingsPage 调用的关闭行为开关。"""
        self.tray.set_minimize_to_tray(enabled)

    def _install_phase2_services(self) -> None:
        """注册 Phase 2 服务：DashboardViewModel + SystemMonitor + CommandPalette。

        存在 ``self`` 的下面这些属性：

        * ``self._dashboard_vm`` ：DashboardViewModel，可用于后续阶段。
        * ``self.system_monitor`` ：1Hz 采样的 :class:`SystemMonitor`。
        * ``self.command_palette`` ：可全局 ``Cmd+K`` 唤醒的命令面板。
        * ``self._command_registry`` ：命令源（可供插件 / 测试动态增删）。

        本方法容忍任何前置依赖缺失（application / event_bus / psutil）——
        失败时仅记录警告不抛异常。
        """
        from app.services.monitor import SystemMonitor
        from app.ui.commands import Command, CommandRegistry
        from app.ui.widgets.command_palette import CommandPalette

        # 1) DashboardViewModel — 替换默认的 HomePageViewModel。
        try:
            dashboard_vm = DashboardViewModel(self._application, self)
            if self._application is not None:
                dashboard_vm.bind()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Phase 2: DashboardViewModel init failed: %s", exc)
            dashboard_vm = None
        self._dashboard_vm = dashboard_vm

        # 2) SystemMonitor — 取 application 上的 event_bus 启动采样。
        if self._application is not None:
            event_bus = self._application.get_service_by_name("event_bus")
        else:
            event_bus = None
        if event_bus is None:
            try:
                from app.core.unified_event_bus import get_event_bus

                event_bus = get_event_bus()
            except Exception:  # noqa: BLE001
                event_bus = None

        monitor: SystemMonitor | None = None
        if event_bus is not None:
            try:
                monitor = SystemMonitor(event_bus, hz=1.0)
                monitor.start()
                logger.debug("SystemMonitor started at 1Hz")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Phase 2: SystemMonitor.start failed: %s", exc)
                monitor = None
        else:
            logger.debug("Phase 2: SystemMonitor skipped — event_bus unavailable")
        self.system_monitor = monitor

        # 3) CommandPalette + 默认命令
        registry = CommandRegistry()
        self._command_registry = registry

        def _nav(page_id: str):
            def _call() -> None:
                self._on_navigate(page_id)

            return _call

        # 把现有的页面路由用最少耦合暴露给面板。每个回调都用闭包
        # 捕获 page_id，常量来自 chrome 模块。
        from app.ui.main.main_window.chrome import (
            NAV_CREATE,
            NAV_SETTINGS,
        )

        default_commands: list[Command] = [
            Command(
                id="nav.home",
                title="打开工作台",
                callback=_nav(NAV_HOME),
                group="nav",
                keywords=("home", "dashboard", "工作台"),
            ),
            Command(
                id="nav.create",
                title="新建项目",
                callback=_nav(NAV_CREATE),
                group="nav",
                keywords=("new", "create", "新建"),
            ),
            Command(
                id="nav.settings",
                title="打开设置",
                callback=_nav(NAV_SETTINGS),
                group="nav",
                keywords=("settings", "preferences", "设置"),
            ),
            Command(
                id="app.toggle_command_palette",
                title="打开命令面板",
                callback=lambda: self._toggle_command_palette(),
                group="ui",
                keywords=("palette", "command", "命令"),
                shortcut_hint="Ctrl+K",
            ),
            Command(
                id="app.quit",
                title="退出",
                callback=self._quit_application,
                group="app",
                keywords=("quit", "exit", "关闭"),
                shortcut_hint="Ctrl+Q",
            ),
        ]
        # 5) Cmd+K 中 help.open 提示
        default_commands.append(
            Command(
                id="help.open",
                title=_tr(
                    MessageKey.HELP_COMMAND_OPEN_TITLE,
                    default="打开帮助面板",
                ),
                callback=lambda: self._show_help_panel(),
                group=_tr(MessageKey.HELP_COMMAND_OPEN_GROUP, default="帮助"),
                shortcut_hint="F1",
                keywords=("help", "帮助", "faq", "guide"),
            )
        )
        for cmd in default_commands:
            registry.register(cmd)

        palette: CommandPalette | None = None
        try:
            palette = CommandPalette(registry, self, shortcut="Ctrl+K")
            palette.commandExecuted.connect(self._on_command_executed)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Phase 2: CommandPalette init failed: %s", exc)
            palette = None
        self.command_palette = palette

    def _toggle_command_palette(self) -> None:
        if getattr(self, "command_palette", None) is None:
            return
        self.command_palette.toggle()

    def _on_command_executed(self, _command_id: str) -> None:
        logger.debug("CommandPalette executed command: %s", _command_id)
        # palette 关闭后，键盘 focus 回到 main window；显式 trigger
        # activePage retranslate 以确保任何最近被修改的 label 同步。
        if hasattr(self, "_home_page") and self._home_page is not None:
            self._home_page.refresh_from_viewmodel()

    # ──────────────────────────────────────────────────────────
    # Phase 3 · Help Panel dock + Settings 帮助中心调度
    # ──────────────────────────────────────────────────────────

    def _install_phase3_help(self) -> None:
        """创建右侧 HelpPanel dock + 接入 SettingsPage 帮助 button 信号。

        存在下面的属性：

        * ``self.help_panel_widget`` —— :class:`HelpPanelWidget` 实例，
          可供其他模块调用 :py:meth:`HelpPanelWidget.open_topic` 跳转 topic。
        * ``self.help_dock`` —— :class:`QDockWidget`，默认隐藏，可通过
          :py:meth:`_show_help_panel` 显示。
        """
        # 延迟 import，避免 PySide6-free 单元测试 (test_settings 等) 加载时
        # 触发 widgets 子模块的全部 import。
        from app.help import build_default_registry
        from app.ui.widgets.help_panel import HelpPanelWidget

        registry = build_default_registry()
        widget = HelpPanelWidget(registry, self)

        dock = QDockWidget(_tr(MessageKey.HELP_PANEL_TITLE, default="帮助中心"), self)
        dock.setObjectName("help_dock")
        dock.setWidget(widget)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        # 默认隐藏，避免首次启动时被阴影挡住 Dashboard。
        dock.hide()
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self.help_panel_widget = widget
        self.help_dock = dock

        # F1 全局快捷键
        from PySide6.QtGui import QKeySequence, QShortcut

        f1 = QShortcut(QKeySequence(Qt.Key.Key_F1), self)
        f1.setContext(Qt.ShortcutContext.ApplicationShortcut)
        f1.activated.connect(self._show_help_panel)

        # 接入 SettingsPage 帮助中心 row 的 button 信号
        settings_page = getattr(self, "_settings_page", None)
        if settings_page is not None and hasattr(
            settings_page, "help_action_requested"
        ):
            settings_page.help_action_requested.connect(self._on_help_action_requested)
            logger.debug(
                "Phase 3: settings.help_action_requested wired (key=%s)",
                id(settings_page),
            )
        else:
            logger.warning(
                "Phase 3: settings_page.help_action_requested unavailable; "
                "help buttons will be no-op"
            )

    def _show_help_panel(self) -> None:
        """显示 / 聚焦右侧帮助 dock。"""
        dock = getattr(self, "help_dock", None)
        if dock is None:
            logger.warning("Help dock unavailable; cannot show")
            return
        dock.show()
        dock.raise_()
        widget = getattr(self, "help_panel_widget", None)
        if widget is not None and hasattr(widget, "_search"):
            widget._search.setFocus()

    def hide_help_panel(self) -> None:
        dock = getattr(self, "help_dock", None)
        if dock is not None:
            dock.hide()

    def _on_help_action_requested(self, key: str) -> None:
        """SettingsPage 帮助中心 row 点击调度。

        * ``help.open`` —— 显示帮助 dock
        * ``help.reset_onboarding`` —— 清除 onboarding_done，下次启动重试
          （当前 Phase 3 仅清除标记位；完整 OnboardingTour 留 v2.5）。
        * ``help.copy_diagnostics`` —— TODO v2.5：调用 utils/diagnostics
        """
        if key == "help.open":
            self._show_help_panel()
            return
        if key == "help.reset_onboarding":
            QSettings("SceneFab", "Application").remove("onboarding/done")
            QMessageBox.information(
                self,
                _tr(MessageKey.HELP_PANEL_TITLE, default="帮助中心"),
                _tr(
                    MessageKey.HELP_ROW_RESET_DESC,
                    default="清除首次启动引导标记，下次启动重新演示。",
                ),
            )
            return
        if key == "help.copy_diagnostics":
            # Phase 4-4 · 真正调用 utils.diagnostics.collect_diagnostics(),
            # 包成 code block 贴到剪贴板，同时给 statusbar 一个反馈。
            self._on_copy_diagnostics()
            return
        logger.warning("Unknown help_action_requested key: %s", key)

    # ──────────────────────────────────────────────────────────
    # Phase 4 · 可观测性 (settings_store + metrics + diagnostics)
    # ──────────────────────────────────────────────────────────

    def _install_phase4_observability(self) -> None:
        """把 settings_store 门面装好，并把 metrics 接入 event_bus。

        必须在 ``_setup_ui`` 之后调用，因为需要 ``self.event_bus`` 和
        ``self._application`` 都已初始化。失败时只记 logger.warning，
        不阻断主窗口启动——可观测性是 best-effort。
        """
        try:
            from app.core.metrics import get_metrics
            from app.core.settings_store import get_settings

            store = get_settings()
            # 1) ConfigManager —— 来自 application 的 settings_manager
            #    内部已持有 config 实例，但 settings_store 走自己的入口。
            try:
                from app.config.config import get_config

                store.bind_config(get_config())
            except Exception as exc:  # noqa: BLE001
                logger.debug("settings_store.bind_config skipped: %s", exc)
            # 2) ProjectSettingsManager
            pm = getattr(self, "_project_manager", None)
            if pm is not None and hasattr(pm, "settings"):
                store.bind_project(pm)
            # 3) QSettings —— 用本窗口用的那个，避免再起一份。
            try:
                store.bind_qsettings(self._help_qsettings())
            except Exception as exc:  # noqa: BLE001
                logger.debug("settings_store.bind_qsettings skipped: %s", exc)

            # 把 metrics 绑到 event_bus：以后所有 publish 的事件都会自动
            # 计数到 events.<event_name> counter，零侵入观测。
            bus = getattr(self, "event_bus", None)
            if bus is not None:
                get_metrics().bind_to_event_bus(bus, prefix="events")
            else:
                logger.debug("Phase 4: self.event_bus missing; metrics not bound")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Phase 4 observability install failed (non-fatal): %s", exc)

    def _help_qsettings(self):
        """返回本窗口用的 QSettings（懒创建，单元测试不会触发）。"""
        # 与 ``__init__`` 里 ``QSettings("SceneFab", "Application")`` 保持
        # 完全相同的 org/app 组合，否则 settings_store 和 main_window
        # 写入的 key 互不可见。
        from PySide6.QtCore import QSettings

        return QSettings("SceneFab", "Application")

    def _on_copy_diagnostics(self) -> None:
        """收集诊断快照、写到剪贴板、在 statusbar 反馈。"""
        try:
            from app.core.audit import AuditLogger
            from app.utils.diagnostics import (
                collect_diagnostics,
                diagnostics_to_clipboard_payload,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("diagnostics import failed: %s", exc)
            QMessageBox.warning(
                self,
                _tr(MessageKey.HELP_PANEL_TITLE, default="帮助中心"),
                f"诊断信息收集失败: {exc}",
            )
            return

        # 把 audit buffer 强制落盘，避免 \"最近 N 条\" 拿不到刚打的事件。
        try:
            AuditLogger().flush()
        except Exception:  # noqa: BLE001
            pass

        text = collect_diagnostics()
        payload = diagnostics_to_clipboard_payload(text)

        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(payload)
        if hasattr(self, "statusbar") and self.statusbar is not None:
            self.statusbar.set_status(
                _tr(
                    MessageKey.HELP_DIAGNOSTICS_COPIED,
                    default="诊断信息已复制到剪贴板",
                )
            )

    def closeEvent(self, event) -> None:
        # Phase 2 · 关闭前停 SystemMonitor / DashboardVM，防止 daemon 线程
        # 在 QApplication 销毁后还在 publish event。
        monitor = getattr(self, "system_monitor", None)
        if monitor is not None:
            try:
                monitor.stop(timeout=1.0)
            except Exception:  # noqa: BLE001
                logger.debug("SystemMonitor.stop suppressed exception", exc_info=True)
        vm = getattr(self, "_dashboard_vm", None)
        if vm is not None:
            try:
                vm.unbind()
            except Exception:  # noqa: BLE001
                logger.debug(
                    "DashboardViewModel.unbind suppressed exception", exc_info=True
                )
        # CommandPalette 可以直接 GC 让 Qt 自动清理，这里只需关掉浮层
        palette = getattr(self, "command_palette", None)
        if palette is not None and palette.isVisible():
            palette.close()
        # Phase 3 · Help dock —— 提前 hide 避免关闭动画与 QApplication 销毁竞速
        help_dock = getattr(self, "help_dock", None)
        if help_dock is not None:
            try:
                help_dock.hide()
            except Exception:  # noqa: BLE001
                logger.debug("help_dock.hide suppressed exception", exc_info=True)
        self.tray.handle_close_event(self, event)

    # ──────────────────────────────────────────────────────────
    # 公共便利方法
    # ──────────────────────────────────────────────────────────

    @property
    def app(self) -> QApplication:
        return QApplication.instance()

    @property
    def application(self) -> Application | None:
        return self._application


__all__ = ["SceneFabMainWindow"]
