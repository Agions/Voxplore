#!/usr/bin/env python3
"""
macOS 苹果原生视觉字体加载与注册管理器 (Font Loader)

功能:
- 动态扫描 resources/fonts 字体包目录并挂载 `.otf` / `.ttf` 字体文件
- 通过 QFontDatabase 向 PySide6 渲染引擎注册 SF Pro Text, SF Pro Display, PingFang SC 苹方字族
- 提供统一的高清晰度 ui_font() 构造器，确保跨平台与 macOS 统一原生质感
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 首选苹果 macOS 原生字体族
PREFERRED_FONT_FAMILIES = [
    "SF Pro Text",
    "SF Pro Display",
    "PingFang SC",
    "Helvetica Neue",
    "Arial",
]

_FONTS_INITIALIZED = False


def init_application_fonts(custom_dir: str | Path | None = None) -> int:
    """
    初始化并注册应用字体包
    
    Args:
        custom_dir: 自定义字体包路径（默认读取 resources/fonts）
        
    Returns:
        成功挂载的字体文件数量
    """
    global _FONTS_INITIALIZED
    if _FONTS_INITIALIZED:
        return 0

    try:
        from PySide6.QtGui import QFontDatabase
    except ImportError:
        logger.debug("PySide6 不可用，跳过应用字体包注册")
        return 0

    font_dir = Path(custom_dir) if custom_dir else Path(__file__).resolve().parents[3] / "resources" / "fonts"
    if not font_dir.exists():
        logger.debug(f"字体包目录不存在: {font_dir}")
        return 0

    loaded_count = 0
    font_extensions = (".otf", ".ttf", ".ttc")
    for font_file in font_dir.iterdir():
        if font_file.suffix.lower() in font_extensions:
            font_id = QFontDatabase.addApplicationFont(str(font_file))
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                logger.info(f"成功挂载字体包: {font_file.name} -> {families}")
                loaded_count += 1
            else:
                logger.warning(f"挂载字体包失败: {font_file.name}")

    _FONTS_INITIALIZED = True
    return loaded_count
