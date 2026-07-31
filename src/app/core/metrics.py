#!/usr/bin/env python3
"""轻量进程内指标层 — Phase 4 · observability。

提供：
- ``Counter``：按 name + label 维度累计整数
- ``Histogram``：滑动窗口统计 p50 / p95 / count / max
- ``Timer``：上下文管理器，自动计算耗时 ms 并打点
- ``MetricsRegistry``：单例注册表，线程安全，支持 ``snapshot()`` 导出 JSON
- ``bind_to_event_bus``：把所有 EventBus 发布的事件计数到 ``events.published``

设计上：
- 仅依赖标准库，无外部 prometheus / opentelemetry 依赖
- 主线程和工作线程共用同一个 registry（threading.Lock 保护）
- 数据保存于内存；如需落盘，调用方周期性 ``snapshot()`` 后自行持久化
"""

from __future__ import annotations

import json
import logging
import math
import threading
import time
from collections import defaultdict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────
#  数据容器
# ────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class _CounterBucket:
    """单 (name, labels) 组合的计数。"""

    value: float = 0.0
    first_seen: float = field(default_factory=time.time)
    last_incr: float = field(default_factory=time.time)


@dataclass(slots=True)
class _HistogramBucket:
    """单 (name, labels) 组合的直方图。"""

    samples: list[float] = field(default_factory=list)
    max_samples: int = 1024
    count: int = 0
    sum: float = 0.0
    max: float = 0.0
    last_value: float = 0.0

    def observe(self, value: float) -> None:
        if len(self.samples) >= self.max_samples:
            # 简单窗口策略：丢弃最旧的一半
            self.samples = self.samples[self.max_samples // 2:]
        self.samples.append(value)
        self.count += 1
        self.sum += value
        if value > self.max:
            self.max = value
        self.last_value = value

    def percentile(self, p: float) -> float:
        if not self.samples:
            return 0.0
        ordered = sorted(self.samples)
        idx = max(0, min(len(ordered) - 1, int(math.ceil(p * len(ordered))) - 1))
        return ordered[idx]


def _label_key(labels: dict[str, str] | None) -> tuple[tuple[str, str], ...]:
    """dict → 排序后的 tuple，作为 dict 键。"""
    if not labels:
        return ()
    return tuple(sorted(labels.items()))


# ────────────────────────────────────────────────────────────────
#  指标注册表
# ────────────────────────────────────────────────────────────────


class MetricsRegistry:
    """进程级单例指标注册表。"""

    _instance: MetricsRegistry | None = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> MetricsRegistry:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self) -> None:
        self._lock = threading.RLock()
        self._counters: dict[str, dict[tuple,
                                       _CounterBucket]] = defaultdict(dict)
        self._histograms: dict[str, dict[tuple,
                                         _HistogramBucket]] = defaultdict(dict)
        self._gauges: dict[str, float] = {}
        self._tag_to_name: dict[str, str] = {}  # event_name → metric_name

    # ─── Counter ───────────────────────────────────────────────

    def counter_inc(
        self,
        name: str,
        *,
        labels: dict[str, str] | None = None,
        value: float = 1.0,
    ) -> None:
        if value < 0:
            raise ValueError("counter value must be >= 0")
        key = _label_key(labels)
        with self._lock:
            bucket = self._counters[name].get(key)
            if bucket is None:
                bucket = _CounterBucket()
                self._counters[name][key] = bucket
            bucket.value += value
            bucket.last_incr = time.time()

    def counter_value(
        self, name: str, *, labels: dict[str, str] | None = None
    ) -> float:
        key = _label_key(labels)
        with self._lock:
            bucket = self._counters.get(name, {}).get(key)
            return bucket.value if bucket else 0.0

    # ─── Histogram ─────────────────────────────────────────────

    def histogram_observe(
        self,
        name: str,
        value: float,
        *,
        labels: dict[str, str] | None = None,
    ) -> None:
        if value < 0:
            raise ValueError("histogram value must be >= 0")
        key = _label_key(labels)
        with self._lock:
            bucket = self._histograms[name].get(key)
            if bucket is None:
                bucket = _HistogramBucket()
                self._histograms[name][key] = bucket
            bucket.observe(value)

    # ─── Gauge ─────────────────────────────────────────────────

    def gauge_set(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def gauge_value(self, name: str) -> float:
        with self._lock:
            return self._gauges.get(name, 0.0)

    # ─── Timer 上下文 ──────────────────────────────────────────

    @contextmanager
    def time(
        self,
        name: str,
        *,
        labels: dict[str, str] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """自动把耗时 ms 写入直方图。"""
        ctx: dict[str, Any] = {"elapsed_ms": 0.0}
        start = time.perf_counter()
        try:
            yield ctx
        finally:
            elapsed = (time.perf_counter() - start) * 1000.0
            ctx["elapsed_ms"] = elapsed
            self.histogram_observe(name, elapsed, labels=labels)
            # 同步写一个 timer.<name>.last 便于 watchdog 读
            self.gauge_set(f"timer.{name}.last_ms", elapsed)

    # ─── Snapshot ──────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        """导出所有指标为可序列化 dict（用于诊断面板 / 落盘）。"""
        with self._lock:
            counters_out: dict[str, Any] = {}
            for name, by_labels in self._counters.items():
                counters_out[name] = {
                    "value": sum(b.value for b in by_labels.values()),
                    "by_labels": {
                        _labels_to_jsonable(k): {
                            "value": b.value,
                            "first_seen": b.first_seen,
                            "last_incr": b.last_incr,
                        }
                        for k, b in by_labels.items()
                    },
                }
            histograms_out: dict[str, Any] = {}
            for name, by_labels in self._histograms.items():
                histograms_out[name] = {
                    "count": sum(b.count for b in by_labels.values()),
                    "by_labels": {
                        _labels_to_jsonable(k): {
                            "count": b.count,
                            "sum": b.sum,
                            "max": b.max,
                            "p50": b.percentile(0.50),
                            "p95": b.percentile(0.95),
                            "last": b.last_value,
                        }
                        for k, b in by_labels.items()
                    },
                }
            return {
                "counters": counters_out,
                "histograms": histograms_out,
                "gauges": dict(self._gauges),
                "generated_at": time.time(),
            }

    def snapshot_json(self) -> str:
        return json.dumps(self.snapshot(), ensure_ascii=False, indent=2)

    def reset(self) -> None:
        """清空所有指标（主要用于测试）。"""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()

    # ─── EventBus 自动绑定 ─────────────────────────────────────

    def bind_to_event_bus(
        self, bus: Any, *, prefix: str = "events"
    ) -> Callable[[], None]:
        """把所有发布事件计数到 ``{prefix}.published``.

        不会破坏现有 handler 链：仍走 bus.subscribe 注册一个旁路 handler。
        """
        if not hasattr(bus, "subscribe"):
            raise TypeError("bus must have a .subscribe() method")

        def _on_event(payload: Any) -> None:
            # 优先从 DomainEvent 取 event_name，否则用 publish() 的第一个参数
            event_name = getattr(payload, "event_name", None) or _event_name_from(
                payload
            )
            self.counter_inc(
                f"{prefix}.published",
                labels={"event": event_name} if event_name else None,
            )

        return bus.subscribe("*", _on_event, name="metrics.tap")

    # ─── 名称映射（让绑定可重命名）───────────────────────────────

    def map_event_name(self, event_name: str, metric_name: str) -> None:
        with self._lock:
            self._tag_to_name[event_name] = metric_name


def _labels_to_jsonable(
    key: tuple[tuple[str, str], ...],
) -> str:
    """``()`` → ``"__no_labels__"``；否则 ``"k1=v1,k2=v2"``."""
    if not key:
        return "__no_labels__"
    return ",".join(f"{k}={v}" for k, v in key)


def _event_name_from(payload: Any) -> str:
    """从 publish() 的隐式 dict / tuple 中恢复 event_name."""
    if isinstance(payload, dict) and "event" in payload:
        return str(payload["event"])
    if isinstance(payload, tuple) and payload:
        return str(payload[0])
    return ""


# ────────────────────────────────────────────────────────────────
#  模块级便捷 API
# ────────────────────────────────────────────────────────────────


def get_metrics() -> MetricsRegistry:
    return MetricsRegistry()


def inc(name: str, *, labels: dict[str, str] | None = None, value: float = 1.0) -> None:
    get_metrics().counter_inc(name, labels=labels, value=value)


def observe(name: str, value: float, *, labels: dict[str, str] | None = None) -> None:
    get_metrics().histogram_observe(name, value, labels=labels)


@contextmanager
def timer(name: str, *, labels: dict[str, str] | None = None) -> Iterator[dict[str, Any]]:
    with get_metrics().time(name, labels=labels) as ctx:
        yield ctx


__all__ = [
    "MetricsRegistry",
    "get_metrics",
    "inc",
    "observe",
    "timer",
]
