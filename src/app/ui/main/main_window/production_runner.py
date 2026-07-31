"""Production flow controller.

Extracted from ``SceneFabMainWindow`` so the main window no longer owns
the ``BaseWorker`` lifecycle, the 5-step progress mapping, or the
MonologueMaker wiring. The controller exposes Qt signals for
``started``, ``finished``, ``failed``, ``cancelled`` so views and the
main window can subscribe without poking private state.

The runner also keeps a single ``ProductionWorker`` instance alive per
run; calling ``start`` again while one is running is a no-op, and
``cancel`` is safe to call multiple times.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from app.core.base_worker import BaseWorker

if TYPE_CHECKING:
    from app.services.video.monologue_maker import MonologueProject


# ─── 5-step pipeline UI mapping ─────────────────────────────────────────
_PROGRESS_STEP_MAP: dict[int, str] = {
    1: "素材导入",
    2: "场景拆分",
    3: "脚本生成",
    4: "配音字幕",
    5: "导出发布",
}

_NEXT_ACTIVE_STEP: dict[int, str] = {
    1: "场景拆分",
    2: "脚本生成",
    3: "配音字幕",
    4: "导出发布",
}

_ALL_PRODUCTION_STEPS: tuple[str, ...] = (
    "素材导入",
    "场景拆分",
    "脚本生成",
    "配音字幕",
    "导出发布",
)

# Default emotions surfaced in the "情感风格" prompt.
DEFAULT_EMOTIONS: tuple[str, ...] = (
    "neutral", "惆怅", "忧郁", "开心", "平静", "温柔", "excited",
)
DEFAULT_CONTEXT = "第一人称影视解说"


class ProductionRunner(QObject):
    """Drives the 5-step MonologueMaker pipeline off the UI thread.

    Signals
    -------
    step_status_changed(step_name, status, color)
        Emitted on every progress tick. UI pages should update their
        step indicator widget. ``status`` is one of ``"进行中"``,
        ``"已完成"``, ``"已失败"``. ``color`` is a CSS hex string
        suitable for QSS.
    progress_message(current, total, message)
        Mirrors ``BaseWorker.progress`` for the status bar.
    finished(project, project_path)
        Emitted exactly once on a successful run. ``project`` is the
        in-memory ``MonologueProject``; ``project_path`` is the
        persisted ``.scenefab`` file path.
    failed(error_message)
        Emitted when the worker reports an error.
    cancelled()
        Emitted when the worker confirmed cancellation.
    """

    step_status_changed = Signal(str, str, str)
    progress_message = Signal(int, int, str)
    finished = Signal(object, str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker: BaseWorker | None = None

    # ──────────────────────────────────────────────────────────
    # 公共 API
    # ──────────────────────────────────────────────────────────

    def is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def start(self, video_path: str, context: str, emotion: str) -> bool:
        """Spin up the worker. Returns False if one is already running."""
        if self.is_running():
            return False

        worker = self._make_worker(video_path, context, emotion)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_finished)
        worker.error.connect(self._on_error)
        worker.cancelled.connect(self._on_cancelled)
        self._worker = worker
        worker.start()
        return True

    def cancel(self) -> bool:
        """Request cancellation. Returns False if no worker is running."""
        if not self.is_running():
            return False
        assert self._worker is not None
        self._worker.cancel()
        return True

    @staticmethod
    def default_emotions() -> tuple[str, ...]:
        return DEFAULT_EMOTIONS

    # ──────────────────────────────────────────────────────────
    # Worker factory
    # ──────────────────────────────────────────────────────────

    def _make_worker(self, video_path: str, context: str, emotion: str) -> BaseWorker:
        # The factory captures ``video_path`` / ``context`` / ``emotion``
        # in closure so we don't have to subclass per-run.
        outer = self

        class ProductionWorker(BaseWorker):
            def _run(self):
                from pathlib import Path

                from app.services.video.monologue_maker import MonologueMaker

                maker = MonologueMaker()
                project = maker.create_project(
                    source_video=video_path,
                    context=context,
                    emotion=emotion,
                )
                if project is None:
                    raise RuntimeError("项目创建失败")
                self.emit_progress(1, 5, "场景分析完成")
                if self.check_cancel_or_pause():
                    return

                maker.generate_script(project)
                self.emit_progress(2, 5, "脚本生成完成")
                if self.check_cancel_or_pause():
                    return

                maker.generate_voice(project)
                self.emit_progress(3, 5, "配音合成完成")
                if self.check_cancel_or_pause():
                    return

                maker.generate_captions(project)
                self.emit_progress(4, 5, "字幕生成完成")

                output_path = Path(project.output_dir) / \
                    f"{project.name}.scenefab"
                project_path = project.save(str(output_path))
                self.emit_progress(5, 5, "项目已保存")

                return {"project": project, "project_path": project_path}

        # PySide6 doesn't allow type-checking against the dynamic class
        # above, so let the caller treat the result as BaseWorker.
        worker = ProductionWorker(name="ProductionWorker", cancellable=True)
        # Forward to outer to keep refcounts stable.
        del outer  # satisfy linters; closure above already captures `self`.
        return worker  # type: ignore[return-value]

    # ──────────────────────────────────────────────────────────
    # Worker → runner signal forwarding
    # ──────────────────────────────────────────────────────────

    def _on_progress(self, current: int, total: int, message: str) -> None:
        self.progress_message.emit(current, total, message)

        if current >= total:
            for step_name in _ALL_PRODUCTION_STEPS:
                self.step_status_changed.emit(step_name, "已完成", "#52c41a")
            return

        done = _PROGRESS_STEP_MAP.get(current)
        if done:
            self.step_status_changed.emit(done, "已完成", "#52c41a")
        next_step = _NEXT_ACTIVE_STEP.get(current)
        if next_step:
            self.step_status_changed.emit(next_step, "进行中", "")

    def _on_finished(self, result) -> None:
        # ``BaseWorker.finished`` carries a ``WorkerResult``; the data
        # dict was built by ``ProductionWorker._run``.
        try:
            if result is None or not getattr(result, "success", False):
                self.failed.emit("生产流程完成但有警告")
                return
            data = getattr(result, "data", None) or {}
            project = data.get("project")
            project_path = data.get("project_path", "")
            self.finished.emit(project, project_path)
        finally:
            self._worker = None

    def _on_error(self, error_msg: str) -> None:
        self.failed.emit(error_msg)
        self._worker = None

    def _on_cancelled(self) -> None:
        self.cancelled.emit()
        self._worker = None


__all__ = [
    "ProductionRunner",
    "DEFAULT_EMOTIONS",
    "DEFAULT_CONTEXT",
    "_ALL_PRODUCTION_STEPS",
]
