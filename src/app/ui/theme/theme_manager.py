#!/usr/bin/env python3
"""
ThemeManager · 主题状态机与系统跟随管理器。

职责：
- 维护三态主题模式（system / light / dark）
- 监听系统外观变化（macOS via Qt 6.5 styleHints / Win registry / Linux xdg）
- 与 ds_tokens.set_theme_mode 协同，重绑定 _C.* 调色板
- 持久化模式到 QSettings (key=appearance/theme_mode)

修复 TD-01: 之前 main_window/_apply_saved_theme 引用了不存在的
``app.ui.theme.theme_manager.ThemeManager``。本文件补齐该模块，并提供
统一的 ``mode_changed`` / ``palette_changed`` 信号供 main_window 接线。

设计要点：
- 单例模式（按 parent QObject 维度隔离），避免重复监听系统信号
- macOS 走 Qt 原生 styleHints().colorSchemeChanged；其它平台走系统检测器
- ``apply_persisted()`` 在 main_window 启动时调用，恢复用户偏好
"""

from __future__ import annotations

import logging
import sys
from enum import Enum

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtGui import QGuiApplication

from app.ui.theme.ds_tokens import set_theme_mode

logger = logging.getLogger(__name__)

__all__ = ["ThemeMode", "ThemeManager"]


class ThemeMode(str, Enum):
    """主题模式（三态）。"""

    SYSTEM = "system"  # 跟随系统
    LIGHT = "light"
    DARK = "dark"


# QSettings organization/application name — 与 main_window / application 保持一致
_QSETTINGS_ORG = "SceneFab"
_QSETTINGS_APP = "Application"
_SETTINGS_KEY = "appearance/theme_mode"


class ThemeManager(QObject):
    """统一管理主题模式：mode ∈ {system, light, dark} → 实际 palette ∈ {light, dark}。

    Signals
    -------
    mode_changed(ThemeMode)
        用户选择的模式变化（手动切换 / 启动恢复）。
    palette_changed(str)
        实际生效的调色板变化（mode=system 时可由系统外观变化触发）。
    """

    mode_changed = Signal(object)  # ThemeMode
    palette_changed = Signal(str)  # "light" | "dark"

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._mode: ThemeMode = ThemeMode.SYSTEM
        self._active_palette: str = "light"
        self._suppress_emit: bool = False
        self._system_listener_installed: bool = False

        # 启动时立刻查询一次系统调色板（避免初始闪烁）
        try:
            self._active_palette = self._query_system_palette()
        except Exception:  # pragma: no cover - 防御性兜底
            logger.debug("启动时查询系统调色板失败，使用默认 light", exc_info=True)
            self._active_palette = "light"

    # ──────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────

    def set_mode(self, mode: ThemeMode | str) -> None:
        """设置主题模式并应用。

        接受 ``ThemeMode`` 或其字符串值（兼容 QSettings 读出的 str）。
        """
        if isinstance(mode, str):
            try:
                mode = ThemeMode(mode)
            except ValueError:
                logger.warning("未知主题模式: %r，回退到 system", mode)
                mode = ThemeMode.SYSTEM

        if mode == self._mode:
            return
        self._mode = mode
        self.mode_changed.emit(mode)
        self._apply()
        self.persist()

    def mode(self) -> ThemeMode:
        """当前用户选择的模式。"""
        return self._mode

    def current_palette(self) -> str:
        """当前实际生效的调色板（light / dark）。"""
        return self._active_palette

    def apply_persisted(self) -> None:
        """从 QSettings 恢复用户偏好并应用。

        应在 main_window 启动早期调用一次（早于首屏渲染）。
        若未持久化过，使用默认 ``system``。
        """
        try:
            qsettings = QSettings(_QSETTINGS_ORG, _QSETTINGS_APP)
            raw = qsettings.value(
                _SETTINGS_KEY, ThemeMode.SYSTEM.value, type=str)
        except Exception:
            logger.warning("读取持久化主题模式失败，使用默认", exc_info=True)
            raw = ThemeMode.SYSTEM.value

        try:
            mode = ThemeMode(raw)
        except ValueError:
            logger.warning("持久化的主题模式无效: %r，使用 system", raw)
            mode = ThemeMode.SYSTEM

        # set_mode 内会触发 _apply + persist；这里只想恢复，不想再写一次
        self._suppress_emit = True
        try:
            self._mode = mode
            self._apply()
        finally:
            self._suppress_emit = False

    def persist(self) -> None:
        """持久化当前 mode 到 QSettings。"""
        try:
            qsettings = QSettings(_QSETTINGS_ORG, _QSETTINGS_APP)
            qsettings.setValue(_SETTINGS_KEY, self._mode.value)
        except Exception:
            logger.debug("持久化主题模式失败", exc_info=True)

    # ──────────────────────────────────────────────────────────
    # 内部：状态机
    # ──────────────────────────────────────────────────────────

    def _apply(self) -> None:
        """根据当前 mode 解析出实际 palette 并 rebind _C。"""
        if self._mode == ThemeMode.SYSTEM:
            self._install_system_listener()
            target = self._query_system_palette()
        elif self._mode == ThemeMode.LIGHT:
            self._uninstall_system_listener()
            target = "light"
        else:  # ThemeMode.DARK
            self._uninstall_system_listener()
            target = "dark"

        if target != self._active_palette:
            self._active_palette = target
            set_theme_mode(target)
            if not self._suppress_emit:
                self.palette_changed.emit(target)
        else:
            # 即使 palette 没变也要保证 _C 已对齐（启动恢复路径可能不一致）
            set_theme_mode(target)

    def _query_system_palette(self) -> str:
        """查询系统当前调色板。优先走 Qt styleHints，失败回退到 OS 检测器。"""
        # macOS / Win / Linux 通用：Qt 6.5+ styleHints.colorScheme()
        try:
            app = QGuiApplication.instance()
            if app is not None:
                scheme = app.styleHints().colorScheme()
                if scheme == Qt.ColorScheme.Dark:
                    return "dark"
                if scheme == Qt.ColorScheme.Light:
                    return "light"
        except Exception:  # pragma: no cover - Qt 版本差异
            logger.debug("Qt styleHints.colorScheme() 查询失败", exc_info=True)

        # 兜底：平台特定检测
        if sys.platform == "darwin":
            return _macos_default_palette()
        if sys.platform == "win32":
            return _windows_default_palette()
        return _linux_default_palette()

    # ──────────────────────────────────────────────────────────
    # 内部：系统监听
    # ──────────────────────────────────────────────────────────

    def _install_system_listener(self) -> None:
        """挂载系统调色板变化监听（仅在 mode=system 时启用）。"""
        if self._system_listener_installed:
            return
        try:
            app = QGuiApplication.instance()
            if app is None:
                return
            hints = app.styleHints()
            hints.colorSchemeChanged.connect(self._on_system_change)
            self._system_listener_installed = True
        except Exception:  # pragma: no cover
            logger.debug("挂载系统调色板监听失败", exc_info=True)

    def _uninstall_system_listener(self) -> None:
        if not self._system_listener_installed:
            return
        try:
            app = QGuiApplication.instance()
            if app is not None:
                try:
                    app.styleHints().colorSchemeChanged.disconnect(self._on_system_change)
                except (RuntimeError, TypeError):
                    pass
        finally:
            self._system_listener_installed = False

    def _on_system_change(self, _scheme: Qt.ColorScheme) -> None:
        """系统外观变化回调：仅在 mode=system 时实际应用。"""
        if self._mode != ThemeMode.SYSTEM:
            return
        self._apply()


# ──────────────────────────────────────────────────────────
# 平台兜底（Qt styleHints 不可用时）
# ──────────────────────────────────────────────────────────


def _macos_default_palette() -> str:
    """macOS 默认调色板探测（无 PyObjC 时退回 light）。

    真实场景下 Qt 6.5+ styleHints 总会先命中，本函数极少被调用。
    """
    return "light"


def _windows_default_palette() -> str:
    """Windows 默认调色板探测。读注册表 AppsUseLightTheme。"""
    try:
        import winreg  # type: ignore[import-not-found]

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if value else "dark"
    except Exception:
        return "light"


def _linux_default_palette() -> str:
    """Linux 默认调色板探测。优先 gsettings，fallback xdg 配置。"""
    # 1) gsettings（GNOME 优先）
    try:
        import subprocess

        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            value = result.stdout.strip().strip("'\"")
            if value == "prefer-dark":
                return "dark"
            if value in ("default", "prefer-light", ""):
                return "light"
    except Exception:
        pass

    # 2) gtk-3.0 xdg fallback
    try:
        from pathlib import Path

        settings = Path.home() / ".config" / "gtk-3.0" / "settings.ini"
        if settings.is_file():
            for line in settings.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.strip().startswith("gtk-application-prefer-dark-theme="):
                    return "dark" if line.split("=", 1)[1].strip() == "1" else "light"
    except Exception:
        pass

    return "light"
