"""Tests for the lightweight in-process metrics registry (Phase 4-1).

覆盖：
  * counter_inc / counter_value（多 label 维度）
  * histogram_observe 的 p50 / p95 / max 聚合
  * gauge_set / gauge_value
  * timer context manager 自动 observe
  * snapshot() 导出可序列化的 dict
  * bind_to_event_bus() 自动把发布事件计入 ``events.<name>`` counter
  * 并发线程安全
"""

from __future__ import annotations

import threading

import pytest

from app.core.metrics import (
    MetricsRegistry,
    get_metrics,
    inc,
    observe,
)


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    """每个用例都拿全新单例，避免互相污染。"""
    MetricsRegistry._instance = None


class TestCounter:
    def test_increment_default(self):
        m = MetricsRegistry()
        m.counter_inc("requests")
        m.counter_inc("requests")
        assert m.counter_value("requests") == 2.0

    def test_increment_with_labels(self):
        m = MetricsRegistry()
        m.counter_inc("requests", labels={"path": "/home", "method": "GET"})
        m.counter_inc("requests", labels={"path": "/home", "method": "GET"})
        m.counter_inc("requests", labels={"path": "/assets", "method": "POST"})
        assert m.counter_value("requests", labels={
                               "path": "/home", "method": "GET"}) == 2.0
        assert m.counter_value("requests", labels={
                               "path": "/assets", "method": "POST"}) == 1.0
        # 未声明的 label 组合视作 0
        assert m.counter_value("requests", labels={"path": "/x"}) == 0.0

    def test_negative_value_rejected(self):
        m = MetricsRegistry()
        with pytest.raises(ValueError):
            m.counter_inc("requests", value=-1.0)

    def test_value_kwarg(self):
        m = MetricsRegistry()
        m.counter_inc("bytes", value=128)
        m.counter_inc("bytes", value=256)
        assert m.counter_value("bytes") == 384.0


class TestHistogram:
    def test_observe_and_quantiles(self):
        m = MetricsRegistry()
        for v in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            m.histogram_observe("latency", v)
        snap = m.snapshot()
        h = snap["histograms"]["latency"]["by_labels"]["__no_labels__"]
        assert h["count"] == 10
        assert h["max"] == 100.0
        # 排序后 median(50% 位置) 应为 ~55
        assert 50.0 <= h["p50"] <= 60.0
        # p95 应为 95
        assert 90.0 <= h["p95"] <= 100.0

    def test_negative_value_rejected(self):
        m = MetricsRegistry()
        with pytest.raises(ValueError):
            m.histogram_observe("latency", -1.0)

    def test_with_labels(self):
        m = MetricsRegistry()
        m.histogram_observe("latency", 50, labels={"op": "read"})
        m.histogram_observe("latency", 100, labels={"op": "read"})
        snap = m.snapshot()
        read = snap["histograms"]["latency"]["by_labels"]["op=read"]
        assert read["count"] == 2
        assert read["max"] == 100.0


class TestGauge:
    def test_set_and_read(self):
        m = MetricsRegistry()
        m.gauge_set("queue.depth", 12)
        m.gauge_set("queue.depth", 7)
        assert m.gauge_value("queue.depth") == 7.0

    def test_default_zero(self):
        m = MetricsRegistry()
        assert m.gauge_value("never.set") == 0.0


class TestTimerContext:
    def test_timer_records_duration(self):
        m = MetricsRegistry()
        with m.time("op.duration"):
            total = 0
            for i in range(1000):
                total += i
            assert total == 499500
        snap = m.snapshot()
        h = snap["histograms"]["op.duration"]["by_labels"]["__no_labels__"]
        assert h["count"] == 1
        # 1000 次加法远小于 0.1s，但应该 >= 0
        assert h["max"] >= 0.0
        # gauge 应被最后一次 timer 写入
        assert m.gauge_value("timer.op.duration.last_ms") >= 0.0


class TestSnapshot:
    def test_returns_serializable_dict(self):
        m = MetricsRegistry()
        m.counter_inc("c", labels={"k": "v"})
        m.histogram_observe("h", 1.0)
        m.gauge_set("g", 9.0)
        snap = m.snapshot()
        assert "generated_at" in snap
        assert "counters" in snap and "histograms" in snap and "gauges" in snap
        assert "c" in snap["counters"]
        assert "h" in snap["histograms"]
        assert snap["gauges"]["g"] == 9.0

    def test_singleton(self):
        a = get_metrics()
        b = get_metrics()
        assert a is b


class TestEventBusBinding:
    def test_bind_counts_published_events(self):
        from app.core.event_types import PipelineStarted
        from app.core.unified_event_bus import UnifiedEventBus

        m = MetricsRegistry()
        bus = UnifiedEventBus()
        m.bind_to_event_bus(bus, prefix="events")

        # DomainEvent 携带 event_name → 按 event label 区分
        bus.publish_event(PipelineStarted(pipeline_id="p1"))
        bus.publish_event(PipelineStarted(pipeline_id="p2"))
        # 普通 publish：payload dict 带 "event" 键时可恢复名称
        bus.publish("other.event", {"event": "other.event"})
        # 无法恢复名称的 payload → 计入无 label 桶
        bus.publish("anonymous.event", {"x": 1})

        # bind_to_event_bus 全部累计到 events.published、按 event label 区分
        assert (
            m.counter_value(
                "events.published", labels={"event": "pipeline.started"})
            == 2.0
        )
        assert (
            m.counter_value("events.published", labels={
                            "event": "other.event"})
            == 1.0
        )
        assert m.counter_value("events.published") == 1.0

    def test_module_level_helpers(self):
        inc("global.requests")
        inc("global.requests", value=4.0)
        assert get_metrics().counter_value("global.requests") == 5.0
        observe("global.size", 42)
        snap = get_metrics().snapshot()
        assert snap["histograms"]["global.size"]["by_labels"]["__no_labels__"]["count"] == 1


class TestConcurrency:
    def test_counter_thread_safe(self):
        m = MetricsRegistry()
        N = 1000

        def worker() -> None:
            for _ in range(N):
                m.counter_inc("concurrent")

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        assert m.counter_value("concurrent") == 4 * N
