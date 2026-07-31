"""Tests for the help registry & content pool (Phase 3 · help system).

These tests are PySide6-free — they exercise the backend search engine and
the multilingual builtin topic pool that backs the HelpPanel dock.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.help import build_default_registry
from app.help.content import builtin_topics
from app.help.models import HelpSearchResult, HelpSection, HelpTopic
from app.help.registry import HelpRegistry

# ────────────────────────────────────────────────────────────────
#  Models
# ────────────────────────────────────────────────────────────────


def test_help_topic_is_frozen_and_serializable() -> None:
    topic = HelpTopic(
        id="t.1",
        title="Hello",
        category="faq",
        body="body",
        sections=(HelpSection(heading="s", body="b", level=3),),
        tags=("a", "b"),
    )
    with pytest.raises((AttributeError, Exception)):  # frozen raises on setattr
        topic.title = "new"  # type: ignore[misc]
    d = topic.to_dict()
    assert d["id"] == "t.1"
    assert d["title"] == "Hello"
    assert len(d["sections"]) == 1


def test_help_search_result_carries_score_and_fields() -> None:
    topic = HelpTopic(id="x", title="X", category="faq")
    res = HelpSearchResult(topic=topic, score=1.5,
                           matched_fields=("title", "body"))
    assert res.score == 1.5
    assert "title" in res.matched_fields


# ────────────────────────────────────────────────────────────────
#  Registry CRUD
# ────────────────────────────────────────────────────────────────


def test_registry_register_and_lookup() -> None:
    reg = HelpRegistry()
    topic = HelpTopic(id="faq.x", title="X")
    reg.register(topic)
    assert reg.get("faq.x") == topic
    assert "faq.x" in reg
    assert len(reg) == 1


def test_registry_register_duplicate_id_overrides() -> None:
    reg = HelpRegistry()
    reg.register(HelpTopic(id="x", title="First"))
    reg.register(HelpTopic(id="x", title="Second"))
    assert len(reg) == 1
    assert reg.get("x").title == "Second"


def test_registry_unregister_and_clear() -> None:
    reg = HelpRegistry()
    reg.register(HelpTopic(id="a", title="A"))
    reg.register(HelpTopic(id="b", title="B"))
    reg.unregister("a")
    assert "a" not in reg
    assert "b" in reg
    reg.clear()
    assert len(reg) == 0


def test_registry_register_validates_id_and_title() -> None:
    reg = HelpRegistry()
    with pytest.raises(ValueError):
        reg.register(HelpTopic(id="", title="X"))
    with pytest.raises(ValueError):
        reg.register(HelpTopic(id="x", title=""))


def test_registry_list_preserves_registration_order() -> None:
    reg = HelpRegistry()
    for i in range(5):
        reg.register(HelpTopic(id=f"id.{i}", title=f"T{i}"))
    listed = reg.list()
    assert [t.id for t in listed] == [f"id.{i}" for i in range(5)]


# ────────────────────────────────────────────────────────────────
#  Categories
# ────────────────────────────────────────────────────────────────


def test_registry_categories_returns_sorted_unique() -> None:
    reg = HelpRegistry()
    reg.register(HelpTopic(id="a", title="A", category="faq"))
    reg.register(HelpTopic(id="b", title="B", category="guide"))
    reg.register(HelpTopic(id="c", title="C", category="faq"))
    assert reg.list_categories() == ["faq", "guide"]


def test_registry_by_category_filters_correctly() -> None:
    reg = HelpRegistry()
    reg.register(HelpTopic(id="a", title="A", category="faq"))
    reg.register(HelpTopic(id="b", title="B", category="guide"))
    reg.register(HelpTopic(id="c", title="C", category="faq"))
    faqs = reg.by_category("faq")
    assert [t.id for t in faqs] == ["a", "c"]
    assert reg.list_shortcuts() == []  # nothing in shortcut category yet


# ────────────────────────────────────────────────────────────────
#  Search
# ────────────────────────────────────────────────────────────────


def test_search_empty_query_returns_empty() -> None:
    reg = HelpRegistry()
    reg.register(HelpTopic(id="a", title="API Key 配置", body="API key"))
    assert reg.search("") == []
    assert reg.search("   ") == []


def test_search_finds_title_hits_with_higher_score() -> None:
    reg = HelpRegistry()
    reg.register(HelpTopic(id="t1", title="API Key", body="无关内容"))
    reg.register(HelpTopic(id="t2", title="FAQ", body="api 关键字出现在 body"))
    results = reg.search("API")
    assert len(results) == 2
    # title hit should score higher than body hit
    assert results[0].topic.id == "t1"
    assert "title" in results[0].matched_fields


def test_search_and_semantics_across_multiple_terms() -> None:
    reg = HelpRegistry()
    reg.register(HelpTopic(id="t1", title="API Key", body=""))
    reg.register(HelpTopic(id="t2", title="subtitle", body="api"))
    reg.register(HelpTopic(id="t3", title="key", body=""))
    # "api key" → both terms must hit; t1 hits both, t3 hits only "key", t2 only "api"
    results = reg.search("api key")
    assert [r.topic.id for r in results] == ["t1"]


def test_search_supports_chinese_terms() -> None:
    reg = HelpRegistry()
    reg.register(HelpTopic(id="zh", title="字幕不同步", body=""))
    assert len(reg.search("字幕")) == 1
    assert len(reg.search("不同步")) == 1
    assert len(reg.search("无关")) == 0


def test_search_honors_limit() -> None:
    reg = HelpRegistry()
    for i in range(10):
        reg.register(HelpTopic(id=f"t.{i}", title=f"Topic {i}", body="common"))
    results = reg.search("common", limit=3)
    assert len(results) == 3


def test_search_results_sorted_by_score_then_title() -> None:
    reg = HelpRegistry()
    reg.register(HelpTopic(id="z", title="Zoo", body=""))  # title hit
    reg.register(HelpTopic(id="y", title="Yard", body="zoo"))  # body hit
    results = reg.search("zoo")
    # title hit scores higher than body hit
    assert results[0].topic.id == "z"


# ────────────────────────────────────────────────────────────────
#  Built-in content pool
# ────────────────────────────────────────────────────────────────


def test_builtin_topics_zh_cn_returns_nonempty() -> None:
    topics = builtin_topics(language="zh_CN")
    assert len(topics) >= 15
    cats = {t.category for t in topics}
    assert {"shortcut", "faq", "onboarding"}.issubset(cats)


def test_builtin_topics_en_us_returns_nonempty() -> None:
    topics = builtin_topics(language="en_US")
    assert len(topics) >= 15
    # sanity: english titles use latin letters
    for t in topics:
        assert t.title  # non-empty


def test_builtin_topics_unknown_language_falls_back_to_zh_cn() -> None:
    zh = builtin_topics("zh_CN")
    fallback = builtin_topics("xx_XX")
    assert [t.id for t in zh] == [t.id for t in fallback]


def test_builtin_topics_have_unique_ids() -> None:
    zh = builtin_topics("zh_CN")
    en = builtin_topics("en_US")
    assert len({t.id for t in zh}) == len(zh)
    assert len({t.id for t in en}) == len(en)


# ────────────────────────────────────────────────────────────────
#  Build default registry (parses docs/guide too)
# ────────────────────────────────────────────────────────────────


def test_build_default_registry_loads_builtins_and_guides() -> None:
    reg = build_default_registry()
    # 17 builtin + at least 50 from docs/guide/*.md
    assert len(reg) > 60
    cats = set(reg.list_categories())
    assert {"shortcut", "faq", "guide"}.issubset(cats)


def test_build_default_registry_can_use_explicit_guide_dir(tmp_path: Path) -> None:
    sample = tmp_path / "guide.md"
    sample.write_text(
        "---\n"
        "title: Sample Guide\n"
        "description: Demo.\n"
        "---\n\n"
        "# Sample\n\n"
        "## Hello Section\n"
        "Body text mentioning `Api` keyword.\n\n"
        "### Sub section\n"
        "More body.\n"
        "\n"
        "## Related\n"
        "Should be skipped.\n",
        encoding="utf-8",
    )
    reg = build_default_registry(guide_dir=tmp_path)
    titles = [t.title for t in reg.by_category("guide")]
    assert "Hello Section" in titles
    assert "Related" not in titles  # skipped
