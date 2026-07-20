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

import os
import tempfile
import time

import pytest

from scenefab.core.event_types import (
    PipelineCompleted,
    PipelineStarted,
    PipelineStepCompleted,
    TaskCreated,
    TaskStatusChanged,
)
from scenefab.core.unified_event_bus import (
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
        self.bus.publish_event(
            PipelineStepCompleted(
                pipeline_id="p1", step_id="a", status="success", duration_ms=10
            )
        )
        time.sleep(0.05)
        log = self.bus.log()
        assert log is not None
        assert len(log) == 2
        assert log.all()[0].event_name == "pipeline.started"

    def test_replay_all(self):
        received = []
        self.bus.subscribe("pipeline.completed", lambda e: received.append(e))
        self.bus.publish_event(
            PipelineCompleted(
                pipeline_id="p1",
                total_duration_ms=100,
                success_count=1,
                failure_count=0,
            )
        )
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
        self.bus.publish_event(
            TaskStatusChanged(task_id="t1", old_status="running", new_status="running")
        )
        self.bus.publish_event(
            TaskStatusChanged(
                task_id="t1", old_status="running", new_status="completed"
            )
        )
        time.sleep(0.05)
        assert len(received) == 1
        assert received[0].new_status == "completed"


# ══════════════════════════════════════════════════════════
# Phase 1b: v1.x 兼容性
# ══════════════════════════════════════════════════════════


class TestV1XCompatibility:
    """v1.x EventBus API 兼容性（直接使用 UnifiedEventBus）"""

    def test_unified_eventbus_subscribe_publish(self):
        """UnifiedEventBus 支持字符串事件的 subscribe/publish"""
        bus = UnifiedEventBus.get_default()
        received = []
        bus.subscribe("v1x.test", lambda d: received.append(d))
        bus.publish("v1x.test", {"y": 1})
        time.sleep(0.05)
        assert received == [{"y": 1}]
        bus.clear_handlers("v1x.test")

    def test_v1x_publish_subscribe(self):
        """get_event_bus() 返回的实例支持字符串事件"""
        bus = get_event_bus()
        received = []
        bus.clear_handlers()
        bus.subscribe("v1x.test", lambda d: received.append(d))
        bus.publish("v1x.test", {"y": 1})
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
        t = UnifiedTask(on_event=lambda e: received.append(e))
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


