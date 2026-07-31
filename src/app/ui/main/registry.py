#!/usr/bin/env python3
"""Page registry — single source of truth for nav + page metadata.

Pages must be registered exactly once. The Sidebar reads ``NAV_ITEMS`` to
render nav buttons; the PageRouter reads ``PAGE_BUILDERS`` to lazy-load
widgets on first navigation. ``PAGE_TITLES`` is the canonical (title,
breadcrumb) pair so the top bar never falls out of sync with the sidebar.

Add a new page in three steps:
    1. Create ``pages/<name>_page.py`` exposing a ``<Name>Page`` widget.
    2. Register a builder in :py:data:`PAGE_BUILDERS` (call
       :py:func:`_build_simple` if the page takes no ViewModel, or write a
       dedicated builder like :py:func:`_build_home` that wires a VM).
    3. Add a ``NavItem`` to ``NAV_ITEMS`` and a title to ``PAGE_TITLES``.

The lazy ``import`` inside each factory keeps startup cost flat and avoids
circular imports between pages.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from app.application import Application


@dataclass(frozen=True)
class NavItem:
    """Sidebar entry — id, display label, and optional tooltip.

    ``label_key`` / ``tooltip_key`` are preferred over the literal
    ``label`` / ``tooltip`` strings. When a key is provided the
    sidebar renders the translated string at draw time and
    refreshes it on language switch. The literal fields stay as a
    graceful fallback for tests and tools that bypass i18n.
    """

    id: str
    label: str = ""
    tooltip: str = ""
    label_key: str | None = None
    tooltip_key: str | None = None


@dataclass(frozen=True)
class PageSpec:
    """Page metadata — display title and breadcrumb for the top bar.

    Like :class:`NavItem`, translation keys take precedence and the
    literal fields serve as fallback for tests / non-i18n callers.
    """

    title: str = ""
    breadcrumb: str = ""
    title_key: str | None = None
    breadcrumb_key: str | None = None


# ─────────────────────────────────────────────────────────────────────
# Navigation sidebar entries (order = display order)
# ─────────────────────────────────────────────────────────────────────

NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem(
        "home",
        label="工作台",
        tooltip="项目总览和快速入口",
        label_key="nav.home",
        tooltip_key="nav.home.tooltip",
    ),
    NavItem(
        "create",
        label="创作流程",
        tooltip="素材 → 脚本 → 配音 → 导出",
        label_key="nav.production",
        tooltip_key="nav.production.tooltip",
    ),
    NavItem(
        "assets",
        label="项目资产",
        tooltip="导入素材和最近项目",
        label_key="nav.assets",
        tooltip_key="nav.assets.tooltip",
    ),
    NavItem(
        "settings",
        label="系统设置",
        tooltip="AI 服务、导出和行为",
        label_key="nav.settings",
        tooltip_key="nav.settings.tooltip",
    ),
    # 注："软件更新"页面仍由 PAGE_BUILDERS 注册，但不再作为侧栏项；
    # 用户改从顶部「帮助 → 检查更新」菜单访问，避免侧栏条目过多。
)


# ─────────────────────────────────────────────────────────────────────
# Page title + breadcrumb (consumed by TopBar)
# ─────────────────────────────────────────────────────────────────────

PAGE_TITLES: dict[str, PageSpec] = {
    "home": PageSpec(title="工作台", title_key="page.home"),
    "create": PageSpec(title="创作流程", title_key="page.production"),
    "assets": PageSpec(title="项目资产", title_key="page.assets"),
    "settings": PageSpec(title="系统设置", title_key="page.settings"),
    "update": PageSpec(title="软件更新", title_key="page.update"),
}


# ─────────────────────────────────────────────────────────────────────
# Lazy page factories (consumed by PageRouter)
# ─────────────────────────────────────────────────────────────────────

PageBuilder = Callable[["Application | None"], "QWidget"]


def _build_simple(module: str, attr: str) -> PageBuilder:
    """Build a no-arg page widget. Page takes no ViewModel yet."""

    def builder(app: Application | None) -> QWidget:  # noqa: ARG001
        import importlib

        cls = getattr(importlib.import_module(module), attr)
        return cls()

    return builder


def _build_home(app: Application | None) -> QWidget:
    """HomePage needs a ViewModel — wire it through here."""
    import importlib

    cls = importlib.import_module("app.ui.main.pages.home_page").HomePage
    if app is None:
        return cls()
    from app.ui.viewmodels.home_viewmodel import HomePageViewModel

    return cls(viewmodel=HomePageViewModel(application=app))


def _build_production(app: Application | None) -> QWidget:
    """ProductionPage needs a ViewModel — wire it through here (Phase 2B)."""
    import importlib

    cls = importlib.import_module(
        "app.ui.main.pages.production_page").ProductionPage
    if app is None:
        return cls()
    from app.ui.viewmodels.production_viewmodel import ProductionPageViewModel

    return cls(viewmodel=ProductionPageViewModel(application=app))


def _build_assets(app: Application | None) -> QWidget:
    """AssetsPage needs a ViewModel — wire it through here (Phase 2C)."""
    import importlib

    cls = importlib.import_module("app.ui.main.pages.assets_page").AssetsPage
    if app is None:
        return cls()
    from app.ui.viewmodels.assets_viewmodel import AssetsPageViewModel

    return cls(viewmodel=AssetsPageViewModel(application=app))


def _build_update(app: Application | None) -> QWidget:
    """UpdatePage wires a singleton UpdaterService (Phase 1, Task 3).

    The service is fetched from the DI container when ``app`` provides
    one; otherwise the page constructs its own default service so the
    navigator can still load the route in test contexts.
    """
    import importlib

    page_cls = importlib.import_module(
        "app.ui.main.pages.update_page").UpdatePage
    service = None
    if app is not None:
        service = app.get_service_by_name("updater_service")
    if service is None:
        try:
            from app.updater import UpdaterService

            service = UpdaterService.from_settings()
        except Exception:
            service = None
    if service is None:
        # Last-resort: page without service — UI is still navigable but
        # every action becomes a no-op.  Avoids hard failures when
        # running in environments where PySide6 is unavailable.
        return page_cls()
    return page_cls(service=service)


PAGE_BUILDERS: dict[str, PageBuilder] = {
    "home": _build_home,
    "create": _build_production,
    "assets": _build_assets,
    "settings": _build_simple(
        "app.ui.main.pages.settings_page", "SettingsPage"
    ),
    "update": _build_update,
}


__all__ = ["NAV_ITEMS", "PAGE_TITLES", "PAGE_BUILDERS", "NavItem", "PageSpec"]
