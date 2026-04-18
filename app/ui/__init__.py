"""
Voxplore UI 模块

提供 PySide6 图形界面组件
"""

from .main.main_window import VoxploreWindow
from .main.main_window import VoxploreWindow as MainWindow

__all__ = [
    "MainWindow",
    "VoxploreWindow",
]
