#!/usr/bin/env python3
"""Page router — extracted from SceneFabMainWindow.

Owns the ``ContentArea`` (a ``QStackedWidget``), the lazy page cache, and
navigation signals. Pages are constructed on first visit via the builders
declared in ``registry.PAGE_BUILDERS``.

The router emits ``page_changed`` with the page id whenever the active
page changes; the main window uses this to update the top-bar title.
"""

from __future__ import annotations

import logging
import traceback
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from scenefab.ui.main.main_window.content_area import ContentArea
from scenefab.ui.main.registry import PAGE_BUILDERS

if TYPE_CHECKING:
    from scenefab.application import Application

logger = logging.getLogger("SceneFab.ui.router")


class PageRouter(QObject):
    """Lazy page navigation over a single ``ContentArea``."""

    page_changed = Signal(str)

    def __init__(
        self,
        content: ContentArea,
        application: Application | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._content = content
        self._application = application
        self._page_map: dict[str, object] = {}

    def navigate(self, page_id: str, animated: bool = True) -> None:
        """Switch to ``page_id``; build the widget on first visit."""
        widget = self._page_map.get(page_id)
        if widget is None:
            builder = PAGE_BUILDERS.get(page_id)
            if builder is None:
                return
            try:
                widget = builder(self._application)
            except Exception:  # noqa: BLE001 — surface any page-build failure
                # 防御性兜底：页面构造失败时不再让异常被 Qt 槽吞掉而
                # 表现为“点击无反应”，而是记录日志并展示一个可见的
                # 错误占位页，便于用户与开发者定位问题。
                logger.exception("构建页面 %r 失败", page_id)
                widget = self._build_error_page(page_id, traceback.format_exc())
            self._page_map[page_id] = widget
            self._content.add_page(page_id, widget)
        self._content.set_page(page_id, animated=animated)
        self.page_changed.emit(page_id)

    @staticmethod
    def _build_error_page(page_id: str, tb: str) -> QWidget:
        """构造一个可见的错误占位页，避免页面构造崩溃时界面“假死”。"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)

        title = QLabel(f"页面加载失败：{page_id}")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #c0392b;")
        title.setWordWrap(True)
        layout.addWidget(title)

        hint = QLabel(
            "该页面在初始化时发生异常，已记录到运行日志。"
            "请将以下错误信息反馈给开发者，或尝试重启应用。"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        detail = QLabel(tb)
        detail.setWordWrap(True)
        detail.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        detail.setStyleSheet(
            "color: #555; background: #f7f7f7; padding: 12px; "
            "border: 1px solid #e0e0e0; border-radius: 6px;"
        )
        layout.addWidget(detail, 1)
        return page

    def cached_pages(self) -> list[str]:
        """List of pages that have been built so far (for tests / devtools)."""
        return list(self._page_map)


__all__ = ["PageRouter"]
