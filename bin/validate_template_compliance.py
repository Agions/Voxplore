#!/usr/bin/env python3
"""Template compliance validator for AICoding architecture deliverables.

Usage:
    python3 bin/validate_template_compliance.py \
        --output-dir .workbuddy/output --filter research_report.md

Validates that the produced document contains every section required by its
matching template. Matching strategy:
  * Numbered headings (e.g. "3.1", "2.2.1") are matched by their leading
    section-number prefix. This tolerates template placeholder headings such
    as "2.2.1 B1 - <标杆系统名称>" (the placeholder is meant to be replaced
    by the real name) and tolerates reasonable subtitle rewrites
    ("3.1 对比矩阵（标杆系统 5 维度加权评分）" still satisfies "3.1 对比矩阵").
  * Unnumbered headings (e.g. the H1 title) are matched by normalized
    startswith, ignoring parentheticals.
  * The template "使用说明" meta/guidance section is skipped because it is
    instructions for filling the template, not a deliverable section.

Exits 0 when all required sections are present, 1 otherwise. This is the
objective gate used by the team lead before a human-review step.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

DEFAULT_TEMPLATES = (
    "/Users/zfkc/.workbuddy/plugins/marketplaces/experts/plugins/"
    "aicoding-architecture-expert-team/skills/aicoding-team-bootstrap/templates"
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_MIN_BYTES = 800
_SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)")
_META_SKIP = ("模版使用说明", "模板使用说明")  # meta guidance sections, not deliverable


def _normalize(heading: str) -> str:
    return re.sub(r"\s+", "", heading).lower()


def extract_headings(path: str) -> list[str]:
    heads: list[str] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = _HEADING_RE.match(line)
            if m:
                heads.append(m.group(2).strip())
    return heads


def _section_prefix(heading: str) -> str | None:
    m = _SECTION_RE.match(heading.strip())
    return m.group(1) if m else None


def _requirement(heading: str) -> tuple[str, str | None]:
    """Return (mode, value).

    mode == 'prefix'   -> an output heading whose section-number prefix equals value
    mode == 'startswith' -> an output heading whose normalized text starts with value
    """
    prefix = _section_prefix(heading)
    if prefix is not None:
        return ("prefix", prefix)
    core = re.sub(r"[（(].*?[)）]", "", _normalize(heading))
    return ("startswith", core or None)


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate architecture doc vs template.")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--filter", required=True)
    ap.add_argument(
        "--templates-dir",
        default=os.environ.get("AICODING_TEMPLATES_DIR", DEFAULT_TEMPLATES),
    )
    args = ap.parse_args()

    out_path = os.path.join(args.output_dir, args.filter)
    if not os.path.exists(out_path):
        print(f"[FAIL] 输出文件不存在: {out_path}")
        return 1

    size = os.path.getsize(out_path)
    if size < _MIN_BYTES:
        print(f"[FAIL] 文件过小 ({size} bytes < {_MIN_BYTES})，疑似空稿")
        return 1

    tmpl_path = os.path.join(args.templates_dir, args.filter)
    if not os.path.exists(tmpl_path):
        print(f"[WARN] 无对应模板: {tmpl_path}，仅做基本存在性/长度校验")
        print(f"[PASS] 基本校验通过（文件 {size} bytes）")
        return 0

    required = extract_headings(tmpl_path)
    out_heads = extract_headings(out_path)
    out_norm = [_normalize(h) for h in out_heads]
    out_prefixes = [_section_prefix(h) for h in out_heads]

    missing = []
    for h in required:
        if any(skip in h for skip in _META_SKIP):
            continue  # meta/guidance section, not a deliverable section
        mode, value = _requirement(h)
        if mode == "prefix":
            if value not in out_prefixes:
                missing.append(h)
        else:
            if not value or not any(on.startswith(value) for on in out_norm):
                missing.append(h)

    if missing:
        print(
            f"[FAIL] {args.filter} 缺少以下模板章节"
            f"（模板 {len(required)} 章节 / 输出 {len(out_heads)} 章节）："
        )
        for m in missing:
            print(f"  - {m}")
        return 1

    print(
        f"[PASS] {args.filter} 结构校验通过：模板章节全部满足"
        f"（编号前缀匹配 + 占位符容错 + 跳过元说明），输出共 {len(out_heads)} 个章节。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
