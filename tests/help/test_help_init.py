"""Tests for ``app.help/__init__.py`` ``build_default_registry`` & friends."""

from __future__ import annotations

from pathlib import Path

from app.help import HelpRegistry, build_default_registry


def test_build_default_registry_returns_help_registry() -> None:
    assert isinstance(build_default_registry(), HelpRegistry)


def test_build_default_registry_zh_has_builtins_and_guides() -> None:
    reg = build_default_registry(language="zh_CN")
    builtin_cats = {"shortcut", "faq", "onboarding"}
    actual_cats = set(reg.list_categories())
    assert builtin_cats.issubset(actual_cats)


def test_build_default_registry_en_swaps_builtins() -> None:
    reg_en = build_default_registry(language="en_US")
    reg_zh = build_default_registry(language="zh_CN")
    # ids are stable across languages but titles differ
    en_ids = {t.id for t in reg_en.list()}
    zh_ids = {t.id for t in reg_zh.list()}
    assert en_ids == zh_ids
    # title differs (Command Palette vs 命令面板)
    en_cmd = reg_en.get("shortcut.command-palette")
    zh_cmd = reg_zh.get("shortcut.command-palette")
    assert en_cmd.title != zh_cmd.title


def test_build_default_registry_with_custom_guide_dir(tmp_path: Path) -> None:
    sample = tmp_path / "guide.md"
    sample.write_text(
        "---\ntitle: Custom\n---\n# Custom\n## Topic\nbody\n",
        encoding="utf-8",
    )
    reg = build_default_registry(guide_dir=tmp_path, language="en_US")
    # builtin pool + 1 from custom dir
    assert any(t.id.startswith("guide.guide.") for t in reg.list())


def test_build_default_registry_idempotent_when_dir_missing(tmp_path: Path) -> None:
    """Passing a path that doesn't exist is not fatal."""
    reg = build_default_registry(
        guide_dir=tmp_path / "missing", language="zh_CN"
    )
    assert len(reg) >= 15  # only builtins survive
