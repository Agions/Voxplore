"""Main-window chrome (menu bar, shortcuts, about-dialog).

Extracted from ``SceneFabMainWindow`` as part of the Phase B
single-responsibility refactor. The controller owns the QMenuBar
construction and exposes simple ``on_*`` slots the main window wires to
its own navigation / project-IO / quit handlers. It does not depend on
the ``Application`` service container or the project manager — the
main window injects those behaviors through callbacks so this file
stays trivially testable.

Internationalization (Phase C)
-----------------------------
All visible strings are routed through :func:`app.ui.i18n.t` with stable
``menu.*`` keys so the menu bar reflects the active UI language. The
controller stores a flat ``(menu, action, key)`` table so a later
``retranslate()`` call (driven by ``Translator.language_changed``)
updates every visible label without rebuilding the QMenuBar tree.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMainWindow, QMenu, QMenuBar, QMessageBox

from app.ui.i18n import t

ActionCallback = Callable[[], None]


class MainWindowChrome:
    """Owns the menu bar + global shortcuts for the main window.

    The class is a plain Python object — it is *not* a QObject. Qt owns
    the menu actions through the QMainWindow itself; this controller
    just builds them and exposes named slots. Keeping it out of the
    QObject tree means it doesn't fight with parent ownership when the
    main window is destroyed and recreated (e.g. theme tests).
    """

    def __init__(
        self,
        window: QMainWindow,
        *,
        on_new_project: ActionCallback,
        on_open_project: ActionCallback,
        on_save_project: ActionCallback,
        on_import_assets: ActionCallback,
        on_export: ActionCallback,
        on_quit: ActionCallback,
        on_navigate: Callable[[str], None],
        on_open_settings: ActionCallback,
        on_check_updates: ActionCallback,
    ) -> None:
        self._window = window
        self._on_navigate = on_navigate
        self._on_open_settings = on_open_settings
        self._on_check_updates = on_check_updates

        # (menu, action, key) tuples — used by ``retranslate()`` to
        # refresh every visible label after a language switch without
        # rebuilding the whole menu tree.
        self._i18n_entries: list[tuple[QMenu, QAction, str]] = []
        self._menu_titles: dict[QMenu, str] = {}

        self._build_menu_bar(
            on_new_project=on_new_project,
            on_open_project=on_open_project,
            on_save_project=on_save_project,
            on_import_assets=on_import_assets,
            on_export=on_export,
            on_quit=on_quit,
        )

    # ──────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────

    def show_about(self) -> None:
        QMessageBox.about(
            self._window,
            t("menu.help.about_window_title"),
            "<h3>" + t("app.name") + "</h3>"
            "<p>" + t("app.tagline") + "</p>"
            "<p>" + t("app.tech_stack") + "</p>",
        )

    def retranslate(self) -> None:
        """Refresh every visible menu + action label with the current
        language. Safe to call multiple times; expected to be hooked up
        to :py:attr:`Translator.language_changed`.

        If the about dialog's window title and tooltip keys were the
        only labels that change, this method is a no-op for that —
        they're resolved lazily by ``show_about``.
        """
        for menu, action, key in self._i18n_entries:
            action.setText(t(key))
        for menu, key in self._menu_titles.items():
            menu.setTitle(t(key))

    # ──────────────────────────────────────────────────────────
    # Menu bar construction
    # ──────────────────────────────────────────────────────────

    def _build_menu_bar(
        self,
        *,
        on_new_project: ActionCallback,
        on_open_project: ActionCallback,
        on_save_project: ActionCallback,
        on_import_assets: ActionCallback,
        on_export: ActionCallback,
        on_quit: ActionCallback,
    ) -> None:
        menubar: QMenuBar = self._window.menuBar()

        def add_action(
            menu: QMenu,
            key: str,
            shortcut: str,
            slot: ActionCallback,
        ) -> QAction:
            action = QAction(t(key), menu)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(slot)
            menu.addAction(action)
            self._i18n_entries.append((menu, action, key))
            return action

        def add_menu(parent: QMenuBar, key: str) -> QMenu:
            menu = QMenu(t(key), parent)
            parent.addMenu(menu)
            self._menu_titles[menu] = key
            return menu

        # 文件
        file_menu = add_menu(menubar, "menu.file")
        add_action(file_menu, "menu.file.new_project", "Ctrl+N",
                   lambda: self._on_navigate("create"))
        add_action(file_menu, "menu.file.open_project", "Ctrl+O",
                   on_open_project)
        add_action(file_menu, "menu.file.save_project", "Ctrl+S",
                   on_save_project)
        add_action(file_menu, "menu.file.import_assets", "Ctrl+I",
                   on_import_assets)
        add_action(file_menu, "menu.file.export", "Ctrl+E", on_export)
        file_menu.addSeparator()
        add_action(file_menu, "menu.file.quit", "Ctrl+Q", on_quit)

        # 编辑
        edit_menu = add_menu(menubar, "menu.edit")
        add_action(edit_menu, "menu.edit.preferences", "Ctrl+,",
                   self._on_open_settings)

        # 视图
        view_menu = add_menu(menubar, "menu.view")
        add_action(view_menu, "menu.view.home", "Ctrl+1",
                   lambda: self._on_navigate("home"))
        add_action(view_menu, "menu.view.production", "Ctrl+2",
                   lambda: self._on_navigate("create"))
        add_action(view_menu, "menu.view.assets", "Ctrl+3",
                   lambda: self._on_navigate("assets"))
        add_action(view_menu, "menu.view.settings", "Ctrl+4",
                   lambda: self._on_navigate("settings"))
        add_action(view_menu, "menu.view.update", "Ctrl+5",
                   lambda: self._on_navigate("update"))
        # Dashboard "快捷操作" 面板承诺的 F5 / F6：
        # - F5 创作流程（对应 Ctrl+2）
        # - F6 项目资产（对应 Ctrl+3）
        # 它们必须以 QAction shortcut 注册，才能在主窗口未打开菜单时也生效。
        add_action(view_menu, "menu.view.production", "F5",
                   lambda: self._on_navigate("create"))
        add_action(view_menu, "menu.view.assets", "F6",
                   lambda: self._on_navigate("assets"))

        # 帮助
        # 注意：检查更新点击不再跳转到独立 update 页面，
        # 而是以 QMessageBox 弹窗反馈结果（保持用户当前上下文）。
        help_menu = add_menu(menubar, "menu.help")
        add_action(help_menu, "menu.help.check_updates", "",
                   self._on_check_updates)
        help_menu.addSeparator()
        add_action(help_menu, "menu.help.about", "", self.show_about)


# Navigation ID constants — shared between main_window and chrome.
NAV_HOME = "home"
NAV_CREATE = "create"
NAV_ASSETS = "assets"
NAV_SETTINGS = "settings"


__all__ = ["MainWindowChrome", "NAV_HOME",
           "NAV_CREATE", "NAV_ASSETS", "NAV_SETTINGS"]
