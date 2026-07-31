"""Theme controller for the main window.

A thin bridge between :class:`~app.ui.theme.theme_manager.ThemeManager`
and the main window. It owns:

- the ``palette_changed`` listener that rebuilds the QSS stack
  (main window + every page) when the active palette flips,
- the ``apply_persisted()`` call that runs at window startup so the
  first frame already renders in the user's chosen palette.

Extracted from ``SceneFabMainWindow`` as part of the Phase B
single-responsibility refactor (plan §4.5 — seventh controller).

The controller is intentionally a :class:`QObject` so it can forward
``palette_changed`` as a Qt signal in addition to letting callers hook
up via :py:meth:`set_palette_hook`. Signals also keep the lifetime
explicit (the parent ``QMainWindow`` owns the controller).
"""

from __future__ import annotations

import logging
from typing import Callable, Iterable

from PySide6.QtCore import QObject, Signal

from app.ui.theme import restyle_app
from app.ui.theme.theme_manager import ThemeManager

logger = logging.getLogger(__name__)


__all__ = ["ThemeController"]


PageLike = object  # anything with an optional ``apply_theme`` method
RouterLike = object  # anything exposing ``_page_map`` (a dict[str, PageLike])


class ThemeController(QObject):
    """Forward ThemeManager palette changes to the restyle layer.

    Parameters
    ----------
    theme_manager : ThemeManager
        The state-machine manager that emits ``palette_changed``.
    router : RouterLike | None
        Optional page-router — when provided, every page with an
        ``apply_theme`` callable is restyled on palette flips.
    hook : Callable[[str], None] | None
        Optional additional hook (e.g. main window's own
        ``apply_theme``). Invoked *before* page restyle.
    parent : QObject | None
        Standard Qt parent for ownership.
    """

    palette_changed = Signal(str)  # mirrors ThemeManager.palette_changed

    def __init__(
        self,
        theme_manager: ThemeManager,
        router: RouterLike | None = None,
        *,
        hook: Callable[[str], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._theme_manager = theme_manager
        self._router = router
        self._hook = hook

        # Bridge ThemeManager.palette_changed → local signal AND run
        # the restyle pipeline. The connect happens once here so the
        # main window doesn't have to remember to wire it up.
        self._theme_manager.palette_changed.connect(self._on_palette_changed)

    # ──────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────

    def apply_persisted(self) -> None:
        """Restore the persisted theme mode and apply it.

        Must be called once after the main window's QSS stack has been
        built so the very first paint matches the user's preference.
        """
        self._theme_manager.apply_persisted()

    def set_router(self, router: RouterLike) -> None:
        """Late-wire the page router (used when the router is created
        after the controller in the main window's ``_setup_ui``).
        """
        self._router = router

    def set_hook(self, hook: Callable[[str], None]) -> None:
        """Install or replace the main-window-level restyle hook."""
        self._hook = hook

    def restyle_pages(self, pages: Iterable[PageLike]) -> None:
        """Iterate ``pages`` and refresh each one for the new palette.

        For every page we try the strictest refresh path first and fall
        back to progressively simpler ones so a missing
        ``apply_theme`` doesn't leave the page visually stuck on the old
        palette:

        1. ``apply_theme()`` — the canonical :class:`ThemeAwareMixin`
           entry point (e.g. ``SettingsPage``).
        2. ``_setup_style()`` — the convention used by every business
           page in this codebase (``HomePage`` / ``ProductionPage`` /
           ``AssetsPage``). Each method only writes a stylesheet, so it
           is safe to invoke repeatedly without rebuilding the layout
           or losing widget state.
        3. ``restyle_app()`` — the global QSS polish pass that catches
           any widget that doesn't expose either of the above.

        Errors on any single page are swallowed so one buggy page
        does not break the whole palette switch.
        """
        for page in pages:
            apply_palette = getattr(page, "apply_palette", None)
            if callable(apply_palette):
                try:
                    apply_palette()
                except Exception:  # pragma: no cover — defensive
                    logger.debug(
                        "%s.apply_palette 失败",
                        type(page).__name__,
                        exc_info=True,
                    )

            apply = getattr(page, "apply_theme", None)
            if callable(apply):
                try:
                    apply()
                    continue
                except Exception:  # pragma: no cover — defensive
                    logger.debug(
                        "%s.apply_theme 失败，回退到 _setup_style",
                        type(page).__name__,
                        exc_info=True,
                    )

            setup_style = getattr(page, "_setup_style", None)
            if callable(setup_style):
                try:
                    setup_style()
                    continue
                except Exception:  # pragma: no cover — defensive
                    logger.debug(
                        "%s._setup_style 失败",
                        type(page).__name__,
                        exc_info=True,
                    )

            # No refresh path available — the global restyle pass below
            # will still unpolish/polish every widget so the page picks
            # up *some* palette change.
            logger.debug(
                "%s 未暴露 apply_theme 或 _setup_style，跳过 page-level refresh",
                type(page).__name__,
            )

    # ──────────────────────────────────────────────────────────
    # Internal: palette change pipeline
    # ──────────────────────────────────────────────────────────

    def _on_palette_changed(self, palette: str) -> None:
        """Run the full restyle: optional hook → pages → app-wide restyle.

        The :class:`SceneFabMainWindow` is registered as a ``hook`` and
        its ``apply_theme`` reissues the main-window stylesheet + every
        chrome widget (sidebar / topbar / statusbar / nav buttons) using
        the freshly rebound ``_C.*`` tokens. Pages are then walked via
        :meth:`restyle_pages`. Finally :func:`restyle_app` unpolishes /
        polishes the entire QApplication tree so any widget that owns a
        raw ``_C.X`` stylesheet (e.g. system dialogs) re-evaluates too.
        """
        if self._hook is not None:
            try:
                self._hook(palette)
            except Exception:  # pragma: no cover — defensive
                logger.debug("主题 hook 失败", exc_info=True)

        if self._router is not None:
            page_map = getattr(self._router, "_page_map", None)
            if isinstance(page_map, dict):
                self.restyle_pages(page_map.values())

        try:
            restyle_app()
        except Exception:  # pragma: no cover — defensive
            logger.debug("restyle_app 失败", exc_info=True)
