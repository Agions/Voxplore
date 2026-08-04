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
    """ASSET_SOURCE_ITEMS exposes exactly 3 sources with expected structure.

    Each tuple is ``(label_key, navigate_to, value_key)`` so the view can
    retranslate without depending on hard-coded Chinese labels.
    """
    from app.ui.main.pages.page_view_models import ASSET_SOURCE_ITEMS

    assert len(ASSET_SOURCE_ITEMS) == 3
    label_keys = [item[0] for item in ASSET_SOURCE_ITEMS]
    assert label_keys == [
        "assets.source.media_dir",
        "assets.source.export_dir",
        "assets.source.resources",
    ]
    # First two are navigable (settings), third is informational
    nav_targets = [item[1] for item in ASSET_SOURCE_ITEMS]
    assert nav_targets == ["settings", "settings", None]
    # Value keys are distinct
    assert len({item[2] for item in ASSET_SOURCE_ITEMS}) == 3


def test_asset_table_columns_contract():
    """ASSET_TABLE_COLUMNS maps header cells to i18n keys (3-column table)."""
    from app.ui.main.pages.page_view_models import ASSET_TABLE_COLUMNS

    assert ASSET_TABLE_COLUMNS == (
        "assets.table.column.kind",
        "assets.table.column.name",
        "assets.table.column.created",
    )


def test_key_value_view_still_exported():
    """KeyValueView continues to exist for delivery / brief rows.

    The view now prefers ``label_key`` so consumers get re-translated
    text on language flips; the legacy ``label`` field is kept as a
    backwards-compat fallback for callers building the row from a raw
    string.
    """
    from app.ui.main.pages.page_view_models import (
        KeyValueView,
    )

    item = KeyValueView(label="foo", value="bar")
    assert item.label == "foo"
    assert item.value == "bar"

    item_with_key = KeyValueView(label_key="home.delivery.resolution",
                                 value="1080x1920")
    assert item_with_key.label_key == "home.delivery.resolution"
    assert item_with_key.label == ""


def test_assets_page_navigate_on_click_set():
    """ASSET_SOURCE_ITEMS flags the first two rows as navigating to settings.

    The previous ``_NAVIGATE_ON_CLICK`` class attribute has been replaced
    with a structured ``navigate_to`` field on the tuple so the page no
    longer depends on hard-coded Chinese titles.
    """
    from app.ui.main.pages.page_view_models import ASSET_SOURCE_ITEMS

    navigate_targets = [item[1] for item in ASSET_SOURCE_ITEMS]
    assert navigate_targets[:2] == ["settings", "settings"]
    assert navigate_targets[2] is None


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
    from PySide6.QtWidgets import QFrame

    from app.ui.main.pages.assets_page import AssetsPage

    _qt_app()  # noqa: F841
    page = AssetsPage()
    try:
        cards = [
            child
            for child in page.findChildren(QFrame)
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
    """The first two source cards (media_dir / export_dir) include a button."""
    from PySide6.QtWidgets import QFrame, QPushButton

    from app.ui.i18n import t
    from app.ui.main.pages.assets_page import AssetsPage
    from app.ui.main.pages.page_view_models import ASSET_SOURCE_ITEMS

    _qt_app()  # noqa: F841
    page = AssetsPage()
    try:
        cards = [
            child
            for child in page.findChildren(QFrame)
            if child.objectName() == "source_item"
        ]

        for index, card in enumerate(cards):
            label_key, nav, _value = ASSET_SOURCE_ITEMS[index]
            buttons = card.findChildren(QPushButton)
            if nav:
                assert buttons, f"{label_key} must have a Choose Folder button"
            else:
                assert not buttons, (
                    f"{label_key} must NOT have a Choose Folder button"
                )

        # Spot-check that labels are actually translated
        first_label = t(ASSET_SOURCE_ITEMS[0][0])
        assert isinstance(first_label, str) and first_label
    finally:
        page.deleteLater()


@pytest.mark.skipif(
    _SKIP_HEADLESS_WIDGET_TESTS,
    reason="AssetsPage(QWidget) 构造在无头 Linux CI 下触发解释器崩溃",
)
def test_assets_page_button_click_emits_navigate_settings():
    """Clicking '选择目录' emits navigate('settings')."""
    from PySide6.QtWidgets import QFrame, QPushButton

    from app.ui.main.pages.assets_page import AssetsPage

    _qt_app()  # noqa: F841
    page = AssetsPage()
    try:
        emitted = []

        def on_nav(val: str) -> None:
            emitted.append(val)

        page.navigate.connect(on_nav)

        card = page.findChild(QFrame, "source_item")
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
    from app.ui.main.pages.assets_page import AssetsPage

    _qt_app()  # noqa: F841
    page = AssetsPage()
    try:
        assert not page._empty_state_widget.isHidden()
        assert page._rows_container.isHidden()
    finally:
        page.deleteLater()
