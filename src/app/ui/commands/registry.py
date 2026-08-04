#!/usr/bin/env python3
"""Command Registry · Phase 2 命令面板（Cmd+K）后端。

约定
----

* 命令通过 :py:meth:`CommandRegistry.register` 在启动阶段一次性注册；
  重复注册同 ``id`` 会被覆盖（便于热重载）。
* ``Command.callback`` 永远是 ``() -> None``；需要传参的命令用闭包捕获。
* ``keywords`` 用于模糊搜索（忽略大小写、子串匹配）—— 标题 + 关键词
  任意一处命中即可。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

__all__ = ["Command", "CommandRegistry"]


@dataclass(frozen=True)
class Command:
    """一条命令的不可变描述。"""

    id: str
    title: str
    callback: Callable[[], None]
    group: str = "general"
    shortcut_hint: str = ""
    keywords: tuple[str, ...] = field(default_factory=tuple)


class CommandRegistry:
    """注册中心。线程不安全 —— 在 UI 线程使用即可。"""

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        self._order: list[str] = []

    # ── CRUD ──

    def register(self, command: Command) -> None:
        if not command.id:
            raise ValueError("Command.id is required")
        if not command.title:
            raise ValueError("Command.title is required")
        if not callable(command.callback):
            raise TypeError("Command.callback must be callable")
        if command.id not in self._commands:
            self._order.append(command.id)
        self._commands[command.id] = command

    def unregister(self, command_id: str) -> None:
        if command_id in self._commands:
            self._commands.pop(command_id, None)
            try:
                self._order.remove(command_id)
            except ValueError:
                pass

    def clear(self) -> None:
        self._commands.clear()
        self._order.clear()

    def get(self, command_id: str) -> Command | None:
        return self._commands.get(command_id)

    def __len__(self) -> int:
        return len(self._commands)

    def __contains__(self, command_id: str) -> bool:
        return command_id in self._commands

    # ── 查询 ──

    def all_commands(self) -> list[Command]:
        """按注册顺序返回所有命令（默认顺序）。"""
        return [self._commands[i] for i in self._order if i in self._commands]

    def search(self, query: str, *, limit: int = 50) -> list[Command]:
        """根据 ``query`` 做模糊匹配；空 query 返回完整列表。

        匹配规则（**按优先级**）：

        1. 完全相等（id == query）→ 排最前
        2. 标题以 query 开头
        3. 标题包含 query（不区分大小写）
        4. 任意 ``keyword`` 包含 query
        """
        commands = self.all_commands()
        if not query.strip():
            return commands[:limit]

        q = query.strip().lower()
        exact: list[tuple[int, Command]] = []
        prefix: list[tuple[int, Command]] = []
        contains: list[tuple[int, Command]] = []
        keyword_hit: list[tuple[int, Command]] = []

        for idx, cmd in enumerate(commands):
            title_lo = cmd.title.lower()
            if cmd.id.lower() == q:
                exact.append((idx, cmd))
            elif title_lo.startswith(q):
                prefix.append((idx, cmd))
            elif q in title_lo:
                contains.append((idx, cmd))
            elif any(q in kw.lower() for kw in cmd.keywords):
                keyword_hit.append((idx, cmd))

        ordered = (
            [c for _, c in exact]
            + [c for _, c in prefix]
            + [c for _, c in contains]
            + [c for _, c in keyword_hit]
        )
        return ordered[:limit]


def merge_keywords(*sources: Iterable[str]) -> tuple[str, ...]:
    """``merge_keywords("a", ["b c"])`` → ``('a', 'b', 'c')``。"""
    tokens: list[str] = []
    for src in sources:
        if not src:
            continue
        if isinstance(src, str):
            tokens.extend(src.split())
        else:
            for item in src:
                tokens.extend(item.split())
    return tuple(t for t in (s.strip() for s in tokens) if t)
