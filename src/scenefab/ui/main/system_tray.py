#!/usr/bin/env python3
"""System tray controller — extracted from SceneFabMainWindow.

Owns the optional QSystemTrayIcon integration. The window delegates
``closeEvent`` interception, ``set_minimize_to_tray`` toggling, and
the "tray menu" affordances to this controller. It is fully self-contained
and can be exercised in isolation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QMainWindow

from scenefab.ui.main.tray_manager import get_tray_manager

if TYPE_CHECKING:
    from scenefab.ui.main.tray_manager import TrayManager

logger = logging.getLogger(__name__)


class SystemTrayController(QObject):
    """Manages the optional system tray icon and its menu.

    Signals
    -------
    show_window_requested : emitted when the user picks "show window".
    open_settings_requested : emitted when the user picks "settings".
    quit_requested : emitted when the user picks "quit".
    """

    show_window_requested = Signal()
    open_settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tray: TrayManager | None = None
        self._minimize_enabled = False
        self._quitting = False
        self._tray_hint_shown = False
        self._init_tray()

    # ── Initialization ─────────────────────────────────────────

    def _init_tray(self) -> None:
        tray = get_tray_manager()
        try:
            self._tray = tray
            tray.show_window_requested.connect(self.show_window_requested)
            tray.open_settings_requested.connect(self.open_settings_requested)
            tray.quit_requested.connect(self._on_quit_requested)
        except Exception as e:  # noqa: BLE001
            logger.warning("Tray init failed: %s", e)
            self._tray = None

    def _on_quit_requested(self) -> None:
        self._quitting = True
        if self._tray is not None:
            self._tray.disable()
        self.quit_requested.emit()
        QApplication.instance().quit()  # type: ignore[union-attr]

    # ── Public API ─────────────────────────────────────────────

    def set_minimize_to_tray(self, enabled: bool) -> None:
        """Toggle whether the window hides to the tray on close."""
        self._minimize_enabled = bool(enabled)
        tray = self._tray
        if tray is None:
            return
        if enabled and not tray.is_enabled:
            tray.enable("SceneFab")
        elif not enabled and tray.is_enabled:
            tray.disable()

    def handle_close_event(self, window: QMainWindow, event) -> None:
        """Intercept window close. Returns nothing; the controller mutates
        ``event`` directly to either ``accept()`` or ``ignore()``."""
        if self._quitting:
            event.accept()
            return
        tray = self._tray
        if (
            self._minimize_enabled
            and tray is not None
            and tray.is_enabled
            and tray.is_available
        ):
            event.ignore()
            window.hide()
            if not self._tray_hint_shown:
                tray.show_notification(
                    "SceneFab",
                    "应用已最小化到系统托盘。双击图标或右键菜单可恢复窗口。",
                )
                self._tray_hint_shown = True
            return
        if tray is not None:
            tray.disable()
        event.accept()

    def restore_from_tray(self, window: QMainWindow) -> None:
        window.showNormal()
        window.raise_()
        window.activateWindow()


__all__ = ["SystemTrayController"]
