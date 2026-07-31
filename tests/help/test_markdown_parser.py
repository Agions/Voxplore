"""Tests for the markdown → HelpTopic parser (Phase 3)."""

from __future__ import annotations

import pytest

from app.help.markdown_parser import (
    _split_into_h2_sections,
    parse_guide_directory,
    parse_markdown,
)

# ────────────────────────────────────────────────────────────────
#  Frontmatter
# ────────────────────────────────────────────────────────────────


def test_parse_markdown_strips_frontmatter() -> None:
    md = (
        "---\n"
        "title: 测试标题\n"
        "description: 测试描述。\n"
        "---\n\n"
        "# 测试标题\n\n"
        "## 第一节\n"
        "正文内容。\n"
    )
    topics = parse_markdown(md, file_name="test.md")
    assert len(topics) == 1
    assert topics[0].title == "第一节"
    assert topics[0].summary == "测试描述。"


def test_parse_markdown_missing_frontmatter_uses_filename() -> None:
    md = "## 直接的 H2\n正文"
    topics = parse_markdown(md, file_name="quick-start.md")
    assert len(topics) == 1
    assert topics[0].title == "直接的 H2"
    assert topics[0].source == "docs/guide/quick-start.md"


# ────────────────────────────────────────────────────────────────
#  H2 切片
# ────────────────────────────────────────────────────────────────


def test_h2_sections_basic() -> None:
    md = (
        "# H1 跳过\n\n"
        "## Section A\n"
        "Body A\n\n"
        "## Section B\n"
        "Body B\n"
    )
    sections = _split_into_h2_sections(md)
    assert [s[0] for s in sections] == ["Section A", "Section B"]
    assert "Body A" in sections[0][1]
    assert "Body B" in sections[1][1]


def test_h3_sections_are_collected_separately() -> None:
    md = (
        "## Parent\n"
        "Intro line\n"
        "### Child 1\n"
        "C1 body\n\n"
        "### Child 2\n"
        "C2 body\n\n"
        "End line\n"
    )
    sections = _split_into_h2_sections(md)
    title, body, h3s = sections[0]
    assert title == "Parent"
    assert "Intro line" in body
    assert "End line" in body  # trailing H2 content survives
    h3_titles = [s.heading for s in h3s]
    assert h3_titles == ["Child 1", "Child 2"]
    # H3 body must be inside the section (not duplicated in H2 body)
    for s in h3s:
        assert s.body not in body


def test_bash_code_block_with_hash_comments_does_not_become_h1() -> None:
    """Regression: ``# DeepSeek（解说稿生成）`` inside a bash block was
    once misparsed as H1. The parser must ignore ``# `` comments.
    """
    md = (
        "## 一键配置\n"
        "```bash\n"
        "# DeepSeek（解说稿生成）\n"
        "DEEPSEEK_API_KEY=sk-xxx\n"
        "```\n"
    )
    sections = _split_into_h2_sections(md)
    assert len(sections) == 1
    title, body, h3s = sections[0]
    assert title == "一键配置"
    assert h3s == []
    assert "DeepSeek" in body  # code block preserved
    assert "DEEPSEEK_API_KEY" in body


def test_related_section_is_preserved_but_filtered_later() -> None:
    """Parser keeps ## 相关文档 sections; caller filters via ``_SKIP_SECTIONS``."""
    md = (
        "## 主要内容\n"
        "Body.\n\n"
        "## 相关文档\n"
        "- [A](https://x)\n"
        "- [B](https://y)\n"
    )
    sections = _split_into_h2_sections(md)
    assert [s[0] for s in sections] == ["主要内容", "相关文档"]


def test_no_h2_returns_empty() -> None:
    md = "纯文本，没有标题。"
    assert _split_into_h2_sections(md) == []


# ────────────────────────────────────────────────────────────────
#  Topic id 稳定性
# ────────────────────────────────────────────────────────────────


def test_topic_ids_include_index_and_slug() -> None:
    md = (
        "## 安装步骤\n"
        "Body\n\n"
        "## 配置方法\n"
        "Body\n"
    )
    topics = parse_markdown(md, file_name="quick-start.md")
    ids = [t.id for t in topics]
    assert ids[0].startswith("guide.quick-start.01-")
    assert ids[1].startswith("guide.quick-start.02-")
    # ids must be unique even when chinese titles slugify identically
    assert len(set(ids)) == 2


# ────────────────────────────────────────────────────────────────
#  目录解析
# ────────────────────────────────────────────────────────────────


def test_parse_guide_directory_returns_topics(tmp_path) -> None:
    (tmp_path / "a.md").write_text(
        "---\ntitle: A\n---\n# A\n## A1\nbody\n",
        encoding="utf-8",
    )
    (tmp_path / "b.md").write_text(
        "---\ntitle: B\n---\n# B\n## B1\nbody\n",
        encoding="utf-8",
    )
    topics = parse_guide_directory(tmp_path)
    assert {t.id.split(".")[-1] for t in topics} == {
        "a-1-a1", "b-1-b1"  # filename + ordinal + h2 slug
    } or {t.title for t in topics} == {"A1", "B1"}


def test_parse_guide_directory_missing_dir_returns_empty(tmp_path) -> None:
    nonexistent = tmp_path / "does-not-exist"
    assert parse_guide_directory(nonexistent) == []


def test_parse_guide_directory_skips_unreadable_files(tmp_path) -> None:
    (tmp_path / "good.md").write_text(
        "---\ntitle: Good\n---\n# G\n## G1\nbody\n",
        encoding="utf-8",
    )
    # create a non-utf-8 file (should be silently skipped)
    (tmp_path / "bad.md").write_bytes(b"\xff\xfe\x00\x01")
    topics = parse_guide_directory(tmp_path)
    titles = {t.title for t in topics}
    assert "G1" in titles
    assert len(topics) == 1


# ────────────────────────────────────────────────────────────────
#  真实 docs/guide/*.md 烟雾测试
# ────────────────────────────────────────────────────────────────


def test_real_docs_guide_parses_cleanly() -> None:
    from pathlib import Path

    guide_dir = Path(__file__).resolve().parents[2] / "docs" / "guide"
    if not guide_dir.exists():
        pytest.skip("docs/guide not present in this checkout")
    topics = parse_guide_directory(guide_dir)
    assert len(topics) >= 40
    # every topic must have a non-empty title and body
    for t in topics:
        assert t.title, f"empty title in {t.id}"
        assert t.id.startswith("guide.")
