"""Main-window smoke tests.

These tests are skipped in headless Python environments without PySide6, but
run in desktop/CI images that provide the Qt runtime.
"""

from __future__ import annotations

import os
import sys

import pytest

_IN_CI = os.environ.get("CI", "").lower() == "true"
_SKIP_HEADLESS_WIDGET_TESTS = _IN_CI and (
    sys.platform == "linux"
    or os.environ.get("QT_QPA_PLATFORM") == "offscreen"
)


@pytest.mark.skipif(
    _SKIP_HEADLESS_WIDGET_TESTS,
    reason="SceneFabMainWindow(QWidget) 构造在无头 Linux CI 下触发解释器崩溃",
)
def test_main_window_registers_production_pages() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    # 即使 PySide6 已安装，无头 CI 镜像可能缺少 Qt 所需的系统 GL 库
    # （如 libEGL.so.1）。这属于环境缺失而非代码缺陷，跳过而非失败。
    try:
        from PySide6.QtWidgets import QApplication

        from app.ui.main.main_window import SceneFabMainWindow

        app = QApplication.instance() or QApplication([])
    except ImportError as e:
        pytest.skip(f"Qt runtime libraries unavailable: {e}")

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
