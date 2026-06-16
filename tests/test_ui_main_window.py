"""Main-window smoke tests.

These tests are skipped in headless Python environments without PySide6, but
run in desktop/CI images that provide the Qt runtime.
"""

from __future__ import annotations

import os

import pytest


def test_main_window_registers_production_pages() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    from scenefab.ui.main.main_window import SceneFabMainWindow

    app = QApplication.instance() or QApplication([])
    window = SceneFabMainWindow()
    try:
        assert window.windowTitle() == "SceneFab"
        assert set(window.content._page_map) == {
            "home",
            "create",
            "assets",
            "settings",
        }
        assert window.content._stack.count() == 4
    finally:
        window.close()
        app.quit()
