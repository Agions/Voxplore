#!/usr/bin/env python3
"""Tests for UI page view-model data."""

from app.services.ai.model_catalog import settings_model_options
from app.ui.i18n import t
from app.ui.main.pages.page_defaults import DEFAULT_EXPORT_DIR
from app.ui.main.pages.page_view_models import (
    ASSET_SOURCE_ITEMS,
    ASSET_TABLE_COLUMNS,
    HOME_STATUS_CARDS,
    SETTINGS_GROUPS,
)


def test_page_view_models_are_headless_importable():
    # Home status cards expose i18n keys (not literal text) so the
    # language layer can re-translate the dashboard at runtime. The
    # legacy ``title`` field is kept as a backwards-compat fallback for
    # callers building a card from raw strings.
    first_card = HOME_STATUS_CARDS[0]
    assert first_card.title_key == "home.status.media"
    assert t(first_card.title_key) == "素材"

    # ``ASSET_SOURCE_ITEMS`` is now a tuple of ``(label_key, navigate_to,
    # value_key)`` tuples so the source panel can render translated text
    # on demand instead of baking a string into the view model.
    assert isinstance(ASSET_SOURCE_ITEMS, tuple)
    label_key, navigate_to, value_key = ASSET_SOURCE_ITEMS[1]
    assert label_key == "assets.source.export_dir"
    assert navigate_to == "settings"
    # The export_dir value placeholder must inject ``DEFAULT_EXPORT_DIR``
    # at render time — verify the i18n template contains a ``{path}``
    # slot and that substituting it produces the expected string.
    template = t(value_key)
    assert "{path}" in template
    rendered = template.format(path=DEFAULT_EXPORT_DIR)
    assert DEFAULT_EXPORT_DIR in rendered

    # Column header keys are plain i18n strings — they round-trip through
    # ``t()`` without losing the bracket-free layout.
    for key in ASSET_TABLE_COLUMNS:
        assert isinstance(t(key), str)
        assert t(key)  # non-empty


def test_settings_model_options_use_catalog():
    # ``SETTINGS_GROUPS`` now stores i18n keys for group titles and
    # resolves to the current language when the page renders, so we
    # match the AI group by its key and verify that ``default_model``
    # exposes a parallel ``options_keys`` tuple alongside the i18n
    # option strings.
    ai_group = next(
        rows for title_key, rows in SETTINGS_GROUPS
        if title_key == "settings.group.ai"
    )
    default_model = next(row for row in ai_group if row.key == "default_model")

    assert default_model.options == tuple(settings_model_options())
    assert default_model.options_keys == tuple(settings_model_options())
