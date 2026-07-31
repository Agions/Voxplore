#!/usr/bin/env python3
"""Unit tests for the three-state ThemeManager."""

from __future__ import annotations

import pytest

try:
    from app.ui.theme import theme_manager as theme_module
    from app.ui.theme.theme_manager import ThemeManager, ThemeMode
except (ImportError, OSError) as exc:
    pytest.skip(
        f"PySide6 theme runtime unavailable: {exc}", allow_module_level=True)


class _FakeSettings:
    values: dict[str, str] = {}

    def __init__(self, *_args) -> None:
        pass

    def value(self, key: str, default=None, type=None):  # noqa: A002
        value = self.values.get(key, default)
        return type(value) if type is not None else value

    def setValue(self, key: str, value: str) -> None:  # noqa: N802
        self.values[key] = value


@pytest.fixture(autouse=True)
def isolate_theme(monkeypatch):
    _FakeSettings.values = {}
    applied: list[str] = []
    monkeypatch.setattr(theme_module, "QSettings", _FakeSettings)
    monkeypatch.setattr(theme_module, "set_theme_mode", applied.append)
    monkeypatch.setattr(
        ThemeManager, "_query_system_palette", lambda self: "light")
    yield applied


def test_theme_modes_have_stable_persisted_values():
    assert [mode.value for mode in ThemeMode] == ["system", "light", "dark"]


def test_set_mode_applies_palette_emits_and_persists(isolate_theme):
    manager = ThemeManager()
    palettes: list[str] = []
    modes: list[ThemeMode] = []
    manager.palette_changed.connect(palettes.append)
    manager.mode_changed.connect(modes.append)

    manager.set_mode(ThemeMode.DARK)

    assert manager.mode() is ThemeMode.DARK
    assert manager.current_palette() == "dark"
    assert isolate_theme[-1] == "dark"
    assert palettes == ["dark"]
    assert modes == [ThemeMode.DARK]
    assert _FakeSettings.values["appearance/theme_mode"] == "dark"


def test_unknown_mode_falls_back_to_system(isolate_theme):
    manager = ThemeManager()
    manager.set_mode("not-a-theme")

    assert manager.mode() is ThemeMode.SYSTEM
    assert manager.current_palette() == "light"
    assert isolate_theme == []


def test_apply_persisted_restores_without_rewriting(monkeypatch, isolate_theme):
    _FakeSettings.values["appearance/theme_mode"] = "dark"
    manager = ThemeManager()
    manager.apply_persisted()

    assert manager.mode() is ThemeMode.DARK
    assert manager.current_palette() == "dark"
    assert isolate_theme[-1] == "dark"
    assert _FakeSettings.values == {"appearance/theme_mode": "dark"}


def test_system_change_only_applies_in_system_mode(monkeypatch, isolate_theme):
    palette = {"value": "light"}
    monkeypatch.setattr(
        ThemeManager, "_query_system_palette", lambda self: palette["value"]
    )
    manager = ThemeManager()
    manager.apply_persisted()

    palette["value"] = "dark"
    manager._on_system_change(None)
    assert manager.current_palette() == "dark"

    manager.set_mode("light")
    palette["value"] = "dark"
    manager._on_system_change(None)
    assert manager.current_palette() == "light"
