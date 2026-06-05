"""
SceneFab v2.1 架构升级测试套件

覆盖：
- Phase 1: UnifiedEventBus 单源真相 + 类型化事件 + 重放
- Phase 2: UnifiedTask 状态机 + TaskManager 桥接
- Phase 3: DIContainer 作用域 + 钩子
- Phase 4: TaskStore 3 后端
- Phase 5: SettingsV2 加载
- Phase 6: EventStore 持久化
- Phase 7: WSHub 推送
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import threading
import time
from typing import Any

import pytest

from scenefab.core.event_types import (
    DomainEvent,
    FFmpegExecuted,
    LLMTokenGenerated,
    PipelineCompleted,
    PipelineStarted,
    PipelineStepCompleted,
    TaskCreated,
    TaskProgressUpdated,
    TaskStatusChanged,
)
from scenefab.core.unified_event_bus import (
    EventLog,
    UnifiedEventBus,
    get_event_bus,
    set_event_bus,
)

# ══════════════════════════════════════════════════════════
# Phase 1: UnifiedEventBus
# ══════════════════════════════════════════════════════════


class TestUnifiedEventBus:
    """UnifiedEventBus 单源真相 + 类型化事件"""

    def setup_method(self):
        self.bus = UnifiedEventBus(enable_log=True, log_size=100)
        set_event_bus(self.bus)

    def test_singleton_via_get_default(self):
        b1 = UnifiedEventBus.get_default()
        b2 = UnifiedEventBus.get_default()
        assert b1 is b2

    def test_string_event_basic(self):
        received = []
        self.bus.subscribe("video.analyzed", lambda d: received.append(d))
        self.bus.publish("video.analyzed", {"frames": 5})
        time.sleep(0.05)
        assert received == [{"frames": 5}]

    def test_typed_event(self):
        received = []
        self.bus.subscribe("pipeline.started", lambda e: received.append(e))
        self.bus.publish_event(PipelineStarted(pipeline_id="p1", total_steps=3))
        time.sleep(0.05)
        assert len(received) == 1
        assert received[0].pipeline_id == "p1"
        assert received[0].total_steps == 3

    def test_wildcard_handler(self):
        received = []
        self.bus.subscribe("*", lambda d: received.append(d))
        self.bus.publish("a", 1)
        self.bus.publish_event(TaskCreated(task_id="t1", task_name="x"))
        time.sleep(0.05)
        assert len(received) == 2

    def test_event_log_captures_typed_events(self):
        self.bus.publish_event(PipelineStarted(pipeline_id="p1", total_steps=1))
        self.bus.publish_event(PipelineStepCompleted(pipeline_id="p1", step_id="a", status="success", duration_ms=10))
        time.sleep(0.05)
        log = self.bus.log()
        assert log is not None
        assert len(log) == 2
        assert log.all()[0].event_name == "pipeline.started"

    def test_replay_all(self):
        received = []
        self.bus.subscribe("pipeline.completed", lambda e: received.append(e))
        self.bus.publish_event(PipelineCompleted(pipeline_id="p1", total_duration_ms=100, success_count=1, failure_count=0))
        time.sleep(0.05)
        received.clear()  # 清空初始触发的
        replayed = self.bus.replay_all()
        time.sleep(0.05)
        assert replayed == 1
        assert len(received) == 1

    def test_handler_exception_isolated(self):
        def bad_handler(d):
            raise RuntimeError("boom")

        received = []
        self.bus.subscribe("test.event", bad_handler)
        self.bus.subscribe("test.event", lambda d: received.append(d))
        self.bus.publish("test.event", {"x": 1})
        time.sleep(0.05)
        # 第二个 handler 应该仍然收到
        assert received == [{"x": 1}]

    def test_unsubscribe_returns_unsubscribe_fn(self):
        received = []
        unsub = self.bus.subscribe("x", lambda d: received.append(d))
        self.bus.publish("x", 1)
        time.sleep(0.05)
        assert len(received) == 1
        unsub()
        self.bus.publish("x", 2)
        time.sleep(0.05)
        assert len(received) == 1  # 仍然只有 1 个

    def test_stats(self):
        self.bus.subscribe("a", lambda d: None)
        self.bus.publish("a", 1)
        self.bus.publish("a", 2)
        time.sleep(0.05)
        stats = self.bus.stats()
        assert stats["published_count"] == 2
        assert stats["handler_invocations"] == 2

    def test_handler_with_filter(self):
        received = []
        self.bus.subscribe(
            "task.status.changed",
            lambda e: received.append(e),
            filter_fn=lambda e: e.new_status == "completed",
        )
        self.bus.publish_event(TaskStatusChanged(task_id="t1", old_status="running", new_status="running"))
        self.bus.publish_event(TaskStatusChanged(task_id="t1", old_status="running", new_status="completed"))
        time.sleep(0.05)
        assert len(received) == 1
        assert received[0].new_status == "completed"


# ══════════════════════════════════════════════════════════
# Phase 1b: v1.x 兼容性
# ══════════════════════════════════════════════════════════


class TestV1XCompatibility:
    """v1.x EventBus API 完全兼容"""

    def test_core_eventbus_delegates(self):
        from scenefab.core import EventBus as CoreEventBus
        b = CoreEventBus()
        # 委托到 UnifiedEventBus 默认实例
        assert b._backend is UnifiedEventBus.get_default()

    def test_event_bus_module_delegates(self):
        from scenefab.event_bus import EventBus as CompatEventBus
        b = CompatEventBus()
        assert b._backend is UnifiedEventBus.get_default()

    def test_v1x_publish_subscribe(self):
        from scenefab.event_bus import event_bus as compat_event_bus
        received = []
        compat_event_bus.clear_handlers()
        compat_event_bus.subscribe("v1x.test", lambda d: received.append(d))
        from scenefab.core.unified_event_bus import get_event_bus
        get_event_bus().publish("v1x.test", {"y": 1})
        time.sleep(0.05)
        assert received == [{"y": 1}]


# ══════════════════════════════════════════════════════════
# Phase 2: UnifiedTask 状态机
# ══════════════════════════════════════════════════════════


class TestUnifiedTask:
    """UnifiedTask 状态机 + 合法性"""

    def test_initial_state_pending(self):
        from scenefab.core.task_model import UnifiedTask
        t = UnifiedTask()
        assert t.status.value == "pending"
        assert t.progress == 0.0

    def test_legal_transitions(self):
        from scenefab.core.task_model import TaskStatus, UnifiedTask
        t = UnifiedTask()
        t.mark_running()
        assert t.status == TaskStatus.RUNNING
        t.mark_paused()
        assert t.status == TaskStatus.PAUSED
        t.mark_running()
        t.mark_completed(result="ok")
        assert t.status == TaskStatus.COMPLETED
        assert t.result == "ok"
        assert t.progress == 1.0

    def test_illegal_transition_raises(self):
        from scenefab.core.task_model import (
            IllegalTransitionError,
            TaskStatus,
            UnifiedTask,
        )
        t = UnifiedTask()
        # pending → completed 不合法（必须先经过 running）
        with pytest.raises(IllegalTransitionError):
            t._transition_to(TaskStatus.COMPLETED)

    def test_terminal_states_block_further_transitions(self):
        from scenefab.core.task_model import (
            IllegalTransitionError,
            TaskStatus,
            UnifiedTask,
        )
        t = UnifiedTask()
        t.mark_running()
        t.mark_failed("oops")
        with pytest.raises(IllegalTransitionError):
            t.mark_completed()  # 终态不能再转

    def test_update_progress_emits_event(self):
        from scenefab.core.task_model import UnifiedTask
        received = []
        t = UnifiedTask(
            on_event=lambda e: received.append(e)
        )
        t.update_progress(0.5, current_step_name="analyzing")
        assert len(received) == 1
        assert received[0].progress == 0.5
        assert received[0].current_step == "analyzing"

    def test_cancel_token(self):
        from scenefab.core.task_model import CancelToken
        token = CancelToken()
        assert not token.cancelled
        token.cancel("user")
        assert token.cancelled
        assert token.reason == "user"


# ══════════════════════════════════════════════════════════
# Phase 3: DIContainer
# ══════════════════════════════════════════════════════════


class TestDIContainer:
    """DI 容器 v2.1"""

    def test_v1x_singleton(self):
        from scenefab.core.di_container import DIContainer
        c = DIContainer()
        class Svc:
            pass
        instance = Svc()
        c.register(Svc, instance)
        assert c.get(Svc) is instance

    def test_transient_creates_new(self):
        from scenefab.core.di_container import DIContainer
        c = DIContainer()
        class Svc:
            pass
        c.register_transient("svc", Svc)
        a = c.get_by_name("svc")
        b = c.get_by_name("svc")
        assert a is not b

    def test_scoped_creates_per_scope(self):
        from scenefab.core.di_container import DIContainer
        c = DIContainer()
        class Svc:
            pass
        c.register_scoped(Svc, Svc)
        with c.enter_scope():
            a = c.get(Svc)
            b = c.get(Svc)
            assert a is b
        with c.enter_scope():
            c2 = c.get(Svc)
            assert c2 is not a

    def test_resolve_hook(self):
        from scenefab.core.di_container import DIContainer
        c = DIContainer()
        seen = []
        c.on_resolve(lambda name, inst: seen.append(name))
        c.register_singleton("logger", object())
        c.get_by_name("logger")
        assert "logger" in seen

    def test_app_container_has_event_bus(self):
        from scenefab.core.di_container import get_app_container
        c = get_app_container()
        assert c.has_by_name("event_bus")


# ══════════════════════════════════════════════════════════
# Phase 4: TaskStore
# ══════════════════════════════════════════════════════════


class TestTaskStore:
    """TaskStore 3 后端"""

    def test_inmemory_basic(self):
        from scenefab.core.task_store import InMemoryTaskStore
        s = InMemoryTaskStore()
        s.save("t1", {"status": "running"})
        assert s.get("t1") == {"status": "running"}
        assert s.exists("t1")
        s.delete("t1")
        assert not s.exists("t1")

    def test_inmemory_ttl(self):
        from scenefab.core.task_store import InMemoryTaskStore
        s = InMemoryTaskStore()
        s.save("t1", {"x": 1})
        s.set_ttl("t1", 0)  # 立即过期
        time.sleep(0.01)
        assert s.get("t1") is None

    def test_sqlite_persists_across_instances(self):
        from scenefab.core.task_store import SQLiteTaskStore
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            s1 = SQLiteTaskStore(path)
            s1.save("t1", {"status": "completed"})
            s2 = SQLiteTaskStore(path)  # 重新打开
            assert s2.get("t1") == {"status": "completed"}
        finally:
            os.unlink(path)

    def test_factory(self):
        from scenefab.core.task_store import create_task_store
        mem = create_task_store("memory")
        assert mem.__class__.__name__ == "InMemoryTaskStore"
        sq = create_task_store("sqlite", db_path=":memory:")
        assert sq.__class__.__name__ == "SQLiteTaskStore"

    def test_update_partial(self):
        from scenefab.core.task_store import InMemoryTaskStore
        s = InMemoryTaskStore()
        s.save("t1", {"a": 1, "b": 2})
        s.update("t1", b=99, c=3)
        assert s.get("t1") == {"a": 1, "b": 99, "c": 3}


# ══════════════════════════════════════════════════════════
# Phase 5: SettingsV2
# ══════════════════════════════════════════════════════════


class TestSettingsV2:
    """配置层 v2.1（pydantic-settings）"""

    def test_available(self):
        from scenefab.core.config_v2 import is_settings_v2_available
        assert is_settings_v2_available()

    def test_get_settings(self):
        from scenefab.core.config_v2 import get_settings
        s = get_settings()
        assert s.app_name == "scenefab"
        assert s.profile.value == "development"

    def test_json_schema(self):
        from scenefab.core.config_v2 import get_settings
        s = get_settings()
        schema = s.to_json_schema()
        assert "properties" in schema
        assert "pipeline" in schema["properties"]

    def test_to_dict(self):
        from scenefab.core.config_v2 import get_settings
        s = get_settings()
        d = s.to_dict()
        assert "llm" in d
        assert "pipeline" in d
        assert "storage" in d


# ══════════════════════════════════════════════════════════
# Phase 6: EventStore
# ══════════════════════════════════════════════════════════


class TestEventStore:
    """EventStore 持久化"""

    def test_inmemory_basic(self):
        from scenefab.core.event_store import InMemoryEventStore
        s = InMemoryEventStore()
        s.append("e1", {"a": 1})
        s.append("e2", {"b": 2})
        assert s.count() == 2

    def test_query_by_name(self):
        from scenefab.core.event_store import InMemoryEventStore
        s = InMemoryEventStore()
        s.append("pipeline.started", {"x": 1})
        s.append("task.created", {"y": 2})
        s.append("pipeline.started", {"x": 3})
        results = s.query(event_name="pipeline.started")
        assert len(results) == 2

    def test_query_by_correlation(self):
        from scenefab.core.event_store import InMemoryEventStore
        s = InMemoryEventStore()
        s.append("a", 1, correlation_id="c1")
        s.append("b", 2, correlation_id="c1")
        s.append("a", 3, correlation_id="c2")
        chain = s.chain("c1")
        assert len(chain) == 2

    def test_sqlite_persists(self):
        from scenefab.core.event_store import SQLiteEventStore
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            s1 = SQLiteEventStore(path)
            s1.append("test.event", {"x": 1})
            s2 = SQLiteEventStore(path)
            assert s2.count() == 1
        finally:
            os.unlink(path)

    def test_install_event_store_into_bus(self):
        from scenefab.core.event_store import (
            InMemoryEventStore,
            install_event_store_into_bus,
        )
        from scenefab.core.event_types import TaskCreated
        from scenefab.core.unified_event_bus import UnifiedEventBus
        bus = UnifiedEventBus()
        store = InMemoryEventStore()
        install_event_store_into_bus(bus, store)
        bus.publish_event(TaskCreated(task_id="t1", task_name="x"))
        time.sleep(0.1)
        assert store.count() >= 1


# ══════════════════════════════════════════════════════════
# Phase 7: WSHub
# ══════════════════════════════════════════════════════════


class TestWSHub:
    """WebSocket Hub"""

    def test_connect_disconnect(self):
        from starlette.websockets import WebSocketState

        from scenefab.core.ws_hub import WSHub

        class MockWS:
            client_state = WebSocketState.CONNECTED
            async def send_json(self, msg): pass
            async def close(self): pass

        async def main():
            hub = WSHub()
            ws = MockWS()
            await hub.connect(ws, client_id="c1")
            assert hub.count() == 1
            await hub.disconnect(ws)
            assert hub.count() == 0
            await hub.stop()
        asyncio.run(main())

    def test_event_filtering(self):
        from starlette.websockets import WebSocketState

        from scenefab.core.event_types import PipelineStarted, TaskCreated
        from scenefab.core.unified_event_bus import UnifiedEventBus, set_event_bus
        from scenefab.core.ws_hub import WSHub

        class MockWS:
            client_state = WebSocketState.CONNECTED
            def __init__(self):
                self.received = []
            async def send_json(self, msg): self.received.append(msg)
            async def close(self): pass

        async def main():
            bus = UnifiedEventBus()
            set_event_bus(bus)
            bus.clear_log()
            bus.clear_handlers()
            hub = WSHub(name="test")
            await hub.start()
            ws = MockWS()
            await hub.connect(ws, client_id="c1", event_names=["task.created"])
            bus.publish_event(TaskCreated(task_id="t1", task_name="x"))
            bus.publish_event(PipelineStarted(pipeline_id="p1", total_steps=1))
            await asyncio.sleep(0.3)
            # 收到：connected + task.created = 2 条（pipeline.started 被过滤）
            assert len(ws.received) == 2
            await hub.stop()
        asyncio.run(main())

    def test_wildcard_subscription(self):
        from starlette.websockets import WebSocketState

        from scenefab.core.event_types import PipelineStarted, TaskCreated
        from scenefab.core.unified_event_bus import UnifiedEventBus, set_event_bus
        from scenefab.core.ws_hub import WSHub

        class MockWS:
            client_state = WebSocketState.CONNECTED
            def __init__(self):
                self.received = []
            async def send_json(self, msg): self.received.append(msg)
            async def close(self): pass

        async def main():
            bus = UnifiedEventBus()
            set_event_bus(bus)
            bus.clear_log()
            bus.clear_handlers()
            hub = WSHub()
            await hub.start()
            ws = MockWS()
            await hub.connect(ws, client_id="c1", event_names=[])  # 所有
            bus.publish_event(TaskCreated(task_id="t1", task_name="x"))
            bus.publish_event(PipelineStarted(pipeline_id="p1", total_steps=1))
            await asyncio.sleep(0.3)
            # connected + 2 events = 3
            assert len(ws.received) == 3
            await hub.stop()
        asyncio.run(main())


# ══════════════════════════════════════════════════════════
# 集成测试：v2.0 PipelineEngine + v2.1 事件总线
# ══════════════════════════════════════════════════════════


class TestPipelineEngineV21Integration:
    """v2.0 PipelineEngine 通过 v2.1 事件总线发布事件"""

    def test_pipeline_publishes_events(self):
        from scenefab.core.pipeline_engine import PipelineEngine, PipelineStep
        from scenefab.core.unified_event_bus import UnifiedEventBus

        bus = UnifiedEventBus()
        bus.clear_log()
        bus.clear_handlers()
        from scenefab.core.unified_event_bus import set_event_bus
        set_event_bus(bus)

        engine = PipelineEngine(event_bus=bus, pipeline_id="integration-test")
        engine.add_step(PipelineStep(id="a", func=lambda c: 1))
        engine.add_step(PipelineStep(id="b", func=lambda c: 2, dependencies=["a"]))
        engine.run({})

        log = bus.log()
        assert log is not None
        events = [r.event_name for r in log.all()]
        assert "pipeline.started" in events
        assert events.count("pipeline.step.completed") == 2
        assert "pipeline.completed" in events


# ══════════════════════════════════════════════════════════
# 集成测试：TaskManager 发布 v2.1 事件
# ══════════════════════════════════════════════════════════


class TestTaskManagerV21Integration:
    """v1.x TaskManager 桥接到 v2.1 事件总线"""

    def test_create_task_publishes_event(self):
        from scenefab.core.event_types import TaskCreated
        from scenefab.core.unified_event_bus import UnifiedEventBus, set_event_bus
        bus = UnifiedEventBus()
        bus.clear_log()
        bus.clear_handlers()
        set_event_bus(bus)

        from scenefab.task_manager import task_manager
        # task_manager 是 singleton；用 create_task 看是否走事件总线
        # 注意：可能受其他测试污染，只校验事件被发出去
        received = []
        bus.subscribe("task.created", lambda e: received.append(e))

        task_id = task_manager.create_task("v21-test", steps=["a", "b"])
        time.sleep(0.1)
        # task_id 是 random；至少有一个 task.created
        assert len(received) >= 1
        # 清理
        task_manager.remove(task_id)
