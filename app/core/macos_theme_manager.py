"""
macOS 主题管理器 - Core 层兼容重导出

此模块已迁移至 app.ui.macos_theme_manager。
保留此文件作为向后兼容的重导出入口。
"""

from app.ui.macos_theme_manager import (
    MacOSThemeManager,
    get_theme_manager,
    apply_macos_theme,
)

__all__ = [
    "MacOSThemeManager",
    "get_theme_manager",
    "apply_macos_theme",
]