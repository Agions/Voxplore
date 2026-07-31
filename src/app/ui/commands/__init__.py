"""Command palette backend + widget facade (Phase 2).

* :class:`Command`, :class:`CommandRegistry`, :func:`merge_keywords` are
  pure-backend helpers (no Qt dependency).
* :class:`CommandPalette` is the Qt widget — imported lazily here so that
  callers pulling just the backend don't pay the PySide6 cost.
"""

from __future__ import annotations

from app.ui.commands.registry import Command, CommandRegistry, merge_keywords


def __getattr__(name: str) -> object:
    """延迟导入 widget —— commands 包不应让纯后端使用方启动 Qt。"""
    if name == "CommandPalette":
        from app.ui.widgets.command_palette import CommandPalette

        return CommandPalette
    raise AttributeError(name)


__all__ = [
    "Command",
    "CommandRegistry",
    "CommandPalette",
    "merge_keywords",
]
