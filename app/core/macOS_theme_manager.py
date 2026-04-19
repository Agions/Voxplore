#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
macOS 主题管理器 - 负责应用和切换 macOS 设计系统
实现动态主题管理、资源加载和状态同步
"""

import logging
from pathlib import Path
from threading import Lock
from typing import Optional
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QTextStream, Signal, QObject
from PySide6.QtGui import QFont


class macOS_ThemeManager(QObject):
    """macOS 设计系统主题管理器"""

    # 信号
    theme_changed = Signal(str)      # 主题切换信号
    before_apply = Signal()          # 样式应用前
    after_apply = Signal()           # 样式应用后

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.current_theme = "dark"
        self._cache = {}
        self._fallback_stylesheet = ""
        self.logger = logging.getLogger(__name__)

        # 获取项目根目录
        self.project_root = Path(__file__).parent.parent.parent
        self.styles_dir = self.project_root / "resources" / "styles" / "macOS"

        self.logger.info("macOS Theme Manager 初始化")

    def load_system(self, theme: str = "dark") -> bool:
        """加载 macOS 设计系统"""
        self.logger.info(f"加载 macOS 设计系统 ({theme} 模式)")

        self.before_apply.emit()

        try:
            # 优先使用 QSS 资源文件
            stylesheet = self._load_from_resources(theme)

            # 如果资源不可用，使用文件系统
            if not stylesheet:
                stylesheet = self._load_from_filesystem(theme)

            # 如果依然失败，使用回退样式
            if not stylesheet:
                self.logger.warning("无法加载样式，使用回退样式")
                stylesheet = self._get_fallback_style()

            # 应用样式
            self.app.setStyleSheet(stylesheet)
            self.current_theme = theme

            # 设置应用字体
            self._set_app_font()

            self.after_apply.emit()
            self.theme_changed.emit(theme)

            self.logger.info("macOS 设计系统应用成功")
            return True

        except Exception as e:
            self.logger.error(f"设计系统应用失败: {e}")
            return False

    def _load_from_resources(self, theme: str) -> str:
        """尝试从 Qt 资源加载"""
        if theme == "dark":
            resource_path = ":/styles/macOS/macOS_desktop_stylesheet.qss"
        else:
            resource_path = f":/styles/macOS/macOS_{theme}.qss"

        if resource_path in self._cache:
            return self._cache[resource_path]

        file = QFile(resource_path)
        if file.exists() and file.open(QFile.ReadOnly | QFile.Text):
            content = QTextStream(file).readAll()
            file.close()
            self._cache[resource_path] = content
            return content

        return ""

    def _load_from_filesystem(self, theme: str) -> str:
        """从文件系统加载"""
        if theme == "dark":
            file_path = self.styles_dir / "macOS_desktop_stylesheet.qss"
        else:
            file_path = self.styles_dir / f"macOS_{theme}.qss"

        if file_path.exists():
            content = file_path.read_text(encoding='utf-8')
            self._cache[str(file_path)] = content
            return content

        self.logger.warning(f"文件不存在: {file_path}")
        return ""

    def _set_app_font(self):
        """设置应用字体 - 使用系统字体栈"""
        font = QFont()
        font.setFamily("-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif")
        font.setPixelSize(13)  # macOS 默认字号
        self.app.setFont(font)

    def _get_fallback_style(self) -> str:
        """获取回退样式"""
        return """
            QWidget {
                background-color: #1E1E1E;
                color: #FFFFFF;
                font-family: -apple-system, sans-serif;
                font-size: 13px;
            }
            QPushButton {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.1);
                padding: 6px 16px;
                border-radius: 6px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #2D2D2D;
                border-color: rgba(255,255,255,0.2);
            }
            QLineEdit {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.1);
                padding: 6px 12px;
                border-radius: 6px;
                min-height: 28px;
            }
        """

    def get_current_theme(self) -> str:
        """获取当前主题"""
        return self.current_theme

    def toggle_theme(self) -> str:
        """切换主题"""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.load_system(new_theme)
        return new_theme

    def refresh(self):
        """刷新当前主题"""
        self.load_system(self.current_theme)


# 全局实例
_theme_manager_instance = None
_theme_lock = Lock()


def get_theme_manager(app: Optional[QApplication] = None) -> macOS_ThemeManager:
    """获取主题管理器单例（线程安全）"""
    global _theme_manager_instance
    if _theme_manager_instance is None:
        with _theme_lock:
            if _theme_manager_instance is None:
                if app is None:
                    app = QApplication.instance()
                _theme_manager_instance = macOS_ThemeManager(app)
    return _theme_manager_instance


def apply_macos_theme(app: QApplication, theme: str = "dark") -> bool:
    """快速应用 macOS 主题的便捷函数"""
    manager = get_theme_manager(app)
    return manager.load_system(theme)


__all__ = ["macOS_ThemeManager", "get_theme_manager", "apply_macos_theme"]
