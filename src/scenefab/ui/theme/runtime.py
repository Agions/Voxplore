#!/usr/bin/env python3
"""
Runtime theme helpers.

These utilities are designed to be called *after* :func:`scenefab.ui.theme.ds_tokens.set_theme_mode`
has rebound ``_C``. They perform the second half of a theme switch:
forcing Qt widgets to re-read the QSS they were given at construction
time so the new palette actually shows up on screen.

Two pieces:

- :func:`restyle_app`
    Walks every live widget owned by the running ``QApplication`` and
    performs ``style().unpolish(w) / polish(w) / w.update()`` so any
    stylesheet using ``_C.X`` is reapplied with the new value.

- :class:`ThemeAwareMixin`
    For *individual* pages that own a stylesheet built from ``_C.X``
    (the common pattern in this codebase). After :func:`set_theme_mode`
    + :func:`restyle_app`, a page can additionally call
    :meth:`ThemeAwareMixin.apply_theme` to ``setStyleSheet`` itself
    again so any embedded template substitution picks up the new
    palette.

Both helpers are no-ops in headless / non-Qt environments (the Qt
import is deferred). Application code that wants runtime switching
should pair :func:`set_theme_mode` with :func:`restyle_app`:

::

    from scenefab.ui.theme import set_theme_mode, restyle_app

    set_theme_mode("dark")
    restyle_app()

or let each page :class:`ThemeAwareMixin.apply_theme` after the global
restyle.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import is unconditional at runtime
    from PySide6.QtWidgets import QApplication


def restyle_app(app: QApplication | None = None) -> int:
    """Force every live widget to re-read its stylesheet.

    Parameters
    ----------
    app : QApplication, optional
        The application instance to iterate. If ``None`` the
        :func:`QApplication.instance` singleton is used. Pass ``app``
        explicitly when running with more than one ``QApplication`` in
        the same process (mainly in test suites).

    Returns
    -------
    int
        The number of widgets that were re-polished. Zero when Qt is
        not available or no widgets exist (e.g. headless test).
    """
    try:
        from PySide6.QtWidgets import QApplication
    except Exception:  # pragma: no cover - PySide6 unavailable
        return 0

    app = app or QApplication.instance()
    if app is None or not isinstance(app, QApplication):
        return 0

    count = 0
    style = app.style()
    for widget in app.allWidgets():
        # C++ pointers that may have been freed between two calls if a
        # worker thread was repopulating the tree).
        try:
            style.unpolish(widget)
            style.polish(widget)
            widget.update()
        except RuntimeError:
            continue
        count += 1
    return count


class ThemeAwareMixin:
    """Mixin giving a :class:`QWidget`-style object a manual theme apply.

    Pages in this codebase typically build their stylesheet *once* at
    construction using :func:`scenefab.ui.theme.styles.build_stylesheet`
    (which references ``_C.X`` at evaluation time). After a palette
    change + :func:`restyle_app`, those already-built QStrings still
    contain the **old** colour literals — they need to be rebuilt.

    A page that stores its builder in ``self._build_stylesheet`` can
    simply ``self.apply_theme()`` and the stylesheet is regenerated
    and applied to the widget.

    The mixin intentionally has no ``__init__`` so it does not
    interfere with multiple-inheritance orderings. ``apply_theme``
    reads two attributes from ``self``:

    - ``self._build_stylesheet`` — ``Callable[[], str]`` returning the
      fresh QSS body. Required.
    - ``self.setStyleSheet`` — Qt widget method to receive the rebuilt
      body. Required.
    """

    _build_stylesheet: Callable[[], str]  #: populated by subclass

    def apply_theme(self) -> str:
        """Rebuild the stylesheet from ``self._build_stylesheet`` and apply it.

        Returns the rebuilt QSS so callers (mostly tests) can assert on it.
        The ``setStyleSheet`` call is type-ignored because ``self``
        is a mixin target whose concrete subclass brings the Qt method.
        """
        qss = self._build_stylesheet()
        self.setStyleSheet(qss)  # type: ignore[attr-defined]
        return qss


__all__ = [
    "restyle_app",
    "ThemeAwareMixin",
]
