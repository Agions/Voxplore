#!/usr/bin/env python3
"""Tests for UI page view-model data."""

from scenefab.services.ai.model_catalog import settings_model_options
from scenefab.ui.main.pages.page_defaults import DEFAULT_EXPORT_DIR
from scenefab.ui.main.pages.page_view_models import (
    ASSET_SOURCE_ITEMS,
    HOME_STATUS_CARDS,
    SETTINGS_GROUPS,
)


def test_page_view_models_are_headless_importable():
    assert HOME_STATUS_CARDS[0].title == "素材"
    assert ASSET_SOURCE_ITEMS[1].value == DEFAULT_EXPORT_DIR


def test_settings_model_options_use_catalog():
    ai_group = next(rows for title, rows in SETTINGS_GROUPS if title == "AI 服务")
    default_model = next(row for row in ai_group if row.key == "default_model")

    assert default_model.options == tuple(settings_model_options())
