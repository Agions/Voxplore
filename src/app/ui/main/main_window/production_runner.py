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

from pathlib import Path
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QObject, Signal

from app.core.base_worker import BaseWorker
from app.models.project import (
    MultiVideoSource,
    MultiVideoStrategy,
    SeriesContext,
)  # v2.5.0

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
    "neutral",
    "惆怅",
    "忧郁",
    "开心",
    "平静",
    "温柔",
    "excited",
)
DEFAULT_CONTEXT = "第一人称影视解说"


class MultiProjectResult:
    """多视频生产结果容器（v2.5.0）。

    单视频场景下：``projects`` 是 1 元素列表，``paths`` 是 1 元素列表。
    多视频场景下：包含每个独立项目的 project / path。
    与 ``MonologueProject`` API 兼容的便利属性：
    - ``first_project`` / ``first_path`` : 取第一个项目与路径
    - ``count`` : 项目数
    - ``is_multi`` : 是否为多视频
    """

    __slots__ = ("projects", "paths", "strategy")

    def __init__(
        self,
        projects: list[MonologueProject],
        paths: list[str],
        strategy: str = "single",
    ) -> None:
        self.projects = list(projects)
        self.paths = list(paths)
        self.strategy = strategy

    @property
    def count(self) -> int:
        return len(self.projects)

    @property
    def is_multi(self) -> bool:
        return len(self.projects) > 1

    @property
    def first_project(self) -> MonologueProject | None:
        return self.projects[0] if self.projects else None

    @property
    def first_path(self) -> str:
        return self.paths[0] if self.paths else ""

    def __len__(self) -> int:
        return len(self.projects)

    def __iter__(self):
        return iter(self.projects)

    def __getitem__(self, idx: int) -> MonologueProject:
        return self.projects[idx]


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
        """启动单视频生产（向后兼容）。内部委派 :meth:`start_batch`。"""
        return self.start_batch([video_path], context, emotion)

    def start_batch(
        self,
        video_paths: list[str],
        context: str,
        emotion: str,
        *,
        strategy: str = "single",
        series_context: SeriesContext | None = None,
    ) -> bool:
        """启动多视频生产。

        Args:
            video_paths: 1-N 个视频文件路径
            context: 主题/情境
            emotion: 情感基调
            strategy: 策略 (``"single"``/``"concat"``/``"batch"``/``"series"``)
            series_context: 整季系列的共享上下文（仅 series 策略生效）

        Returns:
            True: 已启动；False: 已有任务运行中
        """
        if self.is_running():
            return False
        if not video_paths:
            return False

        # 防呆：1 路径强制 single，多路径默认 batch
        if len(video_paths) == 1 and strategy in ("batch", "series"):
            strategy = "single"

        worker = self._make_worker(
            video_paths, context, emotion, strategy, series_context
        )
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

    def _make_worker(
        self,
        video_paths: list[str],
        context: str,
        emotion: str,
        strategy: str,
        series_context: SeriesContext | None,
    ) -> BaseWorker:
        # The factory captures ``video_paths`` / ``context`` / ``emotion``
        # / ``strategy`` / ``series_context`` in closure so we don't have
        # to subclass per-run.
        outer = self

        class ProductionWorker(BaseWorker):
            def _run(self):
                from app.services.video.monologue_maker import MonologueMaker

                maker = MonologueMaker()

                # v2.5.0: 根据策略选择调用方式
                if strategy == "single" or len(video_paths) == 1:
                    projects = [
                        maker.create_project(
                            source_video=video_paths[0],
                            context=context,
                            emotion=emotion,
                            multi_strategy="single",
                        )
                    ]
                else:
                    # batch / concat / series : 用 create_batch
                    mvs = MultiVideoSource(
                        videos=[],
                        strategy=cast(MultiVideoStrategy, strategy),
                        series_context=series_context,
                    )
                    for p in video_paths:
                        mvs.add(p)
                    projects = maker.create_batch(
                        sources=mvs,
                        context=context,
                        emotion=emotion,
                    )

                if not projects:
                    raise RuntimeError("项目创建失败：未生成任何项目")
                self.emit_progress(1, 5, "场景分析完成")
                if self.check_cancel_or_pause():
                    return

                # 步骤 3-5: 逐个走完（batch 模式每个项目独立跑）
                saved_paths: list[str] = []
                for idx, project in enumerate(projects):
                    if self.check_cancel_or_pause():
                        return
                    maker.generate_script(project)
                    self.emit_progress(2, 5, f"脚本生成 {idx + 1}/{len(projects)}")
                    if self.check_cancel_or_pause():
                        return

                    maker.generate_voice(project)
                    self.emit_progress(3, 5, f"配音合成 {idx + 1}/{len(projects)}")
                    if self.check_cancel_or_pause():
                        return

                    maker.generate_captions(project)
                    self.emit_progress(4, 5, f"字幕生成 {idx + 1}/{len(projects)}")

                    output_path = Path(project.output_dir) / f"{project.name}.scenefab"
                    saved_paths.append(project.save(str(output_path)))

                self.emit_progress(5, 5, "全部项目已保存")

                # 单视频走老路径（兼容），多视频用 MultiProjectResult
                if len(projects) == 1:
                    return {
                        "project": projects[0],
                        "project_path": saved_paths[0],
                        "result": None,
                    }
                result = MultiProjectResult(projects, saved_paths, strategy=strategy)
                return {
                    "project": result.first_project,
                    "project_path": ";".join(saved_paths),
                    "result": result,
                }

        # PySide6 doesn't allow type-checking against the dynamic class
        # above, so let the caller treat the result as BaseWorker.
        worker = ProductionWorker(name="ProductionWorker", cancellable=True)
        # Forward to outer to keep refcounts stable.
        del outer  # satisfy linters; closure above already captures `self`.
        return worker

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
    "MultiProjectResult",
]
