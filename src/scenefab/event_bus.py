#!/usr/bin/env python3

"""
SceneFab 事件总线模块 (v1.x 兼容层)

⚠️ v2.1 变更：内部实现委托给 scenefab.core.unified_event_bus.UnifiedEventBus。
所有 v1.x 公开 API（subscribe / publish / emit / on / off / clear / clear_handlers /
unsubscribe_all / has_handlers / get_handler_count / get_registered_events /
contextmanager 形式的 `temporary_subscription` 等）保持不变。

用法（v1.x 兼容）::

    from scenefab.event_bus import EventBus, event_bus
    bus = EventBus()
    bus.subscribe("video.analyzed", handler)
    bus.publish("video.analyzed", data)

新用法（v2.1 推荐）::

    from scenefab.core.unified_event_bus import get_event_bus
    bus = get_event_bus()
    bus.publish_event(PipelineStarted(...))
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any

from scenefab.core.unified_event_bus import (
    UnifiedEventBus,
)
from scenefab.core.unified_event_bus import (
    get_event_bus as _get_unified,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# v1.x EventBus 兼容类（委托到 UnifiedEventBus）
# ──────────────────────────────────────────────────────────


class EventBus:
    """
    事件总线 v1.x 兼容类（v2.1 委托实现）

    所有方法都委托到内部 UnifiedEventBus 实例，因此：
    - v1.x 用法不变
    - 全局所有 EventBus 实例共享同一份事件状态（除非显式传入 backend）
    - 支持 v2.1 强类型事件 publish_event()
    """

    def __init__(self):
        self._backend: UnifiedEventBus = _get_unified()

    # ── 订阅 / 退订 ──

    def subscribe(self, event_name: str, handler: Callable) -> None:
        self._backend.subscribe(event_name, handler)

    def unsubscribe(self, event_name: str, handler: Callable) -> None:
        self._backend.unsubscribe(event_name, handler)

    @contextmanager
    def temporary_subscription(
        self, event_name: str, handler: Callable
    ) -> Generator[None, None, None]:
        """临时订阅（上下文退出时自动取消）"""
        unsubscribe_fn = self._backend.subscribe(event_name, handler)
        try:
            yield
        finally:
            unsubscribe_fn()

    # ── 发布 ──

    def publish(self, event_name: str, data: Any = None) -> None:
        self._backend.publish(event_name, data)

    def emit(self, event_name: str, data: Any = None) -> None:
        """emit 是 publish 的别名（保持 API 兼容性）"""
        self._backend.publish(event_name, data)

    # ── 清理 / 查询 ──

    def clear(self, event_name: str | None = None) -> None:
        self._backend.clear_handlers(event_name)

    def clear_handlers(self, event_name: str | None = None) -> None:
        self._backend.clear_handlers(event_name)

    def unsubscribe_all(self, event_name: str) -> int:
        """取消指定事件的所有处理器，返回移除数量"""
        count = self._backend.handler_count(event_name)
        self._backend.clear_handlers(event_name)
        return count

    def has_handlers(self, event_name: str) -> bool:
        return self._backend.has_handlers(event_name)

    def get_handler_count(self, event_name: str | None = None) -> int:
        return self._backend.handler_count(event_name)

    def get_registered_events(self) -> list[str]:
        return self._backend.registered_events()

    # ── v2.1 新能力 ──

    def publish_event(self, event: Any) -> None:
        """发布类型化 DomainEvent"""
        self._backend.publish_event(event)

    def replay_all(self) -> int:
        return self._backend.replay_all()

    def stats(self) -> dict[str, Any]:
        return self._backend.stats()

    # ── 生命周期 ──
    def close(self) -> None:
        """关闭底层 UnifiedEventBus（释放投递线程池）。

        由 Application.shutdown() 统一调用，幂等。
        """
        self._backend.close()

    @property
    def closed(self) -> bool:
        return self._backend.closed


# 全局事件总线实例（v1.x 兼容名）
event_bus = EventBus()


__all__ = ["EventBus", "event_bus"]
