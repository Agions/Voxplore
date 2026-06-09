#!/usr/bin/env python3

"""
SceneFab Design System — OKLCH 感知均匀色彩系统

.. deprecated::
    兼容层：保留 ``scenefab.ui.components.design_system`` 作为 package 入口，
    重导出所有公共符号。历史代码 ``from .design_system import Colors`` 仍可工作，
    新代码推荐从子模块直接导入：

        from scenefab.ui.components.design_system._tokens import Colors, Radius
        from scenefab.ui.components.design_system._style_generator import StyleSheet
        from scenefab.ui.components.design_system._components import CFButton, ...
"""

# 设计 Tokens
# 组件封装
from ._components import (
    CFButton,
    CFCard,
    CFInput,
    CFLabel,
    CFNavButton,
    CFPanel,
    CFProgressBar,
    CFToastNotification,
)

# 样式生成器
from ._style_generator import StyleSheet
from ._tokens import (
    _C,
    Colors,
    Fonts,
    Motion,
    Radius,
    Shadows,
)

__all__ = [
    # Tokens
    "_C",
    "Colors",
    "Radius",
    "Fonts",
    "Motion",
    "Shadows",
    # Style
    "StyleSheet",
    # Components
    "CFButton",
    "CFLabel",
    "CFCard",
    "CFPanel",
    "CFInput",
    "CFProgressBar",
    "CFNavButton",
    "CFToastNotification",
]
