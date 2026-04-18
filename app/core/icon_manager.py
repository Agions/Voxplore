#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 图标管理器
提供统一的图标加载和管理功能
支持自定义图标和 PyQt 标准图标
"""

from typing import Optional, Dict
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication


# PyQt 标准图标映射
STANDARD_ICONS = {
    "home": "SP_DesktopIcon",
    "settings": "SP_SettingsIcon",
    "video": "SP_MediaPlay",
    "chat": "SP_MessageBoxInformation",
    "projects": "SP_DirIcon",
    "new": "SP_FileIcon",
    "import": "SP_DirOpenIcon",
    "export": "SP_DriveHDIcon",
    "document": "SP_FileDialogDetailedView",
    "globe": "SP_NetworkIcon",
    "refresh": "SP_BrowserReload",
    "save": "SP_DriveHDIcon",
    "open": "SP_DirOpenIcon",
    "close": "SP_TitleBarCloseButton",
    "minimize": "SP_TitleBarMinButton",
    "maximize": "SP_TitleBarMaxButton",
    "restore": "SP_TitleBarNormalButton",
    "delete": "SP_TrashIcon",
    "edit": "SP_FileDialogInfoView",
    "search": "SP_FileDialogContentsView",
    "folder": "SP_DirClosedIcon",
    "file": "SP_FileIcon",
}


class IconManager:
    """图标管理器 - 支持自定义图标和 PyQt 标准图标"""

    def __init__(self, icon_dir: Optional[str] = None):
        self.icon_dir = Path(icon_dir or "resources/icons")
        self._icon_cache: Dict[str, QIcon] = {}
        self._current_theme = "light"

    def get_icon(self, icon_name: str, size: int = 24, theme: Optional[str] = None) -> QIcon:
        """获取图标"""
        if theme is None:
            theme = self._current_theme

        cache_key = f"{icon_name}_{size}_{theme}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        icon = self._load_icon(icon_name, size, theme)
        self._icon_cache[cache_key] = icon
        return icon

    def _load_icon(self, icon_name: str, size: int, theme: str) -> QIcon:
        """加载图标 - 优先使用自定义图标，回退到标准图标"""
        # 尝试加载自定义图标
        custom_icon = self._load_custom_icon(icon_name, size, theme)
        if not custom_icon.isNull():
            return custom_icon

        # 回退到 PyQt 标准图标
        return self._get_standard_icon(icon_name, size)

    def _load_custom_icon(self, icon_name: str, size: int, theme: str) -> QIcon:
        """加载自定义图标"""
        # 尝试多种路径格式
        search_paths = [
            self.icon_dir / f"{icon_name}_{size}.png",
            self.icon_dir / f"{icon_name}.png",
            self.icon_dir / theme / f"{icon_name}_{size}.png",
            self.icon_dir / theme / f"{icon_name}.png",
        ]

        for path in search_paths:
            if path.exists():
                return QIcon(str(path))

        return QIcon()

    def _get_standard_icon(self, icon_name: str, size: int) -> QIcon:
        """获取 PyQt 标准图标"""
        from PySide6.QtWidgets import QStyle

        if not QApplication.instance():
            return QIcon()

        style = QApplication.style()
        qt_icon_name = STANDARD_ICONS.get(icon_name, "SP_FileIcon")

        try:
            icon_enum = getattr(QStyle.StandardPixmap, qt_icon_name)
            return style.standardIcon(icon_enum)
        except (AttributeError, ValueError):
            # 如果找不到，返回空图标
            return QIcon()

    def get_multi_size_icon(self, icon_name: str, theme: Optional[str] = None) -> QIcon:
        """获取多尺寸图标 - 用于应用图标"""
        if theme is None:
            theme = self._current_theme

        cache_key = f"{icon_name}_multi_{theme}"
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        # 尝试加载自定义多尺寸图标
        icon = self._load_custom_multi_size_icon(icon_name, theme)
        if not icon.isNull():
            self._icon_cache[cache_key] = icon
            return icon

        # 回退到加载单尺寸
        icon = self._load_custom_icon(icon_name, 256, theme)
        if not icon.isNull():
            self._icon_cache[cache_key] = icon
            return icon

        # 最后回退到标准图标
        icon = self._get_standard_icon(icon_name, 256)
        self._icon_cache[cache_key] = icon
        return icon

    def _load_custom_multi_size_icon(self, icon_name: str, theme: str) -> QIcon:
        """加载自定义多尺寸图标"""
        icon = QIcon()
        sizes = [16, 32, 64, 128, 256, 512]

        for size in sizes:
            # 尝试多种命名格式
            for pattern in [f"{icon_name}_{size}.png", f"{icon_name}.png"]:
                path = self.icon_dir / pattern
                if path.exists():
                    pixmap = QIcon(str(path)).pixmap(QSize(size, size))
                    if not pixmap.isNull():
                        icon.addPixmap(pixmap)

        return icon

    def set_theme(self, theme: str):
        """设置主题"""
        if theme in ["light", "dark", "high_contrast"]:
            self._current_theme = theme
            self._icon_cache.clear()

    def clear_cache(self):
        """清除图标缓存"""
        self._icon_cache.clear()

    def get_app_icon(self) -> QIcon:
        """获取应用图标"""
        return self.get_multi_size_icon("app_icon")


# 全局图标管理器实例
_icon_manager: Optional[IconManager] = None


def get_icon_manager(icon_dir: Optional[str] = None) -> IconManager:
    """获取全局图标管理器"""
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = IconManager(icon_dir)
    return _icon_manager


def init_icon_manager(icon_dir: str) -> IconManager:
    """初始化图标管理器"""
    global _icon_manager
    _icon_manager = IconManager(icon_dir)
    return _icon_manager


# 便捷函数
def get_icon(icon_name: str, size: int = 24, theme: Optional[str] = None) -> QIcon:
    """获取图标的便捷函数"""
    manager = get_icon_manager()
    return manager.get_icon(icon_name, size, theme)


def get_multi_size_icon(icon_name: str, theme: Optional[str] = None) -> QIcon:
    """获取多尺寸图标的便捷函数"""
    manager = get_icon_manager()
    return manager.get_multi_size_icon(icon_name, theme)


def set_icon_theme(theme: str):
    """设置图标主题的便捷函数"""
    manager = get_icon_manager()
    manager.set_theme(theme)
