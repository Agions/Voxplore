#!/usr/bin/env python3
"""E2EFeedbackLayer 协议 + CompositeFeedbackLayer 单元测试（v2.5.0 重构方向）。

覆盖：
- 协议 runtime_checkable
- CompositeFeedbackLayer 顺序触发
- 异常隔离：单个 layer 抛错不影响其他 layer
- 适配器：ToastLayer / SummaryCardLayer 的方法映射
- 工厂：build_default_composite 返回空 CompositeFeedbackLayer
"""
from __future__ import annotations

import os

import pytest

from app.ui.main.widgets.e2e_feedback import (
    CompositeFeedbackLayer,
    E2EFeedbackLayer,
    SummaryCardLayer,
    ToastLayer,
    build_default_composite,
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PySide6 = pytest.importorskip("PySide6")


class _StubLayer:
    """可记录调用顺序的轻量 feedback layer。"""

    def __init__(self, *, raise_on: str | None = None) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self._raise_on = raise_on

    def show_success(self, message: str, **kw) -> None:
        self.calls.append(("show_success", (message,), kw))
        if self._raise_on == "show_success":
            raise RuntimeError("stub failure")

    def show_error(self, message: str, **kw) -> None:
        self.calls.append(("show_error", (message,), kw))
        if self._raise_on == "show_error":
            raise RuntimeError("stub failure")

    def show_progress(self, progress: float, **kw) -> None:
        self.calls.append(("show_progress", (progress,), kw))
        if self._raise_on == "show_progress":
            raise RuntimeError("stub failure")

    def show_result(self, **kw) -> None:
        self.calls.append(("show_result", (), kw))
        if self._raise_on == "show_result":
            raise RuntimeError("stub failure")


class TestProtocol:
    def test_isinstance_checkable(self) -> None:
        """运行时可检测一个对象是否实现 E2EFeedbackLayer。"""
        stub = _StubLayer()
        assert isinstance(stub, E2EFeedbackLayer)

    def test_partial_layer_not_satisfy_protocol(self) -> None:
        """缺少方法的对象不应通过 isinstance 检查。"""

        class _Partial:
            def show_success(self, message: str) -> None:
                pass

        assert not isinstance(_Partial(), E2EFeedbackLayer)


class TestCompositeDispatch:
    def test_dispatches_to_all_layers_in_order(self) -> None:
        a = _StubLayer()
        b = _StubLayer()
        c = CompositeFeedbackLayer([a, b])

        c.show_success("ok")

        assert len(a.calls) == 1
        assert len(b.calls) == 1
        assert a.calls[0] == ("show_success", ("ok",), {})
        assert b.calls[0] == ("show_success", ("ok",), {})

    def test_dispatches_all_four_methods(self) -> None:
        a = _StubLayer()
        c = CompositeFeedbackLayer([a])

        c.show_success("ok")
        c.show_error("err")
        c.show_progress(0.5)
        c.show_result(steps=5)

        method_names = [call[0] for call in a.calls]
        assert method_names == [
            "show_success",
            "show_error",
            "show_progress",
            "show_result",
        ]

    def test_kwargs_passed_through(self) -> None:
        a = _StubLayer()
        c = CompositeFeedbackLayer([a])

        c.show_success("ok", title="Done", action="open")
        assert a.calls[0] == ("show_success", ("ok",), {
                              "title": "Done", "action": "open"})

    def test_layer_exception_does_not_propagate(self) -> None:
        """单个 layer 抛异常应被吞掉,后续 layer 仍执行。"""
        bad = _StubLayer(raise_on="show_success")
        good = _StubLayer()
        c = CompositeFeedbackLayer([bad, good])

        # 不应抛 RuntimeError
        c.show_success("ok")

        assert bad.calls  # 被调用过
        assert good.calls  # 后续 layer 仍被调用

    def test_empty_composite_safe(self) -> None:
        c = CompositeFeedbackLayer([])
        # 不应抛错
        c.show_success("ok")
        c.show_error("err")
        c.show_progress(0.5)
        c.show_result()

    def test_add_layer(self) -> None:
        a = _StubLayer()
        c = CompositeFeedbackLayer([a])
        b = _StubLayer()

        c.add(b)
        c.show_success("ok")

        assert len(a.calls) == 1
        assert len(b.calls) == 1

    def test_layers_property_returns_copy(self) -> None:
        a = _StubLayer()
        c = CompositeFeedbackLayer([a])
        snapshot = c.layers
        snapshot.append(_StubLayer())  # type: ignore[arg-type]
        # 不影响原 list
        assert len(c.layers) == 1


class TestToastAdapter:
    def test_toast_layer_show_success_routes_to_info(self) -> None:
        class _FakeManager:
            def __init__(self) -> None:
                self.calls: list[tuple] = []

            def info(self, message: str) -> None:
                self.calls.append(("info", message))

            def success(self, *, title: str, message: str) -> None:
                self.calls.append(("success", title, message))

        mgr = _FakeManager()
        layer = ToastLayer(mgr)

        layer.show_success("just message")
        assert mgr.calls == [("info", "just message")]

        layer.show_success("with title", title="Done")
        assert mgr.calls == [("info", "just message"),
                             ("success", "Done", "with title")]

    def test_toast_layer_show_progress_is_noop(self) -> None:
        class _FakeManager:
            pass

        mgr = _FakeManager()
        layer = ToastLayer(mgr)
        # 不抛错
        layer.show_progress(0.5)
        layer.show_result()


class TestSummaryAdapter:
    def test_summary_layer_routes_to_card(self) -> None:
        class _FakeCard:
            def __init__(self) -> None:
                self.received: dict | None = None

            def show_result(self, **kw) -> None:
                self.received = kw

        card = _FakeCard()
        layer = SummaryCardLayer(card)

        layer.show_result(project_path="/a.mp4", elapsed_seconds=10.0)
        assert card.received == {
            "project_path": "/a.mp4", "elapsed_seconds": 10.0}

    def test_summary_other_methods_are_noop(self) -> None:
        class _FakeCard:
            def show_result(self, **kw) -> None:
                pass

        card = _FakeCard()
        layer = SummaryCardLayer(card)
        # 不抛错
        layer.show_success("ok")
        layer.show_error("err")
        layer.show_progress(0.5)


class TestFactory:
    def test_build_default_composite_empty(self) -> None:
        c = build_default_composite()
        assert isinstance(c, CompositeFeedbackLayer)
        assert c.layers == []
