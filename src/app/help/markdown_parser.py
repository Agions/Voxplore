"""解析 ``docs/guide/*.md`` 为 ``HelpTopic`` 列表。

设计要点
========

1. **零第三方依赖**：使用 ``re`` + 内置字符串处理，避免引入 markdown 解析器。
2. **frontmatter 容错**：只识别最常见的 ``---\\nkey: value\\n---`` 形式，缺失字段
   不会让整个文件解析失败。
3. **H2 章节为主粒度**：每个 H2 切片为一个 ``HelpTopic``，H3 作为子 ``HelpSection``；
   这种粒度与 docs/guide/*.md 现有结构（每篇 4-8 个 H2）正好匹配。
4. **相关文档章节跳过**：「## 相关文档」是 link 列表而非内容，解析时丢弃，
   避免污染搜索结果。

调用方式
========

>>> from pathlib import Path
>>> from app.help.markdown_parser import parse_guide_directory
>>> topics = parse_guide_directory(Path("docs/guide"))
>>> topics[0].title
'快速开始'
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import HelpSection, HelpTopic

# ---------------------------------------------------------------------------
# 内部常量
# ---------------------------------------------------------------------------

# YAML frontmatter 边界：必须从文件第 1 行起。
_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<body>.*?)\n---\s*\n",
    re.DOTALL,
)

# 单行 frontmatter 字段（仅支持最常见的 title / description）。
_FIELD_RE = re.compile(r"^(?P<key>title|description)\s*:\s*(?P<value>.+?)\s*$")

# 标题识别：行首 2-4 个 #，后接内容。
_HEADING_RE = re.compile(r"^(?P<level>#{2,4})\s+(?P<text>.+?)\s*$")

# 帮助文档跳过章节标题（不构成内容，仅为 link 列表）。
_SKIP_SECTIONS: frozenset[str] = frozenset({"相关文档", "Related", "Next steps"})

# 文件名 → 简短英文 slug；用于 topic.id 与 category。
_FILE_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    """把任意字符串降级为 ASCII slug。"""
    lowered = text.strip().lower()
    slug = _FILE_SLUG_RE.sub("-", lowered).strip("-")
    return slug or "topic"


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """从 markdown 文本头部剥离 YAML frontmatter。

    Returns:
        (fields, remainder) — 字段字典 + frontmatter 之后的正文。
    """
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return {}, text

    fields: dict[str, str] = {}
    for line in match.group("body").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        field_match = _FIELD_RE.match(stripped)
        if field_match is not None:
            fields[field_match.group("key")] = field_match.group(
                "value").strip()

    remainder = text[match.end():]
    return fields, remainder


# ---------------------------------------------------------------------------
# Markdown 切片
# ---------------------------------------------------------------------------


def _split_into_h2_sections(body: str) -> list[tuple[str, str, list[HelpSection]]]:
    """按 H2 切分正文，返回 [(h2_title, h2_body, h3_sections), ...]。

    策略：遇到 H2 就立即 append 进 ``sections``；遇到 H3 时把内容追加到
    ``sections`` 中**最后一项**的 [2] 列表。这样 H3 的 body 不会丢失。
    文件末尾的 H3 / H2 在 ``_flush_*`` 中补齐。
    """
    sections: list[tuple[str, str, list[HelpSection]]] = []
    current_h2: str | None = None
    current_body_lines: list[str] = []
    current_h3: str | None = None
    current_h3_lines: list[str] = []
    pending_blank = False  # 上一行是否为空白行（用于识别 H3 段结束）

    def _flush_h3() -> None:
        nonlocal current_h3, current_h3_lines
        if current_h3 is not None and sections:
            body_text = "\n".join(current_h3_lines).strip("\n")
            if body_text.strip():
                # HelpSection 是 frozen dataclass，不支持 append，改用 list。
                sections[-1][2].append(
                    HelpSection(heading=current_h3, body=body_text, level=3)
                )
        current_h3 = None
        current_h3_lines = []

    def _flush_h2() -> None:
        # 把上一段 H2 收集到的 body 写回 sections[-1]，
        # 避免 H2 触发时直接 append 空 body 而丢失正文。
        nonlocal current_h2, current_body_lines
        if current_h2 is not None and sections:
            h2_title, h2_body, h3_list = sections[-1]
            if h2_title == current_h2:
                extra = "\n".join(current_body_lines).strip("\n").strip()
                merged = (
                    (h2_body + "\n" + extra).strip()
                    if (h2_body or extra)
                    else ""
                )
                sections[-1] = (h2_title, merged, h3_list)
        current_h2 = None
        current_body_lines = []

    for raw_line in body.splitlines():
        heading_match = _HEADING_RE.match(raw_line)
        if heading_match is not None:
            level = len(heading_match.group("level"))
            text = heading_match.group("text").strip()
            pending_blank = False  # heading 重置空白标记
            if level == 2:
                # 先 flush 上一段 H2 / H3，再开新 H2。
                _flush_h3()
                _flush_h2()
                # 立即 append 新 H2 到 sections（占位），使后续 H3 可正确 append。
                sections.append((text, "", []))
                current_h2 = text
                current_body_lines = []
            elif level == 3 and current_h2 is not None:
                # 在 append 新 H3 之前 flush 上一个 H3。
                _flush_h3()
                current_h3 = text
                current_h3_lines = []
            continue

        # 空行：保留原文结构，同时标记段落分隔。
        if not raw_line.strip():
            pending_blank = True
            if current_h3 is not None:
                current_h3_lines.append(raw_line)
            elif current_h2 is not None:
                current_body_lines.append(raw_line)
            continue

        # 非空非 heading 行：若 H3 段已因空行结束，后续文本归 H2 body。
        if current_h3 is not None and pending_blank:
            _flush_h3()
        if current_h3 is not None:
            current_h3_lines.append(raw_line)
        elif current_h2 is not None:
            current_body_lines.append(raw_line)
        pending_blank = False

    _flush_h3()
    _flush_h2()
    return sections


def _slugify_filename(path: Path) -> str:
    """从文件名提取英文 slug（不含扩展名）。"""
    return _slugify(path.stem)


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------


def parse_markdown(
    text: str,
    *,
    file_name: str = "",
) -> list[HelpTopic]:
    """解析单篇 markdown 文本，返回 0-N 个 ``HelpTopic``。

    Args:
        text: 完整 markdown 文本。
        file_name: 文件名（不含路径），用于 ``id`` 与 ``source`` 字段。

    Returns:
        ``HelpTopic`` 列表，顺序与文件中 H2 出现顺序一致。
    """
    fields, remainder = _parse_frontmatter(text)
    title = fields.get("title") or ""
    description = fields.get("description") or ""
    file_slug = _slugify_filename(Path(file_name)) if file_name else "topic"

    sections = _split_into_h2_sections(remainder)
    topics: list[HelpTopic] = []
    for index, (h2_title, h2_body, h3_sections) in enumerate(sections, start=1):
        if h2_title in _SKIP_SECTIONS:
            continue
        topic_id = f"guide.{file_slug}.{index:02d}-{_slugify(h2_title)}"
        # tags = 标题 + 描述中的中文 2-gram + slug，便于搜索命中。
        tag_candidates = [h2_title, title, description, file_slug]
        tags = tuple(sorted({t for t in tag_candidates if t}))
        topics.append(
            HelpTopic(
                id=topic_id,
                title=h2_title,
                category="guide",
                summary=description,
                source=f"docs/guide/{file_name}" if file_name else "",
                tags=tags,
                sections=tuple(h3_sections),
                body=h2_body,
            )
        )
    return topics


def parse_guide_directory(directory: Path) -> list[HelpTopic]:
    """解析 ``docs/guide/*.md`` 目录下所有 markdown 文件。

    Args:
        directory: 包含 ``.md`` 文件的目录。

    Returns:
        所有 ``HelpTopic`` 拼接后的列表，跳过解析失败的文件（不抛异常）。
    """
    if not directory.exists():
        return []
    all_topics: list[HelpTopic] = []
    for path in sorted(directory.glob("*.md")):
        try:
            # 使用 errors="replace" 避免单文件编码错误让整个目录解析失败。
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        all_topics.extend(parse_markdown(text, file_name=path.name))
    return all_topics


__all__ = ["parse_markdown", "parse_guide_directory"]
