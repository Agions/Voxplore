#!/usr/bin/env python3
"""
UI theme package.

Three layers:

- :mod:`scenefab.ui.theme.ds_tokens`
    Pure-python design tokens (Colours / Radii / Spacing / Shadows / etc.)
    + the :func:`set_theme_mode` API that rebinds :data:`_C` so existing
    ``_C.X`` references pick up the new palette without re-import.

- :mod:`scenefab.ui.theme.styles`
    QSS builder / fragments which read from :data:`_C` at *render time*
    so theme changes automatically apply through the
    :class:`ThemeAwareMixin`.

- :mod:`scenefab.ui.theme.runtime`
    Runtime helpers that live above tokens and styles:
    :func:`restyle_app` (re-polish every widget after a palette switch)
    and :class:`ThemeAwareMixin` (turn-on/off + reapply the local
    stylesheet for a single page). *Depends on PySide6* — only import
    from application code, never from pure data modules.
"""

from __future__ import annotations

from .ds_tokens import (
    _C,
    Colors,
    DarkColors,
    Durations,
    Easings,
    FontSizes,
    FontWeights,
    QSSComponents,
    Radii,
    Shadows,
    Spacing,
    get_theme_mode,
    set_theme_mode,
)
from .runtime import ThemeAwareMixin, restyle_app

__all__ = [
    # tokens
    "Colors",
    "DarkColors",
    "FontSizes",
    "FontWeights",
    "Spacing",
    "Radii",
    "Shadows",
    "Durations",
    "Easings",
    "QSSComponents",
    "_C",
    "set_theme_mode",
    "get_theme_mode",
    # runtime helpers
    "ThemeAwareMixin",
    "restyle_app",
]
