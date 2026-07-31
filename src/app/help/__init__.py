"""SceneFab 内嵌帮助系统。

子模块速览
==========

* :mod:`app.help.models` — 不可变 dataclass：``HelpTopic`` / ``HelpSection`` /
  ``HelpSearchResult``。
* :mod:`app.help.markdown_parser` — 把 ``docs/guide/*.md`` 解析为 ``HelpTopic`` 列表。
* :mod:`app.help.registry` — 注册中心 + AND 全文搜索。
* :mod:`app.help.content` — 内置条目池（FAQ / 快捷键 / onboarding），多语言。

典型用法
========

>>> registry = build_default_registry()
>>> registry.search("api key")
[HelpSearchResult(topic=HelpTopic(id='faq.api-key', ...), score=4.0, ...)]
"""

from __future__ import annotations

from pathlib import Path

from .models import HelpSearchResult, HelpSection, HelpTopic
from .registry import HelpRegistry

__all__ = [
    "HelpSection",
    "HelpTopic",
    "HelpSearchResult",
    "HelpRegistry",
    "build_default_registry",
]


_DEFAULT_LANGUAGE = "zh_CN"


def build_default_registry(
    guide_dir: Path | None = None,
    *,
    language: str = _DEFAULT_LANGUAGE,
) -> HelpRegistry:
    """构造包含内置条目 + docs/guide 解析结果的默认 registry。

    Args:
        guide_dir: ``docs/guide`` 目录路径；为 ``None`` 时尝试项目内置路径。
        language: 语言代码（``"zh_CN"`` 或 ``"en_US"``）。

    Returns:
        填充完毕的 ``HelpRegistry`` 实例。
    """
    from .content import builtin_topics
    from .markdown_parser import parse_guide_directory

    registry = HelpRegistry()
    registry.register_many(builtin_topics(language=language))

    if guide_dir is None:
        # 默认从项目根目录向下查找。
        candidate = Path(__file__).resolve().parents[3] / "docs" / "guide"
        if candidate.exists():
            guide_dir = candidate
    if guide_dir is not None:
        registry.register_many(parse_guide_directory(guide_dir))
    return registry
