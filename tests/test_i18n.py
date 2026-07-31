#!/usr/bin/env python3
"""Unit tests for the dictionary-based UI translator."""

from __future__ import annotations

import pytest

try:
    from app.ui.i18n import ALL_MESSAGE_KEYS, Translator, available_languages
    from app.ui.i18n.messages_en_US import MESSAGES as EN_MESSAGES
    from app.ui.i18n.messages_zh_CN import MESSAGES as ZH_MESSAGES
except (ImportError, OSError) as exc:
    pytest.skip(f"PySide6 i18n runtime unavailable: {exc}", allow_module_level=True)


def test_catalogs_and_declared_keys_have_exact_parity():
    assert set(ZH_MESSAGES) == set(EN_MESSAGES)
    assert set(ZH_MESSAGES) == set(ALL_MESSAGE_KEYS)


def test_lookup_and_formatting_in_both_languages():
    translator = Translator("zh-CN")
    assert translator.tr("common.save") == "保存"
    assert translator.tr("assets.import.done", count=3) == "已选择 3 个素材文件"

    assert translator.set_language("en-US") is True
    assert translator.tr("common.save") == "Save"
    assert translator.tr("assets.import.done", count=3) == "Selected 3 media files"


def test_missing_key_has_visible_fallback():
    translator = Translator()
    assert translator.tr("missing.example") == "[missing.example]"
    assert translator.tr("missing.example", default="Fallback") == "Fallback"


def test_invalid_language_is_rejected_without_state_change():
    translator = Translator("zh-CN")

    assert translator.set_language("ja-JP") is False
    assert translator.language() == "zh-CN"


def test_language_changed_emits_only_for_real_change():
    translator = Translator("zh-CN")
    changed: list[str] = []
    translator.language_changed.connect(changed.append)

    assert translator.set_language("zh-CN") is False
    assert translator.set_language("en-US") is True
    assert changed == ["en-US"]


def test_catalog_has_no_missing_keys():
    for language in ("zh-CN", "en-US"):
        assert Translator(language).missing_keys() == []


def test_available_languages_are_stable_and_user_facing():
    assert available_languages() == [("zh-CN", "简体中文"), ("en-US", "English")]
