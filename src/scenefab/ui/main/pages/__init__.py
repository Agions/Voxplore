"""Production workspace pages."""

from typing import Any

_PAGE_MODULES = {
    "AssetsPage": ".assets_page",
    "HomePage": ".home_page",
    "ProductionPage": ".production_page",
    "SettingsPage": ".settings_page",
}


def __getattr__(name: str) -> Any:
    """Lazily import Qt pages so page data modules remain headless-safe."""
    if name in _PAGE_MODULES:
        from importlib import import_module

        module = import_module(_PAGE_MODULES[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AssetsPage",
    "HomePage",
    "ProductionPage",
    "SettingsPage",
]
