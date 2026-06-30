#!/usr/bin/env python3
"""Page registry — single source of truth for nav + page metadata.

Pages must be registered exactly once. The Sidebar reads ``NAV_ITEMS`` to
render nav buttons; the PageRouter reads ``PAGE_BUILDERS`` to lazy-load
widgets on first navigation. ``PAGE_TITLES`` is the canonical (title,
breadcrumb) pair so the top bar never falls out of sync with the sidebar.

Add a new page in three steps:
    1. Create ``pages/<name>_page.py`` exposing a ``<Name>Page`` widget.
    2. Add a factory to ``PAGE_BUILDERS`` below.
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


@dataclass(frozen=True)
class NavItem:
    """Sidebar entry — id, display label, and optional tooltip."""

    id: str
    label: str
    tooltip: str = ""


@dataclass(frozen=True)
class PageSpec:
    """Page metadata — display title and breadcrumb for the top bar."""

    title: str
    breadcrumb: str = ""


# ─────────────────────────────────────────────────────────────────────
# Navigation sidebar entries (order = display order)
# ─────────────────────────────────────────────────────────────────────

NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem("home", "工作台", "项目总览和快速入口"),
    NavItem("create", "创作流程", "素材 → 脚本 → 配音 → 导出"),
    NavItem("assets", "项目资产", "导入素材和最近项目"),
    NavItem("settings", "系统设置", "AI 服务、导出和行为"),
)


# ─────────────────────────────────────────────────────────────────────
# Page title + breadcrumb (consumed by TopBar)
# ─────────────────────────────────────────────────────────────────────

PAGE_TITLES: dict[str, PageSpec] = {
    "home": PageSpec("工作台"),
    "create": PageSpec("创作流程"),
    "assets": PageSpec("项目资产"),
    "settings": PageSpec("系统设置"),
}


# ─────────────────────────────────────────────────────────────────────
# Lazy page factories (consumed by PageRouter)
# ─────────────────────────────────────────────────────────────────────

PageBuilder = Callable[[], "QWidget"]

PAGE_BUILDERS: dict[str, PageBuilder] = {
    "home": lambda: _import("scenefab.ui.main.pages.home_page", "HomePage")(),
    "create": lambda: _import(
        "scenefab.ui.main.pages.production_page", "ProductionPage"
    )(),
    "assets": lambda: _import(
        "scenefab.ui.main.pages.assets_page", "AssetsPage"
    )(),
    "settings": lambda: _import(
        "scenefab.ui.main.pages.settings_page", "SettingsPage"
    )(),
}


def _import(module: str, attr: str) -> type:
    """Lazy import helper — keeps registry import-cost flat."""
    import importlib

    value: type = getattr(importlib.import_module(module), attr)
    return value


__all__ = ["NAV_ITEMS", "PAGE_TITLES", "PAGE_BUILDERS", "NavItem", "PageSpec"]
