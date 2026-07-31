from __future__ import annotations

import asyncio
import inspect
import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from app.core.event_types import DomainEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[Any], None]
AsyncEventHandler = Callable[[Any], Any]


@dataclass
class _HandlerEntry:
    handler: EventHandler
    is_async: bool
    name: str = ""
    filter_fn: Callable[[Any], bool] | None = None

    def matches(self, payload: Any) -> bool:
        return self.filter_fn is None or self.filter_fn(payload)


@dataclass
class EventStats:
    published_count: int = 0
    handler_invocations: int = 0
    handler_failures: int = 0
    total_handler_time_ms: float = 0.0


class UnifiedEventBus:
    def __init__(
        self,
        *,
        async_loop: asyncio.AbstractEventLoop | None = None,
        max_workers: int = 4,
    ):
        self._handlers: dict[str, list[_HandlerEntry]] = defaultdict(list)
        self._wildcard_handlers: list[_HandlerEntry] = []
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="event-bus"
        )
        self._async_loop = async_loop
        self._stats = EventStats()
        self._stats_lock = threading.Lock()
        self._closed = False

    def subscribe(
        self,
        event_name: str,
        handler: EventHandler | AsyncEventHandler,
        *,
        name: str = "",
        filter_fn: Callable[[Any], bool] | None = None,
    ) -> Callable[[], None]:
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
        return self.subscribe(event_name, handler)

    def off(self, event_name: str, handler: EventHandler | AsyncEventHandler) -> bool:
        return self.unsubscribe(event_name, handler)

    def publish(self, event_name: str, data: Any = None) -> None:
        if self._closed:
            return
        self._dispatch(event_name, data)

    def emit(self, event_name: str, data: Any = None) -> None:
        self.publish(event_name, data)

    def publish_many(self, events: list[tuple[str, Any]] | list[DomainEvent]) -> None:
        for e in events:
            if isinstance(e, DomainEvent):
                self.publish_event(e)
            else:
                event_name, data = e
                self.publish(event_name, data)

    def publish_event(self, event: DomainEvent) -> None:
        if self._closed:
            return
        self._dispatch(event.event_name, event)

    def _dispatch(self, event_name: str, data: Any) -> None:
        with self._lock:
            handlers = list(self._handlers.get(event_name, []))
            handlers.extend(self._wildcard_handlers)

        if not handlers:
            return

        handlers = [h for h in handlers if h.matches(data)]

        if not handlers:
            return

        if len(handlers) == 1:
            self._invoke(handlers[0], event_name, data)
        else:
            futures = [
                self._executor.submit(self._invoke, h, event_name, data)
                for h in handlers
            ]
            for f in futures:
                f.add_done_callback(self._on_handler_done)

        with self._stats_lock:
            self._stats.published_count += 1

    def _invoke(self, entry: _HandlerEntry, event_name: str, data: Any) -> None:
        start = time.perf_counter()
        try:
            if entry.is_async:
                coro = entry.handler(data)
                if self._async_loop and not self._async_loop.is_closed():
                    future = asyncio.run_coroutine_threadsafe(coro, self._async_loop)
                    future.result(timeout=30)
                else:
                    try:
                        loop = asyncio.new_event_loop()
                        try:
                            loop.run_until_complete(
                                asyncio.wait_for(coro, timeout=30.0)
                            )
                        finally:
                            loop.close()
                    except RuntimeError:
                        self._executor.submit(self._invoke_async, entry, data)
                        return
            else:
                entry.handler(data)
            duration_ms = (time.perf_counter() - start) * 1000
            with self._stats_lock:
                self._stats.handler_invocations += 1
                self._stats.total_handler_time_ms += duration_ms
        except Exception as e:
            with self._stats_lock:
                self._stats.handler_failures += 1
            logger.exception(
                f"Event handler '{entry.name}' failed for event '{event_name}': {e}"
            )

    def _invoke_async(self, entry: _HandlerEntry, data: Any) -> None:
        try:
            coro = entry.handler(data)
            if self._async_loop and not self._async_loop.is_closed():
                asyncio.run_coroutine_threadsafe(coro, self._async_loop).result(
                    timeout=30
                )
            else:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(coro)
                finally:
                    loop.close()
        except Exception as e:
            logger.exception(f"Async handler '{entry.name}' failed: {e}")

    def _on_handler_done(self, fut) -> None:
        try:
            fut.result()
        except Exception as e:
            logger.debug(f"Async handler future completed with error: {e}")

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
            }

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
        with self._lock:
            if event_name:
                self._handlers.pop(event_name, None)
            else:
                self._handlers.clear()
                self._wildcard_handlers.clear()

    def close(self) -> None:
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)

    @property
    def closed(self) -> bool:
        return self._closed

    _default_instance: UnifiedEventBus | None = None
    _default_lock = threading.Lock()

    @classmethod
    def get_default(cls) -> UnifiedEventBus:
        if cls._default_instance is None:
            with cls._default_lock:
                if cls._default_instance is None:
                    cls._default_instance = cls()
        return cls._default_instance

    @classmethod
    def set_default(cls, bus: UnifiedEventBus | None) -> None:
        with cls._default_lock:
            if cls._default_instance is not None and cls._default_instance is not bus:
                cls._default_instance.close()
            cls._default_instance = bus


def get_event_bus() -> UnifiedEventBus:
    return UnifiedEventBus.get_default()


def set_event_bus(bus: UnifiedEventBus) -> None:
    UnifiedEventBus.set_default(bus)


def create_event_bus(**kwargs) -> UnifiedEventBus:
    return UnifiedEventBus(**kwargs)


def __getattr__(name: str):
    if name == "event_bus":
        return get_event_bus()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


event_bus: UnifiedEventBus


__all__ = [
    "UnifiedEventBus",
    "EventStats",
    "EventHandler",
    "AsyncEventHandler",
    "get_event_bus",
    "set_event_bus",
    "create_event_bus",
    "event_bus",
]
