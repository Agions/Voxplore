#!/usr/bin/env python3
"""
SceneFab 系统托盘管理器
========================
实现系统托盘图标、菜单和关闭行为控制。

核心设计：
- 默认行为：点击关闭按钮直接退出（不缩放到托盘）
- 仅当用户在设置中开启"关闭时最小化到托盘"时，才激活托盘缩放
- 提供托盘菜单：显示窗口、设置、退出
- 单次实例：避免重复创建托盘图标
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from app.ui.i18n import t

logger = logging.getLogger(__name__)

__all__ = ["TrayManager", "get_tray_manager"]


class TrayManager(QObject):
    """
    系统托盘管理器

    职责：
    1. 管理 QSystemTrayIcon 生命周期
    2. 提供托盘菜单（显示/设置/退出）
    3. 单例模式：全局只允许一个托盘实例
    """

    # 信号：用户从托盘请求"显示主窗口"
    show_window_requested = Signal()
    # 信号：用户从托盘请求"退出应用"
    quit_requested = Signal()
    # 信号：用户从托盘请求"打开设置"
    open_settings_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._parent = parent
        self._tray_icon: QSystemTrayIcon | None = None
        self._menu: QMenu | None = None
        self._enabled = False  # 是否启用托盘功能
        # Translatable menu actions — populated by ``_build_menu``.
        self._title_action: QAction | None = None
        self._show_action: QAction | None = None
        self._settings_action: QAction | None = None
        self._quit_action: QAction | None = None

    @property
    def is_available(self) -> bool:
        """系统是否支持托盘图标"""
        return QSystemTrayIcon.isSystemTrayAvailable()

    @property
    def is_enabled(self) -> bool:
        """托盘功能是否已启用（用户在设置中开启）"""
        return self._enabled

    def enable(self, window_title: str = "SceneFab") -> bool:
        """
        启用系统托盘

        Args:
            window_title: 托盘提示中显示的窗口标题

        Returns:
            True 如果成功创建托盘，False 如果系统不支持
        """
        if self._tray_icon is not None:
            logger.debug("Tray already initialized")
            return True

        if not self.is_available:
            logger.warning("System tray not available on this platform")
            return False

        try:
            # 创建托盘图标
            self._tray_icon = QSystemTrayIcon(self._parent)
            tray_icon = self._tray_icon  # local alias for type narrowing
            assert tray_icon is not None  # for type checker
            tray_icon.setToolTip(window_title)

            # 加载图标
            icon = self._load_app_icon()
            if icon is not None and not icon.isNull():
                tray_icon.setIcon(icon)
            else:
                # 降级：使用应用默认图标
                app = QApplication.instance()
                if app and not app.windowIcon().isNull():
                    tray_icon.setIcon(app.windowIcon())

            # 构建菜单
            self._build_menu(window_title)

            # 绑定双击事件：显示窗口
            tray_icon.activated.connect(self._on_tray_activated)

            # 显示托盘
            tray_icon.show()
            self._enabled = True
            logger.info(f"System tray enabled: {window_title}")
            return True

        except Exception as e:
            logger.error(f"Failed to enable system tray: {e}")
            self._tray_icon = None
            return False

    def disable(self) -> None:
        """禁用并清理托盘"""
        if self._tray_icon is not None:
            try:
                self._tray_icon.hide()
            except Exception as e:
                logger.debug(f"Failed to hide system tray icon: {e}")
            self._tray_icon = None
        if self._menu is not None:
            self._menu.deleteLater()
            self._menu = None
        self._title_action = None
        self._show_action = None
        self._settings_action = None
        self._quit_action = None
        self._enabled = False
        logger.info("System tray disabled")

    def show_notification(
        self,
        title: str,
        message: str,
        icon_type: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        timeout_ms: int = 3000,
    ) -> None:
        """
        显示托盘通知

        Args:
            title: 通知标题
            message: 通知内容
            icon_type: 图标类型
            timeout_ms: 显示时长（毫秒）
        """
        if self._tray_icon is None or not self._enabled:
            return
        try:
            self._tray_icon.showMessage(title, message, icon_type, timeout_ms)
        except Exception as e:
            logger.debug(f"Failed to show tray notification: {e}")

    def _load_app_icon(self) -> QIcon | None:
        """尝试加载应用图标"""
        icon_paths = [
            Path(__file__).parent.parent.parent /
            "resources" / "icons" / "logo.png",
            Path(__file__).parent.parent.parent /
            "resources" / "icons" / "logo.svg",
            Path(__file__).parent.parent.parent / "assets" / "logo.png",
        ]
        for p in icon_paths:
            if p.exists():
                try:
                    return QIcon(str(p))
                except Exception:
                    continue
        return None

    def _build_menu(self, window_title: str) -> None:
        """构建右键菜单"""
        if self._tray_icon is None:
            return

        self._menu = QMenu()
        assert self._menu is not None  # for type checker
        menu = self._menu

        # 标题（不可点击）
        self._title_action = QAction(
            t("tray.menu.header").format(name=window_title), menu
        )
        self._title_action.setEnabled(False)
        menu.addAction(self._title_action)
        menu.addSeparator()

        # 显示窗口
        self._show_action = QAction(t("tray.menu.show_window"), menu)
        self._show_action.triggered.connect(self.show_window_requested.emit)
        menu.addAction(self._show_action)

        # 设置
        self._settings_action = QAction(t("tray.menu.settings"), menu)
        self._settings_action.triggered.connect(
            self.open_settings_requested.emit)
        menu.addAction(self._settings_action)

        menu.addSeparator()

        # 退出
        self._quit_action = QAction(
            t("tray.menu.quit").format(name=window_title), menu
        )
        self._quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(self._quit_action)

        self._tray_icon.setContextMenu(menu)

    def retranslate(self, window_title: str) -> None:
        """Refresh translatable menu text after the active language changes."""
        if self._menu is None:
            return
        if self._title_action is not None:
            self._title_action.setText(
                t("tray.menu.header").format(name=window_title)
            )
        if self._show_action is not None:
            self._show_action.setText(t("tray.menu.show_window"))
        if self._settings_action is not None:
            self._settings_action.setText(t("tray.menu.settings"))
        if self._quit_action is not None:
            self._quit_action.setText(
                t("tray.menu.quit").format(name=window_title)
            )
        # Tooltip on the tray icon may also carry the window title.
        if self._tray_icon is not None:
            self._tray_icon.setToolTip(window_title)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """处理托盘图标激活事件"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # 单击：Windows 上通常触发
            self.show_window_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # 双击：所有平台通用
            self.show_window_requested.emit()


# ═══════════════════════════════════════════════════════════════════════
# 单例访问器
# ═══════════════════════════════════════════════════════════════════════

_tray_manager_instance: TrayManager | None = None


def get_tray_manager() -> TrayManager:
    """获取全局托盘管理器实例"""
    global _tray_manager_instance
    if _tray_manager_instance is None:
        _tray_manager_instance = TrayManager()
    return _tray_manager_instance


def reset_tray_manager() -> None:
    """重置托盘管理器（主要用于测试）"""
    global _tray_manager_instance
    if _tray_manager_instance is not None:
        _tray_manager_instance.disable()
    _tray_manager_instance = None
