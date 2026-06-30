#!/usr/bin/env python3
"""Page router — extracted from SceneFabMainWindow.

Owns the ``ContentArea`` (a ``QStackedWidget``), the lazy page cache, and
navigation signals. Pages are constructed on first visit via the builders
declared in ``registry.PAGE_BUILDERS``.

The router emits ``page_changed`` with the page id whenever the active
page changes; the main window uses this to update the top-bar title.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from scenefab.ui.main.main_window.content_area import ContentArea
from scenefab.ui.main.registry import PAGE_BUILDERS


class PageRouter(QObject):
    """Lazy page navigation over a single ``ContentArea``."""

    page_changed = Signal(str)

    def __init__(self, content: ContentArea, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._content = content
        self._page_map: dict[str, object] = {}

    def navigate(self, page_id: str, animated: bool = True) -> None:
        """Switch to ``page_id``; build the widget on first visit."""
        widget = self._page_map.get(page_id)
        if widget is None:
            builder = PAGE_BUILDERS.get(page_id)
            if builder is None:
                return
            widget = builder()
            self._page_map[page_id] = widget
            self._content.add_page(page_id, widget)
        self._content.set_page(page_id, animated=animated)
        self.page_changed.emit(page_id)

    def cached_pages(self) -> list[str]:
        """List of pages that have been built so far (for tests / devtools)."""
        return list(self._page_map)


__all__ = ["PageRouter"]
