"""
图标管理器 - Core 层兼容重导出

此模块已迁移至 app.ui.icon_manager。
保留此文件作为向后兼容的重导出入口。
"""

from app.ui.icon_manager import (
    IconManager,
    get_icon_manager,
    init_icon_manager,
    get_icon,
    get_multi_size_icon,
    set_icon_theme,
)

__all__ = [
    "IconManager",
    "get_icon_manager",
    "init_icon_manager",
    "get_icon",
    "get_multi_size_icon",
    "set_icon_theme",
]