"""
主题优化器 - 拆分为模块化包

模块:
- _presets: ThemePresets (主题配色方案预设)
- _selector: ThemePresetSelector (主题选择器 UI)
- _preview: ThemeColorPreview (颜色预览 UI)
- _styles: generate_theme_stylesheet (样式表生成器)
"""

from scenefab.ui.theme.theme_optimizer._presets import ThemePresets
from scenefab.ui.theme.theme_optimizer._preview import ThemeColorPreview
from scenefab.ui.theme.theme_optimizer._selector import ThemePresetSelector
from scenefab.ui.theme.theme_optimizer._styles import generate_theme_stylesheet

__all__ = [
    "ThemePresets",
    "ThemePresetSelector",
    "ThemeColorPreview",
    "generate_theme_stylesheet",
]
