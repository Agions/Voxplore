#!/usr/bin/env python3
"""Tests for theme mode switching (Phase 3).

Covers:
- default_mode_is_light
- set_theme_mode_dark_rebinds_tokens
- set_theme_mode_light_resets_tokens
- set_theme_mode_unknown_falls_back_to_light
- get_theme_mode_returns_active
- light_and_dark_palettes_have_same_keys
- rebinding_is_idempotent
"""

from __future__ import annotations

import pytest

from scenefab.ui.theme.ds_tokens import (
    _C,
    Colors,
    DarkColors,
    get_theme_mode,
    set_theme_mode,
)


@pytest.fixture(autouse=True)
def reset_theme_mode():
    """Ensure each test starts in light mode (avoids state leak)."""
    set_theme_mode("light")
    yield
    set_theme_mode("light")


# ── 1. default mode is light ───────────────────────────────────────
def test_default_mode_is_light():
    """Fresh import → light mode is active."""
    assert get_theme_mode() == "light"
    assert _C.BG_BASE == Colors.BG_BASE  # "#f6f8fb"


# ── 2. set_theme_mode("dark") rebinds _C tokens ────────────────────
def test_set_theme_mode_dark_rebinds_tokens():
    """Switching to dark changes _C values to DarkColors."""
    set_theme_mode("dark")
    assert get_theme_mode() == "dark"
    # Spot-check a few colour tokens
    assert _C.BG_BASE == DarkColors.BG_BASE
    assert _C.TEXT_PRIMARY == DarkColors.TEXT_PRIMARY
    assert _C.PRIMARY == DarkColors.PRIMARY
    assert _C.BG_BASE != Colors.BG_BASE  # actually different


# ── 3. set_theme_mode("light") resets tokens ───────────────────────
def test_set_theme_mode_light_resets_tokens():
    """Switching back to light reverts tokens."""
    set_theme_mode("dark")
    set_theme_mode("light")
    assert get_theme_mode() == "light"
    assert _C.BG_BASE == Colors.BG_BASE
    assert _C.TEXT_PRIMARY == Colors.TEXT_PRIMARY


# ── 4. unknown mode falls back to light ────────────────────────────
def test_set_theme_mode_unknown_falls_back_to_light():
    """Unknown mode string → light, no exception."""
    result = set_theme_mode("neon-pink")
    assert result == "light"
    assert get_theme_mode() == "light"


# ── 5. light and dark palettes have matching keys ──────────────────
def test_light_and_dark_palettes_have_same_keys():
    """Colors and DarkColors must have identical attribute sets.

    Prevents a future contributor from adding a token to Colors but
    forgetting DarkColors (which would crash set_theme_mode with
    AttributeError mid-switch).
    """
    light_keys = {
        k
        for k in vars(Colors)
        if not k.startswith("_") and k.isupper()
    }
    dark_keys = {
        k
        for k in vars(DarkColors)
        if not k.startswith("_") and k.isupper()
    }
    missing = light_keys - dark_keys
    extra = dark_keys - light_keys
    assert not missing, f"DarkColors missing keys: {missing}"
    assert not extra, f"DarkColors has extra keys: {extra}"


# ── 6. rebinding is idempotent ─────────────────────────────────────
def test_rebinding_is_idempotent():
    """Calling set_theme_mode twice with the same mode is a no-op."""
    set_theme_mode("dark")
    bg1 = _C.BG_BASE
    set_theme_mode("dark")
    bg2 = _C.BG_BASE
    assert bg1 == bg2
    assert get_theme_mode() == "dark"


# ── 7. dark palette has meaningful values (not all same as light) ─
def test_dark_palette_differs_from_light():
    """DarkColors is not just an alias for Colors — at least the BG
    and text tokens must differ, otherwise the "dark" mode is a
    silent no-op.
    """
    assert DarkColors.BG_BASE != Colors.BG_BASE
    assert DarkColors.TEXT_PRIMARY != Colors.TEXT_PRIMARY
    assert DarkColors.BG_SURFACE != Colors.BG_SURFACE
