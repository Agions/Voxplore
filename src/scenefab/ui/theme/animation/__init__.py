#!/usr/bin/env python3

r"""
SceneFab 动效系统

历史：原 monolith 文件 scenefab.ui.theme.animation_helper 已重构为子包：
- _animation_helper.py: AnimationHelper 通用动画
- _page_transition.py: PageTransition 页面切换
- _widgets.py: AnimatedButton / LoadingAnimation

为保持向后兼容，本 __init__.py 重导出所有公共符号，旧代码
``from scenefab.ui.theme.animation_helper import AnimationHelper`` 已迁移为
``from scenefab.ui.theme.animation import AnimationHelper``。

迁移命令（grep + sed）：
    rg "from scenefab\.ui\.theme\.animation_helper import" --type py
"""

from ._animation_helper import AnimationHelper
from ._page_transition import PageTransition
from ._widgets import AnimatedButton, LoadingAnimation

__all__ = [
    "AnimationHelper",
    "PageTransition",
    "AnimatedButton",
    "LoadingAnimation",
]
