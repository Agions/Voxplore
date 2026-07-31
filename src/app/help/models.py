"""帮助系统数据模型。

设计原则
========

1. **不可变快照**：每个 ``HelpTopic`` 一旦注册就不可修改，方便跨线程共享。
2. **平台无关**：纯 dataclass，不依赖 PySide6，便于在 headless 单元测试中使用。
3. **可序列化**：字段全部是 JSON 友好的基础类型，便于将来导出 / 缓存。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HelpSection:
    """一段独立的章节内容。

    ``heading`` 可以是 H3 子标题或列表项名；``body`` 为 markdown 原文。
    """

    heading: str
    body: str
    level: int = 3  # markdown heading level: 2/3/4


@dataclass(frozen=True)
class HelpTopic:
    """一条完整的帮助条目。

    Attributes:
        id: 唯一 id（如 ``"guide.quick-start.step-install"``）。
        title: 标题，列表与搜索时展示。
        category: 分类（如 ``"guide"``、``"faq"``、``"shortcut"``），用于目录分组。
        summary: 简短的一句话描述，列表视图第二行。
        source: 来源标记（如 ``"docs/guide/quick-start.md"``），用于溯源。
        tags: 关键字列表，用于搜索时的关键词命中。
        sections: 子章节列表（H3 子标题或代码块），用于面板渲染。
        body: 主内容 markdown（不包含子章节部分）。
    """

    id: str
    title: str
    category: str = "guide"
    summary: str = ""
    source: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    sections: tuple[HelpSection, ...] = field(default_factory=tuple)
    body: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转字典，便于 JSON 导出与调试。"""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "summary": self.summary,
            "source": self.source,
            "tags": list(self.tags),
            "sections": [
                {"heading": s.heading, "body": s.body, "level": s.level}
                for s in self.sections
            ],
            "body": self.body,
        }


@dataclass(frozen=True)
class HelpSearchResult:
    """一条搜索结果，含原始 topic 与匹配分。"""

    topic: HelpTopic
    score: float
    matched_fields: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """转字典，便于调试输出。"""
        return {
            "topic": self.topic.to_dict(),
            "score": self.score,
            "matched_fields": list(self.matched_fields),
        }


__all__ = ["HelpSection", "HelpTopic", "HelpSearchResult"]
