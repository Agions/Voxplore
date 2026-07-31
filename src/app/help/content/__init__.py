"""内置帮助条目池。

每条 entry 由 ``builtin_topics(language)`` 根据当前语言返回。条目主要分三类：

* ``category="shortcut"`` — 键盘快捷键速查，固定 5-8 条。
* ``category="faq"`` — 启动 / 配置 / 性能 / 导出等高频问题。
* ``category="onboarding"`` — 首次启动时展示的 5 步引导。

新的语言只需在子目录新增 ``xx_XX.py`` 并在 :func:`builtin_topics` 注册即可。
"""

from __future__ import annotations

from ..models import HelpTopic

__all__ = ["builtin_topics"]


def builtin_topics(language: str = "zh_CN") -> list[HelpTopic]:
    """根据当前语言返回内置 ``HelpTopic`` 列表。

    Args:
        language: 语言代码，目前支持 ``"zh_CN"`` 与 ``"en_US"``。

    Returns:
        该语言对应的 ``HelpTopic`` 列表；未知语言降级为中文。
    """
    if language == "en_US":
        from . import en_US as mod
    else:
        # zh_CN 作为默认语言；任何未识别的 code 全部降级为中文。
        from . import zh_CN as mod
    return mod.TOPICS
