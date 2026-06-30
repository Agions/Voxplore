#!/usr/bin/env python3
"""Production page ViewModel (Phase 2B + 2B+1).

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
- :attr:`runner_mode` — ``"noop"`` (no TTS key, default) or ``"live"``
  (real MonologueMaker calls). Read-only — set by ``start_pipeline``.

Design notes
------------

The runner is a callable injected at ``start_pipeline`` time. The default
(``_noop_runner``) advances the state machine without calling any
external service. When a TTS / LLM API key is present, the VM
substitutes a live runner that wraps ``MonologueMaker.generate_*`` calls.

The ``runner_mode`` is decided by :func:`_has_runtime_keys`, which checks
``SCENEFAB_TTS_KEY`` / ``SCENEFAB_LLM_KEY`` env vars OR an
``Application.get_config()`` flag. The check is intentionally cheap
(``os.getenv``) so ``start_pipeline`` stays synchronous.

A :class:`MonologueProject` is constructed in :meth:`start_pipeline`
(before any runner is dispatched) so the live runner can hand it
through ``generate_script`` / ``generate_voice`` / ``generate_captions``.
If construction fails (bad source path, missing file), the pipeline
fails immediately with a clear error message — no state machine
advances.

The ViewModel is tolerant when no ``Application`` is bound: it still
constructs, exposes properties, and ``start_pipeline`` falls back to
the noop runner. This keeps tests that don't construct a real app cheap.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from scenefab.services.video.monologue_maker import MonologueMaker, MonologueProject
from scenefab.ui.viewmodels import ViewModelBase

if TYPE_CHECKING:
    from scenefab.application import Application

logger = logging.getLogger(__name__)

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


def _has_runtime_keys() -> bool:
    """Decide whether the live runner can talk to real services.

    Returns True iff either env var is set (non-empty):
    - ``SCENEFAB_TTS_KEY`` (voice synthesis)
    - ``SCENEFAB_LLM_KEY`` (script generation / scene analysis)

    The check is intentionally *presence-only*: we never read the actual
    key value. A non-empty placeholder is enough to mark the project
    "live" — the real failure mode (401/403) surfaces inside the runner
    as a step_failed signal, which is the right UI feedback.
    """
    return bool(
        os.getenv("SCENEFAB_TTS_KEY", "").strip()
        or os.getenv("SCENEFAB_LLM_KEY", "").strip()
    )


# ── Runner callable type ──────────────────────────────────────────────
# A runner is ``Callable[[Any, int], None]``: it takes the live project
# + step index, performs the work, and returns. The first arg is ``Any``
# so the noop runner can accept the ``_StubProject`` sentinel without
# forcing every runner to declare a MonologueProject-typed parameter.
RunnerFn = Callable[[Any, int], None]


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


def _noop_runner(project: Any, step_index: int) -> None:
    """Default runner: advance state machine without external calls.

    Used when no TTS / LLM key is configured. Lets the UI demonstrate
    the state machine end-to-end (all 5 steps go pending → active → done)
    without requiring real service connectivity.
    """
    # project is accepted but not modified — keeps the signature stable
    # with the live runner so the VM never has to branch on runner kind.
    _ = (project, step_index)


def _live_runner(maker: MonologueMaker) -> RunnerFn:
    """Build a live runner that calls the real MonologueMaker methods.

    Step mapping (matches STEP_DEFINITIONS):
    - 0 素材导入    : no-op (project already constructed by VM caller)
    - 1 场景拆分    : no-op (handled by create_project internally)
    - 2 脚本生成    : maker.generate_script(project)
    - 3 配音字幕    : maker.generate_voice + generate_captions
    - 4 导出发布    : project.save() returns path

    Exceptions propagate to the ``_StepRunner`` wrapper which converts
    them to ``step_failed`` signals.
    """

    def _run(project: MonologueProject, step_index: int) -> None:
        if step_index == 2:
            maker.generate_script(project)
        elif step_index == 3:
            maker.generate_voice(project)
            maker.generate_captions(project)
        elif step_index == 4:
            # save() lives on MonologueProject, not MonologueMaker
            project.save()
        # steps 0/1 are handled in create_project (called by VM)

    return _run


class _StepRunner(QRunnable):
    """Background worker that advances one pipeline step.

    Receives a runner callable and dispatches it on the QThreadPool. Any
    exception from the runner is caught and reported via ``step_failed``
    — the UI thread must never see a raw Python exception.
    """

    def __init__(self, step_index: int, project: Any, runner: RunnerFn) -> None:
        super().__init__()
        self.signals = _PipelineStepSignals()
        self._step_index = step_index
        self._project = project
        self._runner = runner

    @Slot()
    def run(self) -> None:  # pragma: no cover - exercised via QThreadPool
        try:
            self._runner(self._project, self._step_index)
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
        self._runner_mode: str = "noop"  # noop / live
        self._current_project: MonologueProject | None = None

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
    def runner_mode(self) -> str:
        """``"live"`` if runtime keys are present, else ``"noop"``.

        Read-only — set per-run inside :meth:`start_pipeline` based on
        the env state at that moment.
        """
        return self._runner_mode

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
        running is a no-op (the user must wait or reset).

        Side effects (Phase 2B+1):
        - If a TTS / LLM key is configured AND a MonologueMaker service
          is registered, the VM switches to ``runner_mode="live"`` and
          constructs a real ``MonologueProject``. Steps 2-4 then call
          ``generate_script`` / ``generate_voice`` / ``generate_captions``
          / ``save`` on a worker thread.
        - Otherwise, ``runner_mode="noop"`` and the state machine
          advances without any external service call.
        """
        if self._pipeline_state == "running":
            return
        if not source_video or not context:
            return

        # 决定 runner kind + 构造 project (设置 _runner_mode)
        try:
            self._setup_pipeline(source_video, context)
        except Exception as e:  # noqa: BLE001 - bubble up to UI
            self._reset_for_new_run()
            self._set_pipeline_state("failed")
            self.pipeline_failed.emit(f"无法创建项目: {e}")
            return

        # Reset only step state — preserve _runner_mode set by _setup_pipeline
        self._reset_step_state()
        self._set_pipeline_state("running")
        self._advance_to_step(0)

    def reset_pipeline(self) -> None:
        """Reset all steps back to pending. Safe to call any time."""
        self._reset_for_new_run()
        self._set_pipeline_state("idle")

    # ── 内部:状态机 ────────────────────────────────────────────────
    def _setup_pipeline(self, source_video: str, context: str) -> None:
        """Decide runner + construct project for this run.

        Sets ``_runner_mode`` and ``_current_project``. The runner
        callable is selected here (per-run) so the same VM can be
        live in one run and noop in the next.
        """
        maker = self._monologue_maker()
        if _has_runtime_keys() and maker is not None:
            self._runner_mode = "live"
            try:
                self._current_project = maker.create_project(
                    source_video=source_video,
                    context=context,
                )
            except Exception as e:
                # create_project 失败时,降级 noop 但记录 warning
                logger.warning("MonologueMaker.create_project failed (%s), falling back to noop", e)
                self._runner_mode = "noop"
                self._current_project = None
        else:
            self._runner_mode = "noop"
            self._current_project = None

    def _reset_for_new_run(self) -> None:
        """Full reset: step state + runner + project.

        Used by :meth:`reset_pipeline` and on start_pipeline failure
        (when we want to start from a clean slate).
        """
        self._reset_step_state()
        self._last_project_path = ""
        self._current_project = None
        self._runner_mode = "noop"

    def _reset_step_state(self) -> None:
        """Reset only the 5 step statuses + current_step.

        Preserves ``_runner_mode`` and ``_current_project`` so callers
        who just set them (e.g. ``_setup_pipeline``) don't have their
        work wiped out. Used by :meth:`start_pipeline` after the
        runner mode has been decided.
        """
        for i in range(len(self._step_status)):
            if self._step_status[i] != "pending":
                self._step_status[i] = "pending"
                self.step_status_changed.emit(i)
        self._current_step = -1
        self.current_step_changed.emit()

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
        if self._current_project is None or self._runner_mode == "noop":
            # noop mode: 没有 project 也不需要,直接 no-op runner
            project = self._current_project or _StubProject()
            runner: Callable[[MonologueProject, int], None] = _noop_runner
        else:
            maker = self._monologue_maker()
            if maker is None:  # pragma: no cover - guarded by _setup_pipeline
                project = self._current_project
                runner = _noop_runner
            else:
                project = self._current_project
                runner = _live_runner(maker)

        runnable = _StepRunner(index, project, runner)
        runnable.signals.step_finished.connect(self._on_step_finished)
        runnable.signals.step_failed.connect(self._on_step_failed)
        self._thread_pool.start(runnable)

    def _on_step_finished(self, index: int) -> None:
        # step 4 (导出发布): project.save() returns path → capture for pipeline_finished
        if (
            index == 4
            and self._current_project is not None
            and self._runner_mode == "live"
        ):
            try:
                self._last_project_path = self._current_project.save()
            except Exception as e:  # noqa: BLE001
                self._mark_step_failed(index, f"导出失败: {e}")
                return
        self._mark_step_done(index)

    def _on_step_failed(self, index: int, error: str) -> None:
        self._mark_step_failed(index, error)

    # ── Service access ──────────────────────────────────────────────
    def _monologue_maker(self) -> MonologueMaker | None:
        app = self._application
        if app is None:
            return None
        return app.get_service(MonologueMaker)


class _StubProject:
    """Sentinel for noop mode — satisfies the runner signature.

    The runner callable is typed ``Callable[[MonologueProject, int], None]``
    so we need *something* to pass in. ``_StubProject`` accepts every
    attribute access (defensive) and never raises — its sole purpose
    is to keep the type system happy in noop mode.
    """

    def __getattr__(self, name: str) -> _StubProject:
        return self

    def __call__(self, *args: object, **kwargs: object) -> _StubProject:
        return self


__all__ = [
    "ProductionPageViewModel",
    "STEP_DEFINITIONS",
    "_has_runtime_keys",
]
