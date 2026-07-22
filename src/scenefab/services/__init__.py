"""SceneFab 服务模块。

包根只暴露命名，不主动导入视频、音频、AI 等重型实现。
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_SUBMODULES = {
    "ai",
    "export",
    "orchestration",
    "video",
    "video",
}

# Lazy-loaded names sourced from the canonical AI modules.
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "ServiceStatus": ("scenefab.services.ai.base", "ServiceStatus"),
    "ServiceHealth": ("scenefab.services.ai.base", "ServiceHealth"),
}


def __getattr__(name: str) -> Any:
    if name in _SUBMODULES:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module

    if name in _LAZY_IMPORTS:
        mod_path, attr = _LAZY_IMPORTS[name]
        module = import_module(mod_path)
        value = getattr(module, attr)
        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ai",
    "video",
    "export",
    "video",
    "orchestration",
    "ServiceStatus",
    "ServiceHealth",
]
