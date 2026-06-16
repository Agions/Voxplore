"""
主题管理器 - 管理应用程序主题
"""

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from .tokens import COLORS, DARK_TOKENS, LIGHT_TOKENS


def _theme_token(key: str, mode: str = "light") -> str:
    """Resolve a theme token by key and mode."""
    tokens = LIGHT_TOKENS if mode == "light" else DARK_TOKENS
    return tokens.get(key, COLORS.get(key, "#64748b"))


@dataclass
class ThemeConfig:
    """主题配置（简化版）"""

    name: str = "production"
    mode: str = "light"


@dataclass
class ThemeColors:
    """主题颜色"""

    # Primary
    primary: str = ""
    secondary: str = ""
    # Surface
    background: str = ""
    surface: str = ""
    card: str = ""
    # Text
    text: str = ""
    text_secondary: str = ""
    # Border / Divider
    border: str = ""
    divider: str = ""
    # Functional
    error: str = ""
    warning: str = ""
    success: str = ""
    info: str = ""
    # Accent
    accent: str = ""
    tertiary: str = ""
    light: str = ""
    dark: str = ""

    @classmethod
    def from_mode(cls, mode: str = "light") -> "ThemeColors":
        """Build a ThemeColors instance from resource-aligned tokens."""
        return cls(
            primary=_theme_token("primary", mode),
            secondary=_theme_token("primary-hover", mode),
            background=_theme_token("bg-base", mode),
            surface=_theme_token("bg-surface", mode),
            card=_theme_token("bg-surface", mode),
            text=_theme_token("text-primary", mode),
            text_secondary=_theme_token("text-secondary", mode),
            border=_theme_token("border-default", mode),
            divider=_theme_token("border-subtle", mode),
            error=_theme_token("error", mode),
            warning=_theme_token("warning", mode),
            success=_theme_token("success", mode),
            info=_theme_token("info", mode),
            accent=_theme_token("accent", mode),
            tertiary=_theme_token("accent-subtle", mode),
            light=_theme_token("primary-subtle", mode),
            dark=_theme_token("primary-pressed", mode),
        )


class ThemePreset:
    """主题预设"""

    def __init__(self, name: str, mode: str, colors: ThemeColors):
        self.name = name
        self.mode = mode
        self.colors = colors
        self.stylesheet_path = f"{mode}_theme.qss"


class ThemeManager(QObject):
    """主题管理器"""

    # 信号定义
    theme_changed = Signal(str)  # 主题模式变更信号
    theme_applied = Signal()  # 主题应用完成信号

    def __init__(self, theme_config: ThemeConfig | None = None):
        super().__init__()

        if theme_config is None:
            theme_config = ThemeConfig()
        self.theme_config = theme_config
        self.current_mode = theme_config.mode
        self.colors = ThemeColors.from_mode(theme_config.mode)
        self.theme_presets: list[ThemePreset] = []

        # 初始化主题预设
        self._initialize_theme_presets()

        # 更新颜色配置
        self._update_colors()

    def _initialize_theme_presets(self) -> None:
        """初始化主题预设"""
        dark_colors = ThemeColors.from_mode("dark")
        light_colors = ThemeColors.from_mode("light")

        self.theme_presets = [
            ThemePreset("浅色主题", "light", light_colors),
            ThemePreset("深色主题", "dark", dark_colors),
        ]

    def get_available_themes(self) -> list[str]:
        """获取可用主题列表"""
        return [preset.name for preset in self.theme_presets]

    def get_theme_preset(self, theme_name: str) -> ThemePreset | None:
        """获取指定主题预设"""
        for preset in self.theme_presets:
            if preset.name == theme_name:
                return preset
        return None

    def apply_theme_by_name(self, theme_name: str) -> None:
        """通过主题名称应用主题"""
        preset = self.get_theme_preset(theme_name)
        if preset:
            self.set_theme_mode(preset.mode)
            # 应用主题颜色
            self.colors = preset.colors
            self._apply_to_application()
            self.theme_changed.emit(theme_name)
            self.theme_applied.emit()

    def _update_colors(self) -> None:
        """更新颜色配置"""
        self.colors = ThemeColors.from_mode(self.current_mode)

    def set_theme_mode(self, mode: str) -> None:
        """设置主题模式"""
        if mode != self.current_mode:
            self.current_mode = mode
            self._update_colors()
            self.theme_changed.emit(mode)
            # 应用主题到整个应用
            self._apply_to_application()
            self.theme_applied.emit()

    def get_theme_mode(self) -> str:
        """获取主题模式"""
        return self.current_mode

    def apply_theme(self, widget) -> None:
        """应用主题到窗口部件"""
        stylesheet = self.get_stylesheet()
        widget.setStyleSheet(stylesheet)

    def get_stylesheet(self) -> str:
        """获取样式表"""
        import os

        stylesheet_path = ""

        if self.current_mode == "light":
            # 使用外部浅色主题样式表
            stylesheet_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
                "..",
                "resources",
                "styles",
                "light_theme.qss",
            )
        else:
            # 使用外部深色主题样式表
            stylesheet_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "..",
                "..",
                "resources",
                "styles",
                "dark_theme.qss",
            )

        try:
            with open(stylesheet_path, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            # 如果外部样式表不存在，使用默认样式
            return self._get_default_stylesheet()

    def _get_default_stylesheet(self) -> str:
        """获取默认样式表"""
        return """/* 默认样式 */
        QMainWindow {
            background-color: #f6f8fb;
            color: #182235;
        }
        QPushButton {
            background-color: #ffffff;
            color: #182235;
            border: 1px solid #cbd5e1;
            border-radius: 7px;
            padding: 8px 16px;
        }
        QPushButton:hover {
            background-color: #f1f5f9;
            border-color: #0891b2;
        }
        QLineEdit, QTextEdit {
            background-color: #ffffff;
            color: #182235;
            border: 1px solid #cbd5e1;
            border-radius: 7px;
            padding: 8px;
        }
        QLabel {
            color: #182235;
        }
        """

    def get_colors(self) -> ThemeColors:
        """获取主题颜色"""
        return self.colors

    def set_color(self, color_type: str, color: str) -> None:
        """设置主题颜色"""
        if hasattr(self.colors, color_type):
            setattr(self.colors, color_type, color)

    def get_color(self, color_type: str) -> str:
        """获取主题颜色"""
        return getattr(self.colors, color_type, "#000000")

    def _apply_to_application(self) -> None:
        """将主题应用到整个应用程序"""
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app:
            # 获取样式表
            stylesheet = self.get_stylesheet()
            # 应用样式到整个应用
            app.setStyleSheet(stylesheet)  # type: ignore[attr-defined]
            # 应用到所有顶级窗口
            for widget in app.allWidgets():  # type: ignore[attr-defined]
                widget.setStyleSheet(stylesheet)

    def apply_theme_instantly(self, theme_name: str) -> None:
        """立即应用主题，用于实时预览"""
        preset = self.get_theme_preset(theme_name)
        if preset:
            # 保存当前主题状态
            original_mode = self.current_mode

            # 保存当前颜色配置
            original_colors = ThemeColors(
                primary=self.colors.primary,
                secondary=self.colors.secondary,
                background=self.colors.background,
                surface=self.colors.surface,
                card=self.colors.card,
                text=self.colors.text,
                text_secondary=self.colors.text_secondary,
                border=self.colors.border,
                divider=self.colors.divider,
                error=self.colors.error,
                warning=self.colors.warning,
                success=self.colors.success,
                info=self.colors.info,
                accent=self.colors.accent,
                tertiary=self.colors.tertiary,
                light=self.colors.light,
                dark=self.colors.dark,
            )

            # 应用新主题
            self.current_mode = preset.mode
            self.colors = preset.colors
            self._apply_to_application()
            self.theme_changed.emit(theme_name)
            self.theme_applied.emit()

            # 3秒后恢复原主题（仅用于预览）
            QTimer.singleShot(
                3000, lambda: self._restore_theme(original_mode, original_colors)
            )

    def _restore_theme(self, original_mode: str, original_colors: ThemeColors) -> None:
        """恢复原始主题"""
        self.current_mode = original_mode
        self.colors = original_colors
        self._apply_to_application()
        self.theme_changed.emit(original_mode)
        self.theme_applied.emit()

    def get_current_theme_info(self) -> dict[str, Any]:
        """获取当前主题信息"""
        return {
            "mode": self.current_mode,
            "colors": self.colors.__dict__,
            "available_themes": self.get_available_themes(),
        }

    # ─── 新设计系统集成 ────────────────────────────────────
    def apply_design_system(self, widget=None) -> None:
        """应用全新设计系统"""
        from .base_styles import get_base_qss

        full_css = get_base_qss()

        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if widget:
            widget.setStyleSheet(full_css)
        elif app:
            app.setStyleSheet(full_css)  # type: ignore[attr-defined]
            for w in app.allWidgets():  # type: ignore[attr-defined]
                w.setStyleSheet(full_css)
