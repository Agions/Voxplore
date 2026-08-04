#!/usr/bin/env python3
"""E2EFeedbackLayer 端到端反馈统一抽象 (v2.5.0 端到端流程优化 · 重构方向)。

设计目标
--------
SceneFab v2.5.0 端到端流程中,用户在不同阶段会接触到多种反馈组件:
- Toast(瞬态轻通知,4s 自动关闭)
- Step Progress(进行态: 步骤状态 + ETA)
- Summary Card(完成态: 持久化展示)
- Error Recovery Banner(失败态: 重试/跳过条幅)

虽然各自实现不同,但都回答同一个问题:「当前流水线发生什么了?」
本模块通过 :class:`E2EFeedbackLayer` 协议 + :class:`CompositeFeedbackLayer`
组合器,把这些组件统一到一个接口下,让调用方(main_window)用同一种方式
表达反馈意图,具体落到哪些组件由组合策略决定。

设计契约
--------
1. **协议 (Protocol)**: 用 ``typing.Protocol`` 定义,任何满足 4 个方法的类
   都可以被识别为 feedback layer,无需继承 — 鸭子类型友好
2. **组合器**: :class:`CompositeFeedbackLayer` 顺序触发多个 layer,
   支持 ``on_success`` / ``on_error`` / ``on_progress`` / ``on_result`` 四类事件
3. **轻量**: 协议层 0 字段、0 状态,只是契约;具体组件仍是独立模块

例子
----
>>> class MyLayer:
...     def show_success(self, message, **kw): print("ok", message)
...     def show_error(self, message, **kw): print("err", message)
...     def show_progress(self, progress, **kw): print("progress", progress)
...     def show_result(self, **kw): print("done")
>>> composite = CompositeFeedbackLayer([MyLayer()])
>>> composite.show_success("Pipeline finished")
ok Pipeline finished
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class E2EFeedbackLayer(Protocol):
    """端到端反馈层协议。

    实现类只需提供 4 个方法,无需继承:
    - :meth:`show_success` —— 成功事件(如生产完成)
    - :meth:`show_error` —— 错误事件(可携带 retry / skip action)
    - :meth:`show_progress` —— 进度更新(0.0 ~ 1.0)
    - :meth:`show_result` —— 持久化成果展示(产品级,带操作入口)
    """

    def show_success(self, message: str, **kwargs: Any) -> None:
        """展示成功消息(瞬态通知,如 Toast 4s 自动关闭)。"""
        ...

    def show_error(self, message: str, **kwargs: Any) -> None:
        """展示错误消息(可携带 actions={"retry": callable, "skip": callable})。"""
        ...

    def show_progress(self, progress: float, **kwargs: Any) -> None:
        """展示进度更新(progress ∈ [0.0, 1.0])。"""
        ...

    def show_result(self, **kwargs: Any) -> None:
        """展示持久化结果(直到用户主动关闭)。"""
        ...


class CompositeFeedbackLayer:
    """组合多个 feedback layer 的容器。

    所有方法会按 layer 顺序调用。某个 layer 抛异常不会阻塞后续 layer
    (便于一个组件故障时不连累其他反馈)。
    """

    def __init__(self, layers: list[E2EFeedbackLayer]) -> None:
        self._layers: list[E2EFeedbackLayer] = list(layers)

    @property
    def layers(self) -> list[E2EFeedbackLayer]:
        return list(self._layers)

    def add(self, layer: E2EFeedbackLayer) -> None:
        """注册新 layer。"""
        self._layers.append(layer)

    def _safe_dispatch(self, method_name: str, *args: Any, **kwargs: Any) -> None:
        """安全地调用每个 layer 的同名方法,捕获并继续。"""
        for layer in self._layers:
            method = getattr(layer, method_name, None)
            if method is None:
                continue
            try:
                method(*args, **kwargs)
            except Exception:  # noqa: BLE001 - dispatcher must not crash
                # 不抛错: feedback 失败不应影响主流程
                continue

    def show_success(self, message: str, **kwargs: Any) -> None:
        self._safe_dispatch("show_success", message, **kwargs)

    def show_error(self, message: str, **kwargs: Any) -> None:
        self._safe_dispatch("show_error", message, **kwargs)

    def show_progress(self, progress: float, **kwargs: Any) -> None:
        self._safe_dispatch("show_progress", progress, **kwargs)

    def show_result(self, **kwargs: Any) -> None:
        self._safe_dispatch("show_result", **kwargs)


# ═══════════════════════════════════════════════════════════════════
# 适配器:把现有组件适配到协议
# ═══════════════════════════════════════════════════════════════════


class ToastLayer:
    """把现有 :class:`ToastManager` 适配到 :class:`E2EFeedbackLayer`。

    show_success/error 映射到 ``info/success/error``;
    show_progress / show_result 是 no-op(Toast 不适合承载持续反馈)。
    """

    def __init__(self, manager: Any) -> None:
        self._manager = manager

    def show_success(self, message: str, **kwargs: Any) -> None:
        title = kwargs.get("title", "")
        if title:
            self._manager.success(title=title, message=message)
        else:
            self._manager.info(message=message)

    def show_error(self, message: str, **kwargs: Any) -> None:
        title = kwargs.get("title", "")
        actions = kwargs.get("actions")
        if title:
            self._manager.error(
                title=title, message=message, actions=actions or None
            )
        else:
            self._manager.error(message=message, actions=actions or None)

    def show_progress(self, progress: float, **kwargs: Any) -> None:  # noqa: ARG002
        # Toast 不适合承载进度,显式 no-op
        return None

    def show_result(self, **kwargs: Any) -> None:  # noqa: ARG002
        return None


class SummaryCardLayer:
    """把现有 :class:`ProductionSummaryCard` 适配到 :class:`E2EFeedbackLayer`。

    show_result 映射到 ``show_result``;其他方法是 no-op
    (Summary 是完成态展示,不适合瞬态反馈)。
    """

    def __init__(self, card: Any) -> None:
        self._card = card

    def show_success(self, message: str, **kwargs: Any) -> None:  # noqa: ARG002
        return None

    def show_error(self, message: str, **kwargs: Any) -> None:  # noqa: ARG002
        return None

    def show_progress(self, progress: float, **kwargs: Any) -> None:  # noqa: ARG002
        return None

    def show_result(self, **kwargs: Any) -> None:
        # ProductionSummaryCard.show_result 接受 (project_path, elapsed_seconds, file_size_bytes, steps_completed, steps_total)
        self._card.show_result(**kwargs)


# ═══════════════════════════════════════════════════════════════════
# 工厂
# ═══════════════════════════════════════════════════════════════════


def build_default_composite() -> CompositeFeedbackLayer:
    """构造项目默认的 :class:`CompositeFeedbackLayer`。

    留作占位 — 实际装配由 main_window 在持有 ToastManager 与 SummaryCard
    实例后调用,这里只做契约占位。
    """
    return CompositeFeedbackLayer([])


__all__ = [
    "CompositeFeedbackLayer",
    "E2EFeedbackLayer",
    "SummaryCardLayer",
    "ToastLayer",
    "build_default_composite",
]
