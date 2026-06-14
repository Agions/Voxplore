"""SceneFab 服务模块。

包根只暴露命名，不主动导入视频、音频、AI 等重型实现。
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_SUBMODULES = {
    "ai",
    "audio",
    "export",
    "orchestration",
    "video",
    "video_tools",
}

_SERVICE_MANAGER_ATTRS = {
    "AIServiceManager": "AIServiceManagerCompat",
    "ServiceStatus": "ServiceStatus",
    "ServiceHealth": "ServiceHealth",
    "get_ai_service_manager": "get_ai_service_manager",
    "ServiceManager": "ServiceManager",
}


def __getattr__(name: str) -> Any:
    if name in _SUBMODULES:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module

    if name in _SERVICE_MANAGER_ATTRS:
        module = import_module(f"{__name__}.service_manager")
        value = getattr(module, _SERVICE_MANAGER_ATTRS[name])
        globals()[name] = value
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ai",
    "video",
    "audio",
    "export",
    "video_tools",
    "orchestration",
    "AIServiceManager",
    "ServiceStatus",
    "ServiceHealth",
    "get_ai_service_manager",
    "ServiceManager",
]
