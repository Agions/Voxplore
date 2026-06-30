"""Tests for the Home page ViewModel binding.

Covers:
- Default state when no Application is provided (graceful fallback)
- VM updates emit the right signals
- View reflects VM state on construction
"""

from __future__ import annotations

import os

import pytest

PySide6 = pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal  # noqa: E402  (after pytest.importorskip)


class _MockProjectManager(QObject):
    """Bare-minimum stand-in for ProjectManager.

    Emits the same signals a real one would, so the ViewModel can
    subscribe without pulling in the full DI graph.
    """

    project_opened = Signal(str)
    project_closed = Signal(str)
    project_saved = Signal(str)
    recent_projects_updated = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.recent_projects: list[str] = []
        self._current = None

    def get_current_project(self):
        return self._current


class _MockApplication:
    """Returns a ProjectManager only when asked for it."""

    def __init__(self) -> None:
        self.pm = _MockProjectManager()

    def get_service(self, service_type):  # noqa: ARG002
        return self.pm


def test_vm_default_state_without_application() -> None:
    """No application injected → graceful fallback to 'no project' defaults."""
    from scenefab.ui.viewmodels.home_viewmodel import HomePageViewModel

    vm = HomePageViewModel(application=None)
    assert vm.media_count == 0
    assert vm.scene_count == 0
    assert vm.script_status == "待生成"
    assert vm.export_config == "1080x1920"
    assert vm.recent_projects == []


def test_vm_creation_with_application_does_not_crash() -> None:
    """Application is injected but PM has no project → fallback to defaults."""
    from scenefab.ui.viewmodels.home_viewmodel import HomePageViewModel

    app = _MockApplication()
    vm = HomePageViewModel(application=app)  # type: ignore[arg-type]
    vm.bind()
    try:
        assert vm.media_count == 0
        assert vm.scene_count == 0
        assert vm.script_status == "待生成"
    finally:
        vm.unbind()


def test_home_page_with_viewmodel_renders_status_cards() -> None:
    """HomePage(viewmodel=vm) shows VM state in its 4 status cards."""
    from PySide6.QtWidgets import QApplication  # type: ignore[attr-defined]

    from scenefab.ui.main.pages.home_page import HomePage
    from scenefab.ui.viewmodels.home_viewmodel import HomePageViewModel

    qt_app = QApplication.instance() or QApplication([])  # noqa: F841
    app = _MockApplication()
    vm = HomePageViewModel(application=app)  # type: ignore[arg-type]
    page = HomePage(viewmodel=vm)
    try:
        # 4 cards present
        assert len(page._status_cards) == 4
        # Default state propagates
        for _card, val, state, title in page._status_cards:
            if title == "素材":
                assert val.text() == "0"
                assert state.text() == "未导入"
            elif title == "场景":
                assert val.text() == "0"
                assert state.text() == "未拆分"
            elif title == "脚本":
                assert val.text() == "--"
                assert state.text() == "待生成"
            elif title == "导出":
                assert val.text() == "1080x1920"
                assert state.text() == "已配置"
    finally:
        page.deleteLater()


def test_home_page_without_viewmodel_uses_static_defaults() -> None:
    """Backward compat: HomePage() with no VM still renders the original look."""
    from PySide6.QtWidgets import QApplication  # type: ignore[attr-defined]

    from scenefab.ui.main.pages.home_page import HomePage

    qt_app = QApplication.instance() or QApplication([])  # noqa: F841
    page = HomePage()
    try:
        assert len(page._status_cards) == 4
        for _card, val, state, title in page._status_cards:
            if title == "素材":
                assert val.text() == "0"
                assert state.text() == "未导入"
    finally:
        page.deleteLater()
