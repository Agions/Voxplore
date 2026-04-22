"""
主题管理器 - 管理应用程序主题
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, QTimer

# OKLCH Design Token source — all ThemeColors must reference these.
from app.ui.theme.tokens import COLORS, LIGHT_TOKENS, DARK_TOKENS


def _oklch(key: str, mode: str = "dark") -> str:
    """Resolve an OKLCH token by key, mode-sensitively."""
    tokens = DARK_TOKENS if mode == "dark" else LIGHT_TOKENS
    return tokens.get(key, COLORS.get(key, "oklch(0.50 0.00 0)"))


from dataclasses import dataclass


@dataclass
class ThemeConfig:
    """主题配置（简化版）"""
    name: str = "voxplore"
    mode: str = "dark"


@dataclass
class ThemeColors:
    """主题颜色 — OKLCH Design Tokens (Voxplore)"""
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
    def from_mode(cls, mode: str = "dark") -> "ThemeColors":
        """Build a ThemeColors instance from OKLCH tokens."""
        return cls(
            primary=_oklch("primary", mode),
            secondary=_oklch("primary-hover", mode),
            background=_oklch("bg-base", mode),
            surface=_oklch("bg-surface", mode),
            card=_oklch("bg-surface", mode),
            text=_oklch("text-primary", mode),
            text_secondary=_oklch("text-secondary", mode),
            border=_oklch("border-default", mode),
            divider=_oklch("border-subtle", mode),
            error=_oklch("error", mode),
            warning=_oklch("warning", mode),
            success=_oklch("success", mode),
            info=_oklch("info", mode),
            accent=_oklch("accent", mode),
            tertiary=_oklch("accent-subtle", mode),
            light=_oklch("primary-subtle", mode),
            dark=_oklch("primary-pressed", mode),
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
        self.theme_presets: List[ThemePreset] = []

        # 初始化主题预设
        self._initialize_theme_presets()

        # 更新颜色配置
        self._update_colors()

    def _initialize_theme_presets(self) -> None:
        """初始化主题预设 — 深色/浅色使用 OKLCH tokens，彩色变体保留 hex"""
        # OKLCH 深色/浅色主题
        dark_colors   = ThemeColors.from_mode("dark")
        light_colors  = ThemeColors.from_mode("light")

        # 蓝调深色 — GitHub 风格（保留定制 hex）
        blue_dark_colors = ThemeColors(
            primary="#388BFD", secondary="#1F6FEB", background="#0D1117",
            surface="#161B22", card="#161B22", text="#E6EDF3",
            text_secondary="#C9D1D9", border="#30363D", divider="#21262D",
            error="#DA3633", warning="#D29922", success="#238636",
            info="#388BFD", accent="#A371F7", tertiary="#8B5CF6",
            light="#DBEAFE", dark="#1E40AF"
        )

        # 森林绿色（保留定制 hex）
        forest_colors = ThemeColors(
            primary="#22C55E", secondary="#16A34A", background="#064E3B",
            surface="#14532D", card="#14532D", text="#ECFDF5",
            text_secondary="#99F6E4", border="#16A34A", divider="#15803D",
            error="#EF4444", warning="#F59E0B", success="#22C55E",
            info="#3B82F6", accent="#8B5CF6", tertiary="#EC4899",
            light="#BBF7D0", dark="#052E16"
        )

        # 紫色主题（保留定制 hex）
        purple_colors = ThemeColors(
            primary="#9C27B0", secondary="#7B1FA2", background="#121212",
            surface="#1E1B1E", card="#1E1B1E", text="#FFFFFF",
            text_secondary="#E0E0E0", border="#4A148C", divider="#311B92",
            error="#F44336", warning="#FFB300", success="#66BB6A",
            info="#2196F3", accent="#EC407A", tertiary="#5C6BC0",
            light="#E1BEE7", dark="#4A148C"
        )

        # 橙色主题（保留定制 hex）
        orange_colors = ThemeColors(
            primary="#FF5722", secondary="#E64A19", background="#263238",
            surface="#37474F", card="#37474F", text="#FFFFFF",
            text_secondary="#CFD8DC", border="#546E7A", divider="#455A64",
            error="#F44336", warning="#FFB74D", success="#81C784",
            info="#4FC3F7", accent="#9575CD", tertiary="#FF8A65",
            light="#FFCCBC", dark="#BF360C"
        )

        # 添加主题预设
        self.theme_presets = [
            ThemePreset("深色主题",   "dark",  dark_colors),
            ThemePreset("浅色主题",   "light", light_colors),
            ThemePreset("蓝调深色",   "dark",  blue_dark_colors),
            ThemePreset("森林绿色",   "dark",  forest_colors),
            ThemePreset("紫色主题",   "dark",  purple_colors),
            ThemePreset("橙色主题",   "dark",  orange_colors),
            # Voxplore 架构升级 - 新增主题
            ThemePreset("Voxplore 声视界", "voxplore", dark_colors),
        ]

    def get_available_themes(self) -> List[str]:
        """获取可用主题列表"""
        return [preset.name for preset in self.theme_presets]
        
    def get_theme_preset(self, theme_name: str) -> Optional[ThemePreset]:
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
        """更新颜色配置 — 从 OKLCH tokens 驱动"""
        self.colors = ThemeColors.from_mode(self.current_mode)
        # Allow theme_config overrides if explicitly set (non-empty)
        if self.theme_config.primary_color:
            self.colors.primary = self.theme_config.primary_color
        if self.theme_config.secondary_color:
            self.colors.secondary = self.theme_config.secondary_color
        if self.theme_config.background_color:
            self.colors.background = self.theme_config.background_color
        if self.theme_config.surface_color:
            self.colors.surface = self.theme_config.surface_color
        if self.theme_config.text_color:
            self.colors.text = self.theme_config.text_color

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

        if self.current_mode == "voxplore":
            # Voxplore 专用主题
            stylesheet_path = os.path.join(os.path.dirname(__file__), "voxplore.qss")
        elif self.current_mode == "dark":
            # 使用外部深色主题样式表
            stylesheet_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "resources", "styles", "dark_theme.qss")
        else:
            # 使用外部浅色主题样式表（如果存在）
            stylesheet_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "resources", "styles", "light_theme.qss")
        
        try:
            with open(stylesheet_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            # 如果外部样式表不存在，使用默认样式
            return self._get_default_stylesheet()

    def _get_default_stylesheet(self) -> str:
        """获取默认样式表"""
        return """/* 默认样式 */
        QMainWindow {
            background-color: #1E1E1E;
            color: white;
        }
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
        }
        QPushButton:hover {
            background-color: #1976D2;
        }
        QLineEdit, QTextEdit {
            background-color: #2D2D2D;
            color: white;
            border: 1px solid #404040;
            border-radius: 4px;
            padding: 8px;
        }
        QLabel {
            color: white;
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
            app.setStyleSheet(stylesheet)
            # 应用到所有顶级窗口
            for widget in app.allWidgets():
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
                dark=self.colors.dark
            )
            
            # 应用新主题
            self.current_mode = preset.mode
            self.colors = preset.colors
            self._apply_to_application()
            self.theme_changed.emit(theme_name)
            self.theme_applied.emit()
            
            # 3秒后恢复原主题（仅用于预览）
            QTimer.singleShot(3000, lambda: self._restore_theme(original_mode, original_colors))
            
    def _restore_theme(self, original_mode: str, original_colors: ThemeColors) -> None:
        """恢复原始主题"""
        self.current_mode = original_mode
        self.colors = original_colors
        self._apply_to_application()
        self.theme_changed.emit(original_mode)
        self.theme_applied.emit()
        
    def get_current_theme_info(self) -> Dict[str, Any]:
        """获取当前主题信息"""
        return {
            "mode": self.current_mode,
            "colors": self.colors.__dict__,
            "available_themes": self.get_available_themes()
        }

    # ─── 新设计系统集成 ────────────────────────────────────
    def apply_design_system(self, widget=None) -> None:
        """应用全新设计系统（简约科技风 + OKLCH tokens）"""
        from .qss_variables import register_qss_variables
        from .base_styles import get_base_qss

        vars_css = register_qss_variables()
        base_css = get_base_qss()
        full_css = f"""{vars_css}\n{base_css}"""

        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if widget:
            widget.setStyleSheet(full_css)
        elif app:
            app.setStyleSheet(full_css)
            for w in app.allWidgets():
                w.setStyleSheet(full_css)