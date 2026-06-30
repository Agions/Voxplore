#!/usr/bin/env python3
"""Production page ViewModel (Phase 2B).

Drives the 5-step first-person narration pipeline as a state machine:

    01 素材导入    (ingest source video, hand off to ProjectManager)
    02 场景拆分    (extract scenes + emotion peaks)
    03 脚本生成    (MonologueMaker.generate_script)
    04 配音字幕    (MonologueMaker.generate_voice + generate_captions)
    05 导出发布    (export draft + close pipeline)

The ViewModel exposes:

- :attr:`step_status` — list of status strings, one per step.
  Values: ``"pending"`` / ``"active"`` / ``"done"`` / ``"error"``.
- :attr:`pipeline_state` — aggregate state: ``"idle"`` / ``"running"`` /
  ``"done"`` / ``"failed"``.
- :attr:`current_step` — 0-based index of the in-flight step (or -1).

The view (``ProductionPage``) reads these on construction and updates
its 5 pipeline rows. The ViewModel re-emits on every step transition.

Design notes
------------

The ViewModel drives state, not actual work. The real heavy lifting
(MonologueMaker.generate_*) is delegated to a background thread so the
UI stays responsive; this is wired through a small ``QThreadPool``-based
helper (:class:`PipelineRunner`). For the first cut (Phase 2B MVP) the
runner is a no-op worker that just advances the state machine — wiring
the real MonologueMaker call sites is Phase 2B+1.

The ViewModel is tolerant when no ``Application`` is bound: it still
constructs, exposes properties, and the ``start_pipeline`` call is a
no-op. This keeps tests that don't construct a real app cheap.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from scenefab.services.video.monologue_maker import MonologueMaker
from scenefab.ui.viewmodels import ViewModelBase

if TYPE_CHECKING:
    from scenefab.application import Application

# ── Step definitions (5 步流水线) ──────────────────────────────────────
STEP_DEFINITIONS: list[tuple[str, str, str]] = [
    ("01", "素材导入", "选择影视片段并记录来源"),
    ("02", "场景拆分", "识别人物、冲突和关键转折"),
    ("03", "脚本生成", "使用第一人称视角组织叙事"),
    ("04", "配音字幕", "完成音频、字幕与节奏校准"),
    ("05", "导出发布", "按竖屏平台参数生成成片"),
]

# 每个 step 对应的 status 显示名
_STATUS_LABELS: dict[str, str] = {
    "pending": "待开始",
    "active": "进行中",
    "done": "已完成",
    "error": "失败",
}


# ── 异步执行 helper ───────────────────────────────────────────────────
class _PipelineStepSignals(QObject):
    """Per-step signals for cross-thread delivery.

    QRunnable cannot itself declare signals; the convention is to
    hold a QObject-derived sibling that owns them.
    """

    step_finished = Signal(int)  # step index
    step_failed = Signal(int, str)  # step index + error message
    pipeline_finished = Signal(str)  # project path
    pipeline_failed = Signal(str)  # error message


class _StepRunner(QRunnable):
    """Background worker that advances one pipeline step.

    For Phase 2B MVP this is a no-op that just emits ``step_finished``
    after a brief QThreadPool::msleep(50) — the real work (calling
    MonologueMaker.generate_script etc.) is wired up in Phase 2B+1
    when the full 5-step runtime is settled.
    """

    def __init__(self, step_index: int) -> None:
        super().__init__()
        self.signals = _PipelineStepSignals()
        self._step_index = step_index

    @Slot()
    def run(self) -> None:  # pragma: no cover - exercised via QThreadPool
        try:
            # Phase 2B+1: 此处接 MonologueMaker.generate_*
            #   - step 2 → generate_script
            #   - step 3 → generate_voice + generate_captions
            #   - step 4 → export_to_jianying
            self.signals.step_finished.emit(self._step_index)
        except Exception as e:  # noqa: BLE001 - runner must never crash UI
            self.signals.step_failed.emit(self._step_index, str(e))


# ── 主 ViewModel ──────────────────────────────────────────────────────
class ProductionPageViewModel(ViewModelBase):
    """5-step pipeline state machine for the production page."""

    step_status_changed = Signal(int)  # step index
    pipeline_state_changed = Signal()
    current_step_changed = Signal()
    pipeline_finished = Signal(str)  # project path
    pipeline_failed = Signal(str)  # error message

    def __init__(self, application: Application | None = None, parent=None) -> None:
        super().__init__(application, parent)
        self._step_status: list[str] = ["pending"] * len(STEP_DEFINITIONS)
        self._pipeline_state: str = "idle"  # idle / running / done / failed
        self._current_step: int = -1
        self._thread_pool = QThreadPool.globalInstance()
        self._last_project_path: str = ""

    # ── 公开属性 ────────────────────────────────────────────────────
    @property
    def step_definitions(self) -> list[tuple[str, str, str]]:
        return list(STEP_DEFINITIONS)

    @property
    def step_status(self) -> list[str]:
        return list(self._step_status)

    @property
    def pipeline_state(self) -> str:
        return self._pipeline_state

    @property
    def current_step(self) -> int:
        return self._current_step

    @property
    def status_label(self) -> str:
        """Return human-readable label for the current pipeline state."""
        return {
            "idle": "就绪",
            "running": "进行中",
            "done": "已完成",
            "failed": "失败",
        }.get(self._pipeline_state, "未知")

    def get_step_status(self, index: int) -> str:
        if 0 <= index < len(self._step_status):
            return self._step_status[index]
        return "pending"

    def get_status_label(self, status: str) -> str:
        return _STATUS_LABELS.get(status, status)

    # ── 业务入口 ────────────────────────────────────────────────────
    def start_pipeline(self, source_video: str, context: str) -> None:
        """Start the 5-step pipeline. Idempotent: re-starting while
        running is a no-op (the user must wait or reset)."""
        if self._pipeline_state == "running":
            return
        if not source_video or not context:
            return
        self._reset_for_new_run()
        self._set_pipeline_state("running")
        self._advance_to_step(0)

    def reset_pipeline(self) -> None:
        """Reset all steps back to pending. Safe to call any time."""
        self._reset_for_new_run()
        self._set_pipeline_state("idle")

    # ── 内部:状态机 ────────────────────────────────────────────────
    def _reset_for_new_run(self) -> None:
        for i in range(len(self._step_status)):
            if self._step_status[i] != "pending":
                self._step_status[i] = "pending"
                self.step_status_changed.emit(i)
        self._current_step = -1
        self.current_step_changed.emit()
        self._last_project_path = ""

    def _set_pipeline_state(self, new_state: str) -> None:
        if new_state != self._pipeline_state:
            self._pipeline_state = new_state
            self.pipeline_state_changed.emit()

    def _advance_to_step(self, index: int) -> None:
        """Mark step ``index`` as active and dispatch its runner."""
        if not 0 <= index < len(self._step_status):
            return
        self._current_step = index
        self.current_step_changed.emit()
        self._step_status[index] = "active"
        self.step_status_changed.emit(index)
        self._dispatch_step(index)

    def _mark_step_done(self, index: int) -> None:
        if not 0 <= index < len(self._step_status):
            return
        self._step_status[index] = "done"
        self.step_status_changed.emit(index)
        if index + 1 < len(self._step_status):
            self._advance_to_step(index + 1)
        else:
            self._set_pipeline_state("done")
            self.pipeline_finished.emit(self._last_project_path)

    def _mark_step_failed(self, index: int, error: str) -> None:
        if 0 <= index < len(self._step_status):
            self._step_status[index] = "error"
            self.step_status_changed.emit(index)
        self._set_pipeline_state("failed")
        self.pipeline_failed.emit(error)

    # ── 内部:异步分发 ──────────────────────────────────────────────
    def _dispatch_step(self, index: int) -> None:
        runner = _StepRunner(index)
        runner.signals.step_finished.connect(self._on_step_finished)
        runner.signals.step_failed.connect(self._on_step_failed)
        self._thread_pool.start(runner)

    def _on_step_finished(self, index: int) -> None:
        self._mark_step_done(index)

    def _on_step_failed(self, index: int, error: str) -> None:
        self._mark_step_failed(index, error)

    # ── Service access (used by 2B+1 wiring) ────────────────────────
    def _monologue_maker(self) -> MonologueMaker | None:
        app = self._application
        if app is None:
            return None
        return app.get_service(MonologueMaker)


__all__ = ["ProductionPageViewModel", "STEP_DEFINITIONS"]
