"""Tests for the Assets page (Issue #96: directory picker navigation).

PySide6-free tests (run in all environments):
- navigate signal contract (AssetsPage emits "settings" for navigable cards)
- ASSET_SOURCE_ITEMS / ASSET_TABLE_COLUMNS static contract
- page_view_models data model structure

PySide6 tests (skipped on headless Linux CI where QWidget construction
aborts the interpreter):
- Source-panel card structure (title/description labels)
- "选择目录" buttons present only for "素材目录"/"输出目录" cards
- Button click emits navigate("settings")
- Row rendering and refresh_projects / add_imported_files API
"""

from __future__ import annotations

import os
import sys

import pytest

# ── PySide6-free tests ──────────────────────────────────────────────────


def test_asset_source_items_contract():
    """ASSET_SOURCE_ITEMS exposes exactly 3 sources with expected labels."""
    from scenefab.ui.main.pages.page_view_models import ASSET_SOURCE_ITEMS

    assert len(ASSET_SOURCE_ITEMS) == 3
    labels = [item.label for item in ASSET_SOURCE_ITEMS]
    assert labels == ["素材目录", "输出目录", "资源规范"]


def test_asset_table_columns_contract():
    """ASSET_TABLE_COLUMNS is the documented 3-column header."""
    from scenefab.ui.main.pages.page_view_models import ASSET_TABLE_COLUMNS

    assert ASSET_TABLE_COLUMNS == ("类型", "名称", "创建日期")


def test_key_value_view_contract():
    """KeyValueView carries a label and a value."""
    from scenefab.ui.main.pages.page_view_models import (
        ASSET_SOURCE_ITEMS,
        KeyValueView,
    )

    item = ASSET_SOURCE_ITEMS[0]
    assert isinstance(item, KeyValueView)
    assert item.label == "素材目录"
    assert item.value == "未设置"


def test_assets_page_navigate_on_click_set():
    """AssetsPage._NAVIGATE_ON_CLICK lists exactly the two configurable dirs."""
    _src = (
        __import__("pathlib").Path(__file__).resolve()
        .parents[2]
        / "src"
        / "scenefab"
        / "ui"
        / "main"
        / "pages"
        / "assets_page.py"
    )
    # We can't execute the module (it imports PySide6), so verify the
    # constant contract by grepping the source.
    source = _src.read_text(encoding="utf-8")
    assert '_NAVIGATE_ON_CLICK = {"素材目录", "输出目录"}' in source


# ── PySide6 tests ───────────────────────────────────────────────────────

PySide6 = pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

_IN_CI = os.environ.get("CI", "").lower() == "true"

_SKIP_HEADLESS_WIDGET_TESTS = _IN_CI and (
    sys.platform == "linux"
    or os.environ.get("QT_QPA_PLATFORM") == "offscreen"
)


def _qt_app():
    return QApplication.instance() or QApplication([])


@pytest.mark.skipif(
    _SKIP_HEADLESS_WIDGET_TESTS,
    reason="AssetsPage(QWidget) 构造在无头 Linux CI 下触发解释器崩溃",
)
def test_assets_page_renders_three_source_cards():
    """AssetsPage builds exactly 3 source-panel cards."""
    from scenefab.ui.main.pages.assets_page import AssetsPage

    _qt_app()  # noqa: F841
    page = AssetsPage()
    try:
        cards = [
            child
            for child in page.findChildren(  # type: ignore[attr-defined]
                "QFrame"
            )
            if child.objectName() == "source_item"
        ]
        assert len(cards) == 3
    finally:
        page.deleteLater()


@pytest.mark.skipif(
    _SKIP_HEADLESS_WIDGET_TESTS,
    reason="AssetsPage(QWidget) 构造在无头 Linux CI 下触发解释器崩溃",
)
def test_assets_page_navigable_cards_have_button():
    """素材目录 and 输出目录 cards include a '选择目录' QPushButton."""
    from scenefab.ui.main.pages.assets_page import AssetsPage

    _qt_app()  # noqa: F841
    page = AssetsPage()
    try:
        cards = [
            child
            for child in page.findChildren(  # type: ignore[attr-defined]
                "QFrame"
            )
            if child.objectName() == "source_item"
        ]
        from PySide6.QtWidgets import QPushButton

        has_button = {
            [c.text() for c in card.findChildren("QLabel")][0]: card.findChildren(  # type: ignore[attr-defined]
                QPushButton
            )
            for card in cards
        }

        assert has_button["素材目录"], "素材目录 must have 选择目录 button"
        assert has_button["输出目录"], "输出目录 must have 选择目录 button"
        assert not has_button.get("资源规范", []), (
            "资源规范 must NOT have 选择目录 button"
        )
    finally:
        page.deleteLater()


@pytest.mark.skipif(
    _SKIP_HEADLESS_WIDGET_TESTS,
    reason="AssetsPage(QWidget) 构造在无头 Linux CI 下触发解释器崩溃",
)
def test_assets_page_button_click_emits_navigate_settings():
    """Clicking '选择目录' emits navigate('settings')."""
    from scenefab.ui.main.pages.assets_page import AssetsPage

    _qt_app()  # noqa: F841
    page = AssetsPage()
    try:
        from PySide6.QtWidgets import QPushButton

        emitted = []

        def on_nav(val: str) -> None:
            emitted.append(val)

        page.navigate.connect(on_nav)

        card = page.findChild(  # type: ignore[attr-defined]
            "QFrame", "source_item"
        )
        assert card is not None
        btn = card.findChild(QPushButton)
        assert btn is not None, "素材目录 card must contain a QPushButton"
        btn.click()
        assert emitted == ["settings"]
    finally:
        page.deleteLater()


@pytest.mark.skipif(
    _SKIP_HEADLESS_WIDGET_TESTS,
    reason="AssetsPage(QWidget) 构造在无头 Linux CI 下触发解释器崩溃",
)
def test_assets_page_rows_empty_without_project_manager():
    """Without a ProjectManager the page shows an empty state."""
    from scenefab.ui.main.pages.assets_page import AssetsPage

    _qt_app()  # noqa: F841
    page = AssetsPage()
    try:
        assert page._empty_state.isVisible()
        assert not page._rows_container.isVisible()
    finally:
        page.deleteLater()
