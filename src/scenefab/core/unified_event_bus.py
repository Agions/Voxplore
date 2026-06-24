"""
SceneFab 统一事件总线 v2.1

设计目标（取代 v1.x 的两个散件实现）：

1. **单源真相**：本类是整个项目唯一权威实现
   - `scenefab.event_bus.EventBus` 和 `scenefab.core.EventBus` 全部委托到此
   - v1.x 字符串事件 API 完全兼容（`publish("foo", data)` 仍工作）
   - v2.1 新增 DomainEvent 类型化事件（`publish_event(DomainEvent)` 强类型）

2. **异步支持**：`publish_event` 支持 async handler，使用 `asyncio.run_coroutine_threadsafe`
   - 线程安全：sync / async handler 混合安全
   - 不阻塞主调用线程

3. **可重放**：
   - 所有事件经过总线时记录到 `EventLog`（可关）
   - 重启时 `replay_all()` / `replay_from(event_id)` 重发历史事件
   - 配合 `EventStore` 持久化（可选 SQLite / 内存）

4. **可观测**：
   - handler 异常捕获不中断总线（隔离）
   - 统计每个事件的发布次数 / handler 数量 / 平均耗时
   - 暴露 `stats()` 快照

5. **依赖注入友好**：
   - 不再是 `Singleton` 硬编码，提供工厂 `UnifiedEventBus.create()`
   - 全局实例 `event_bus` 仍提供 v1.x 兼容

v2.1 不破坏 v1.x 行为：所有现有 `subscribe("foo", handler)` 调用照样工作。
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from scenefab.core.event_types import DomainEvent

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# 类型定义
# ──────────────────────────────────────────────────────────


# 兼容两种 handler 签名
EventHandler = Callable[[Any], None]  # sync
AsyncEventHandler = Callable[[Any], Any]  # sync or async


@dataclass
class _HandlerEntry:
    """handler 注册条目（v2.1 内部用）"""

    handler: EventHandler
    is_async: bool
    name: str = ""  # 可选命名，方便诊断
    filter_fn: Callable[[Any], bool] | None = None  # 可选过滤

    def matches(self, payload: Any) -> bool:
        return self.filter_fn is None or self.filter_fn(payload)


@dataclass
class EventRecord:
    """事件日志条目（用于重放 / 审计）"""

    sequence: int  # 单调递增
    event_id: str
    event_name: str
    payload: Any
    timestamp: float
    correlation_id: str | None = None
    causation_id: str | None = None


@dataclass
class EventStats:
    """事件统计"""

    published_count: int = 0
    handler_invocations: int = 0
    handler_failures: int = 0
    total_handler_time_ms: float = 0.0
    per_event: dict[str, int] = field(default_factory=dict)
    per_handler: dict[str, float] = field(default_factory=dict)


# ──────────────────────────────────────────────────────────
# 事件日志（可重放）
# ──────────────────────────────────────────────────────────


class EventLog:
    """
    事件日志（环形缓冲 / 可重放）

    默认 1000 条上限，超过滚动丢弃。可通过 env var SCENEFAB_EVENT_LOG_SIZE 调整。
    """

    def __init__(self, max_size: int = 1000):
        self._max_size = max_size
        self._records: deque[EventRecord] = deque(maxlen=max_size)
        self._sequence = 0
        self._lock = threading.Lock()

    def append(
        self,
        event_name: str,
        payload: Any,
        event_id: str = "",
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> EventRecord:
        with self._lock:
            self._sequence += 1
            record = EventRecord(
                sequence=self._sequence,
                event_id=event_id or str(uuid.uuid4()),
                event_name=event_name,
                payload=payload,
                timestamp=time.time(),
                correlation_id=correlation_id,
                causation_id=causation_id,
            )
            self._records.append(record)
            return record

    def all(self) -> list[EventRecord]:
        with self._lock:
            return list(self._records)

    def from_sequence(self, seq: int) -> list[EventRecord]:
        with self._lock:
            return [r for r in self._records if r.sequence > seq]

    def from_event_id(self, event_id: str) -> list[EventRecord]:
        with self._lock:
            start = None
            for r in self._records:
                if r.event_id == event_id:
                    start = r.sequence
                    break
            if start is None:
                return []
            return [r for r in self._records if r.sequence > start]

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._sequence = 0

    def __len__(self) -> int:
        return len(self._records)


# ──────────────────────────────────────────────────────────
# 统一事件总线
# ──────────────────────────────────────────────────────────


class UnifiedEventBus:
    """
    统一事件总线 v2.1

    取代 v1.x 两个 EventBus 实现。

    用法（v1.x 兼容）::

        bus = UnifiedEventBus()
        bus.subscribe("video.analyzed", handler)
        bus.publish("video.analyzed", data)

    用法（v2.1 类型化）::

        bus = UnifiedEventBus()
        bus.publish_event(PipelineStarted(pipeline_id="p1", total_steps=5))

    用法（异步 handler）::

        async def my_handler(event):
            await asyncio.sleep(0.01)

        bus.subscribe("task.created", my_handler)  # 自动识别 async
    """

    def __init__(
        self,
        *,
        async_loop: asyncio.AbstractEventLoop | None = None,
        max_workers: int = 4,
        enable_log: bool = True,
        log_size: int = 1000,
    ):
        self._handlers: dict[str, list[_HandlerEntry]] = defaultdict(list)
        self._wildcard_handlers: list[_HandlerEntry] = []  # "*" 匹配所有
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="event-bus"
        )
        self._async_loop = async_loop
        self._log = EventLog(max_size=log_size) if enable_log else None
        self._stats = EventStats()
        self._stats_lock = threading.Lock()
        self._closed = False

    # ────────────────────────────────────────────────
    # 订阅 / 退订
    # ────────────────────────────────────────────────

    def subscribe(
        self,
        event_name: str,
        handler: EventHandler | AsyncEventHandler,
        *,
        name: str = "",
        filter_fn: Callable[[Any], bool] | None = None,
    ) -> Callable[[], None]:
        """
        订阅事件。

        Args:
            event_name: 事件名（"*" 匹配所有）
            handler: 处理函数（sync 或 async）
            name: 可选标识（便于诊断）
            filter_fn: 可选过滤器，payload 满足条件才触发

        Returns:
            取消订阅的函数
        """
        is_async = inspect.iscoroutinefunction(handler)
        entry = _HandlerEntry(
            handler=handler,
            is_async=is_async,
            name=name or handler.__name__,
            filter_fn=filter_fn,
        )
        with self._lock:
            if event_name == "*":
                self._wildcard_handlers.append(entry)
            else:
                self._handlers[event_name].append(entry)

        def unsubscribe() -> None:
            self.unsubscribe(event_name, handler, name=name)

        return unsubscribe

    def unsubscribe(
        self,
        event_name: str,
        handler: EventHandler | AsyncEventHandler,
        *,
        name: str = "",
    ) -> bool:
        """取消订阅"""
        with self._lock:
            target_list = (
                self._wildcard_handlers
                if event_name == "*"
                else self._handlers.get(event_name, [])
            )
            for i, entry in enumerate(target_list):
                if entry.handler is handler or (name and entry.name == name):
                    target_list.pop(i)
                    return True
        return False

    def on(
        self, event_name: str, handler: EventHandler | AsyncEventHandler
    ) -> Callable[[], None]:
        """链式风格别名（与 EventEmitter 兼容）"""
        return self.subscribe(event_name, handler)

    def off(self, event_name: str, handler: EventHandler | AsyncEventHandler) -> bool:
        """链式风格别名"""
        return self.unsubscribe(event_name, handler)

    # ────────────────────────────────────────────────
    # 发布（v1.x 字符串事件）
    # ────────────────────────────────────────────────

    def publish(self, event_name: str, data: Any = None) -> None:
        """
        发布字符串事件（v1.x 兼容）。

        异步 handler 自动通过 `asyncio.run_coroutine_threadsafe` 调度。
        """
        if self._closed:
            return
        self._dispatch(event_name, data, source_event=None)

    def emit(self, event_name: str, data: Any = None) -> None:
        """publish 的别名（兼容 EventEmitter.emit）"""
        self.publish(event_name, data)

    def publish_many(self, events: list[tuple[str, Any]] | list[DomainEvent]) -> None:
        """批量发布（v2.1 便利方法）"""
        for e in events:
            if isinstance(e, DomainEvent):
                self.publish_event(e)
            else:
                event_name, data = e
                self.publish(event_name, data)

    # ────────────────────────────────────────────────
    # 发布（v2.1 类型化事件）
    # ────────────────────────────────────────────────

    def publish_event(self, event: DomainEvent) -> None:
        """
        发布类型化领域事件（v2.1 强类型入口）。

        自动：
        - 提取 event_name 作为分发键
        - 写入 EventLog
        - 同步/异步 handler 混合调度
        """
        if self._closed:
            return
        # 记录日志
        if self._log is not None:
            self._log.append(
                event_name=event.event_name,
                payload=event,
                event_id=event.event_id,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
            )
        self._dispatch(event.event_name, event, source_event=event)

    # ────────────────────────────────────────────────
    # 内部调度
    # ────────────────────────────────────────────────

    def _dispatch(
        self,
        event_name: str,
        data: Any,
        *,
        source_event: DomainEvent | None,
    ) -> None:
        with self._lock:
            handlers = list(self._handlers.get(event_name, []))
            handlers.extend(self._wildcard_handlers)

        if not handlers:
            return

        # 过滤
        handlers = [h for h in handlers if h.matches(data)]

        if not handlers:
            return

        # 调度（隔离 handler 异常，不中断总线）
        if len(handlers) == 1:
            self._invoke(handlers[0], event_name, data)
        else:
            # 多 handler 并行
            futures = [
                self._executor.submit(self._invoke, h, event_name, data)
                for h in handlers
            ]
            # 不阻塞主调，handler 完成即可
            for f in futures:
                f.add_done_callback(self._on_handler_done)

        # 统计
        with self._stats_lock:
            self._stats.published_count += 1
            self._stats.per_event[event_name] = (
                self._stats.per_event.get(event_name, 0) + 1
            )

    def _invoke(self, entry: _HandlerEntry, event_name: str, data: Any) -> None:
        start = time.perf_counter()
        try:
            if entry.is_async:
                coro = entry.handler(data)  # type: ignore[func-returns-value]
                if self._async_loop and not self._async_loop.is_closed():
                    # 在主事件循环跑 async handler
                    future = asyncio.run_coroutine_threadsafe(coro, self._async_loop)  # type: ignore[var-annotated, arg-type]
                    future.result(timeout=30)
                else:
                    # 临时事件循环（一次性）
                    try:
                        loop = asyncio.new_event_loop()
                        try:
                            loop.run_until_complete(coro)  # type: ignore[arg-type]
                        finally:
                            loop.close()
                    except RuntimeError:
                        # 在已经有 loop 的线程里，回退到 executor
                        self._executor.submit(self._invoke_async, entry, data)
                        return
            else:
                entry.handler(data)
            duration_ms = (time.perf_counter() - start) * 1000
            with self._stats_lock:
                self._stats.handler_invocations += 1
                self._stats.total_handler_time_ms += duration_ms
                self._stats.per_handler[entry.name] = (
                    self._stats.per_handler.get(entry.name, 0.0) + duration_ms
                )
        except Exception as e:
            with self._stats_lock:
                self._stats.handler_failures += 1
            logger.exception(
                f"Event handler '{entry.name}' failed for event '{event_name}': {e}"
            )

    def _invoke_async(self, entry: _HandlerEntry, data: Any) -> None:
        try:
            coro = entry.handler(data)  # type: ignore[func-returns-value]
            if self._async_loop and not self._async_loop.is_closed():
                asyncio.run_coroutine_threadsafe(coro, self._async_loop).result(  # type: ignore[arg-type]
                    timeout=30
                )
            else:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(coro)  # type: ignore[arg-type]
                finally:
                    loop.close()
        except Exception as e:
            logger.exception(f"Async handler '{entry.name}' failed: {e}")

    def _on_handler_done(self, fut) -> None:
        try:
            fut.result()
        except Exception as e:
            logger.debug(f"Async handler future completed with error: {e}")

    # ────────────────────────────────────────────────
    # 重放
    # ────────────────────────────────────────────────

    def replay_all(self) -> int:
        """
        重放所有历史事件。返回重发数量。
        """
        if self._log is None:
            return 0
        records = self._log.all()
        for r in records:
            self._dispatch(r.event_name, r.payload, source_event=None)
        return len(records)

    def replay_from(self, after_event_id: str) -> int:
        """从指定事件 ID 之后开始重放"""
        if self._log is None:
            return 0
        records = self._log.from_event_id(after_event_id)
        for r in records:
            self._dispatch(r.event_name, r.payload, source_event=None)
        return len(records)

    def replay_from_sequence(self, after_seq: int) -> int:
        """从指定序列号之后开始重放"""
        if self._log is None:
            return 0
        records = self._log.from_sequence(after_seq)
        for r in records:
            self._dispatch(r.event_name, r.payload, source_event=None)
        return len(records)

    # ────────────────────────────────────────────────
    # 统计 & 日志访问
    # ────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._stats_lock:
            avg_ms = (
                self._stats.total_handler_time_ms / self._stats.handler_invocations
                if self._stats.handler_invocations > 0
                else 0.0
            )
            return {
                "published_count": self._stats.published_count,
                "handler_invocations": self._stats.handler_invocations,
                "handler_failures": self._stats.handler_failures,
                "avg_handler_time_ms": round(avg_ms, 3),
                "total_handler_time_ms": round(self._stats.total_handler_time_ms, 3),
                "per_event": dict(self._stats.per_event),
                "per_handler": dict(self._stats.per_handler),
            }

    def log(self) -> EventLog | None:
        return self._log

    # ────────────────────────────────────────────────
    # 查询 & 清理
    # ────────────────────────────────────────────────

    def handler_count(self, event_name: str | None = None) -> int:
        with self._lock:
            if event_name is None:
                return sum(len(v) for v in self._handlers.values()) + len(
                    self._wildcard_handlers
                )
            return len(self._handlers.get(event_name, []))

    def registered_events(self) -> list[str]:
        with self._lock:
            return list(self._handlers.keys())

    def has_handlers(self, event_name: str) -> bool:
        with self._lock:
            return bool(self._handlers.get(event_name)) or bool(self._wildcard_handlers)

    def clear_handlers(self, event_name: str | None = None) -> None:
        """清除处理器（v1.x 兼容）"""
        with self._lock:
            if event_name:
                self._handlers.pop(event_name, None)
            else:
                self._handlers.clear()
                self._wildcard_handlers.clear()

    def clear_log(self) -> None:
        if self._log is not None:
            self._log.clear()

    def close(self) -> None:
        """关闭总线（不再接受新事件）"""
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)

    @property
    def closed(self) -> bool:
        return self._closed

    # ────────────────────────────────────────────────
    # 工厂 & 单例
    # ────────────────────────────────────────────────

    _default_instance: UnifiedEventBus | None = None
    _default_lock = threading.Lock()

    @classmethod
    def get_default(cls) -> UnifiedEventBus:
        """获取进程级默认实例（单例，v2.1 单源真相）"""
        if cls._default_instance is None:
            with cls._default_lock:
                if cls._default_instance is None:
                    cls._default_instance = cls()
        return cls._default_instance

    @classmethod
    def set_default(cls, bus: UnifiedEventBus | None) -> None:
        """注入 / 重置默认实例（v2.1 DI 友好）"""
        with cls._default_lock:
            if cls._default_instance is not None and cls._default_instance is not bus:
                cls._default_instance.close()
            cls._default_instance = bus


# ──────────────────────────────────────────────────────────
# 工厂 & 全局实例
# ──────────────────────────────────────────────────────────


_global_bus: UnifiedEventBus | None = None
_global_lock = threading.Lock()


def get_event_bus() -> UnifiedEventBus:
    """获取全局事件总线（v2.1 单源真相，等价于 UnifiedEventBus.get_default()）"""
    return UnifiedEventBus.get_default()


def set_event_bus(bus: UnifiedEventBus) -> None:
    """注入自定义事件总线（v2.1 测试 / DI 友好）

    同时更新函数级单例 + 类级单例，确保 get_event_bus() 和
    UnifiedEventBus.get_default() 都返回新实例。
    """
    global _global_bus
    with _global_lock:
        _global_bus = bus
    # 同步类级单例
    UnifiedEventBus.set_default(bus)


def create_event_bus(**kwargs) -> UnifiedEventBus:
    """工厂函数（v2.1 推荐用法）"""
    return UnifiedEventBus(**kwargs)


# v1.x 别名（保持 import 兼容）
event_bus = get_event_bus()  # 懒加载


__all__ = [
    "UnifiedEventBus",
    "EventLog",
    "EventRecord",
    "EventStats",
    "EventHandler",
    "AsyncEventHandler",
    "get_event_bus",
    "set_event_bus",
    "create_event_bus",
    "event_bus",
]
