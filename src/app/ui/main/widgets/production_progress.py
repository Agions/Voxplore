#!/usr/bin/env python3
"""ProgressETA — 5 步流水线 ETA 估算器 (v2.5.0 端到端流程优化 Phase 3)。

设计目标：
- 纯逻辑、无 Qt 依赖、可独立单元测试
- 滑动窗口平均：用最近 N 个已完成步骤的实际耗时推断剩余耗时
- 渐进式：第 1 步未完成时无数据 → 返回 None(UI 显示"进行中…",不显示 ETA)
- 防漂移：超时步(> 60s)自动裁剪，避免历史长任务污染新预测

调用契约：
1. ``record_step(seconds)`` 在每步完成时记录耗时
2. ``estimate_remaining(completed)`` 计算当前已完成步骤后的剩余时间
3. ``format_seconds(n)`` helper 把秒数渲染为"5s"/"1m20s"/"2m"，与现有 _humanize_duration 风格一致
"""

from __future__ import annotations

# 历史步耗时上限（秒）：超过则裁剪到本值，避免单步卡死污染后续 ETA
_STEP_DURATION_CAP_SECONDS: float = 60.0


def cap_step_duration(seconds: float) -> float:
    """裁剪极端耗时，保持 ETA 估算稳定。

    一旦某步意外卡死 10 分钟，后续窗口平均仍会被拉偏。
    简单做法：把超过上限的耗时降到上限，避免污染预测。
    """
    if seconds < 0:
        return 0.0
    if seconds > _STEP_DURATION_CAP_SECONDS:
        return _STEP_DURATION_CAP_SECONDS
    return seconds


def format_seconds(seconds: float) -> str:
    """把秒数格式化为人类可读字符串。

    - < 60s : "5.0s"
    - < 3600s : "1m20.0s"
    - >= 3600s : "60m" 简化（5 步流水线总耗时一般不会到 1 小时）

    与 ``ProductionSummaryCard._humanize_duration`` 风格保持一致，
    避免 UI 上出现两种时间格式风格。
    """
    if seconds < 0:
        return "0.0s"
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        rest = seconds - minutes * 60
        return f"{minutes}m{rest:04.1f}s"
    minutes = int(seconds // 60)
    return f"{minutes}m"


class ProgressETA:
    """5 步流水线 ETA 估算器。

    Parameters
    ----------
    total_steps:
        流水线总步数（当前固定 5）。
    window:
        滑动窗口大小。窗口越小，越跟随最新节奏；窗口越大，越平滑但滞后。
        默认 3（5 步流水线中取最近 3 步作为基线，剩余 2 步按平均外推）。

    Notes
    -----
    - 算法：avg(window[-window:]) × remaining_steps
    - 无数据（尚未完成任何一步）→ ``estimate_remaining`` 返回 None
    - 全部完成（completed == total）→ 返回 0.0
    """

    def __init__(self, total_steps: int, window: int = 3) -> None:
        if total_steps <= 0:
            raise ValueError(f"total_steps must be > 0, got {total_steps}")
        if window <= 0:
            raise ValueError(f"window must be > 0, got {window}")
        self._total = total_steps
        self._window = window
        self._durations: list[float] = []

    # ── Public API ───────────────────────────────────────────────
    @property
    def total_steps(self) -> int:
        return self._total

    @property
    def completed_steps(self) -> int:
        return len(self._durations)

    @property
    def has_data(self) -> bool:
        """是否已有至少一步耗时记录，可用于决定 UI 是否显示 ETA。"""
        return bool(self._durations)

    def record_step(self, duration_seconds: float) -> None:
        """记录一个已完成步骤的实际耗时（自动裁剪到上限）。

        重复调用多于 ``total_steps`` 次不会抛错，但超出的记录
        不参与 ETA 估算（窗口只看最近 N 步）。
        """
        self._durations.append(cap_step_duration(duration_seconds))

    def estimate_remaining(self, completed: int) -> float | None:
        """估算剩余秒数。

        Parameters
        ----------
        completed:
            当前已完成步骤数（含刚完成的）。可为 0（尚未开始）
            或 total（全部完成）。

        Returns
        -------
        剩余秒数；``None`` 表示数据不足（无 ETA）；0.0 表示全部完成。
        """
        if completed < 0:
            completed = 0
        if completed >= self._total:
            return 0.0
        if not self._durations:
            return None
        # 滑动窗口：只取最近 N 步
        recent = self._durations[-self._window:]
        avg = sum(recent) / len(recent)
        # 剩余步数：按 UI 视角是 total - completed
        # 但 VM 可能多调几次 record_step，所以用 _total 作分母基准
        remaining = max(0, self._total - completed)
        return avg * remaining

    def reset(self) -> None:
        """清空历史（开始新一次生产流水线时调用）。"""
        self._durations.clear()


__all__ = [
    "ProgressETA",
    "cap_step_duration",
    "format_seconds",
]
