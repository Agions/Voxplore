"""
Voxplore UI Windows
多窗口架构：主窗口 + 步骤子窗口 + 项目列表窗口
"""

from .base_step_window import BaseStepWindow
from .upload_window import UploadWindow
from .scene_window import SceneWindow
from .narration_window import NarrationWindow
from .export_window import ExportWindow
from .main_window import MainWindow, VoxploreApp
from .projects_window import ProjectsWindow, ProjectCard

__all__ = [
    "BaseStepWindow",
    "UploadWindow",
    "SceneWindow",
    "NarrationWindow",
    "ExportWindow",
    "MainWindow",
    "VoxploreApp",
    "ProjectsWindow",
    "ProjectCard",
]
