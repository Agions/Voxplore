"""
MainWindow 常量和配置
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class PageType(Enum):
    """页面类型"""
    HOME = "home"
    SETTINGS = "settings"
    PROJECTS = "projects"
    VIDEO_EDITOR = "video_editor"
    AI_VIDEO_CREATOR = "ai_video_creator"
    AI_CONFIG = "ai_config"
    AI_CHAT = "ai_chat"


@dataclass
class WindowConfig:
    """窗口配置"""
    title: str = "Voxplore"
    width: int = 1200
    height: int = 800
    min_width: int = 800
    min_height: int = 600
    icon_path: Optional[str] = None
    style: str = "Fusion"
