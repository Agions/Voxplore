"""HelpRegistry · 帮助条目注册中心与搜索引擎。

设计要点
========

1. **来源透明**：每条 topic 在 ``source`` 字段标注来源（``"docs/guide/..."`` 或
   ``"built-in:faq"``），便于 UI 显示与排错。
2. **去重与覆盖**：重复 ``id`` 视为覆盖（与 CommandRegistry 保持一致），保证
   ``register`` 可重入。
3. **分类树** ``by_category``：``list_categories()`` 返回排序后的分类列表，
   面板左侧目录树直接消费。
4. **全文搜索**：轻量加权匹配——命中 title 加 3 分、tags 加 2 分、body 加 1 分；
   多关键字 AND 语义：每条 term 至少一处命中才算匹配。
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .models import HelpSearchResult, HelpTopic

__all__ = ["HelpRegistry"]


# 命中权重
_SCORE_TITLE = 3.0
_SCORE_TAG = 2.0
_SCORE_BODY = 1.0

# 多关键字之间 AND：每条 term 必须命中至少一处字段。
# 搜索结果按得分降序；得分相同则按 topic.title 升序。

_TERM_SPLIT_RE = re.compile(r"[\s,，]+")


def _split_terms(query: str) -> list[str]:
    """把查询字符串切分为小写 term 列表。"""
    query = (query or "").strip().lower()
    if not query:
        return []
    return [t for t in _TERM_SPLIT_RE.split(query) if t]


def _hit_score(topic: HelpTopic, term: str) -> tuple[float, tuple[str, ...]]:
    """计算单 term 在 topic 上的命中分与命中字段元组。

    Returns:
        (score, fields) — score=0 表示未命中；fields 是命中的字段名列表。
    """
    fields: list[str] = []
    score = 0.0
    title_lc = topic.title.lower()
    if term in title_lc:
        score += _SCORE_TITLE
        fields.append("title")

    tags_lc = tuple(t.lower() for t in topic.tags)
    if any(term in t for t in tags_lc):
        score += _SCORE_TAG
        fields.append("tags")

    # body + summary + 章节正文合并后做一次 contains
    blob_parts = [topic.body.lower(), topic.summary.lower()]
    blob_parts.extend(s.body.lower() for s in topic.sections)
    blob = "\n".join(blob_parts)
    if term in blob:
        score += _SCORE_BODY
        fields.append("body")
    return score, tuple(fields)


class HelpRegistry:
    """帮助条目注册中心。"""

    def __init__(self) -> None:
        self._topics: dict[str, HelpTopic] = {}
        self._order: list[str] = []

    # ── CRUD ──

    def register(self, topic: HelpTopic) -> None:
        """注册一条 topic。重复 id 视为覆盖。"""
        if not topic.id:
            raise ValueError("HelpTopic.id is required")
        if not topic.title:
            raise ValueError("HelpTopic.title is required")
        if topic.id not in self._topics:
            self._order.append(topic.id)
        self._topics[topic.id] = topic

    def register_many(self, topics: Iterable[HelpTopic]) -> None:
        """批量注册；任意一条出错立刻抛出。"""
        for topic in topics:
            self.register(topic)

    def unregister(self, topic_id: str) -> None:
        if topic_id in self._topics:
            self._topics.pop(topic_id, None)
            try:
                self._order.remove(topic_id)
            except ValueError:
                pass

    def clear(self) -> None:
        self._topics.clear()
        self._order.clear()

    def get(self, topic_id: str) -> HelpTopic | None:
        return self._topics.get(topic_id)

    def __contains__(self, topic_id: object) -> bool:
        return isinstance(topic_id, str) and topic_id in self._topics

    def __len__(self) -> int:
        return len(self._topics)

    # ── 列表 / 分类 ──

    def list(self) -> list[HelpTopic]:
        """按注册顺序返回所有 topic。"""
        return [self._topics[i] for i in self._order if i in self._topics]

    def list_categories(self) -> list[str]:
        """返回排序后的分类列表（去重）。"""
        return sorted({t.category for t in self.list() if t.category})

    def by_category(self, category: str) -> list[HelpTopic]:
        """返回指定分类下的 topic 列表（按注册顺序）。"""
        return [t for t in self.list() if t.category == category]

    # ── 搜索 ──

    def search(self, query: str, *, limit: int = 20) -> list[HelpSearchResult]:
        """AND 全文搜索。

        Args:
            query: 搜索词；多个 term 以空白 / 逗号分隔。
            limit: 最多返回多少条结果。

        Returns:
            按得分降序排列的 ``HelpSearchResult`` 列表。
        """
        terms = _split_terms(query)
        if not terms:
            return []

        results: list[HelpSearchResult] = []
        for topic in self.list():
            total_score = 0.0
            all_fields: list[str] = []
            for term in terms:
                score, fields = _hit_score(topic, term)
                if score <= 0:
                    # AND：任一 term 未命中，整条丢弃。
                    total_score = 0.0
                    all_fields = []
                    break
                total_score += score
                all_fields.extend(fields)
            if total_score > 0:
                # 去重 fields 但保留出现顺序。
                seen: set[str] = set()
                uniq = tuple(f for f in all_fields if not (
                    f in seen or seen.add(f)))
                results.append(
                    HelpSearchResult(
                        topic=topic, score=total_score, matched_fields=uniq)
                )

        results.sort(key=lambda r: (-r.score, r.topic.title))
        return results[:limit]

    def list_shortcuts(self) -> list[HelpTopic]:
        """专门列出 category=='shortcut' 的条目。"""
        return self.by_category("shortcut")
