"""Export controller for the main window.

Owns the export format choice, output-directory prompt, and the
``ExportManager`` invocation. The main window wires callbacks for
``on_no_project`` and ``on_success`` so this controller doesn't need
to know about ``HomePage`` or the status bar.

Extracted from ``SceneFabMainWindow`` as part of the Phase B refactor.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMainWindow, QMessageBox

if TYPE_CHECKING:
    from app.services.video.monologue_maker import MonologueProject


# 默认导出格式选项（显示文案 → 内部 enum 映射）
EXPORT_FORMATS: tuple[tuple[str, str], ...] = (
    ("剪映草稿", "JIANYING"),
    ("MP4 视频", "MP4"),
)


class ExportController(QObject):
    """Drives the export dialog and dispatches to ``ExportManager``.

    Signals
    -------
    exported(output_dir)
        Emitted after a successful export with the resolved output
        directory so callers (status bar, home dashboard) can react.
    failed(error_message)
        Emitted when the underlying ``ExportManager`` raises.
    """

    exported = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        window: QMainWindow,
        *,
        get_project: Callable[[], MonologueProject | None],
        on_no_project: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(window)
        self._window = window
        self._get_project = get_project
        self._on_no_project = on_no_project

    # ──────────────────────────────────────────────────────────
    # 公共 API
    # ──────────────────────────────────────────────────────────

    def run(self) -> None:
        """Show the export dialog and execute the chosen format."""
        project = self._get_project()
        if project is None:
            if self._on_no_project is not None:
                self._on_no_project()
            else:
                QMessageBox.warning(self._window, "无法导出", "请先完成生产流程")
            return

        fmt_choice = self._prompt_format()
        if fmt_choice is None:
            return

        output_dir = self._prompt_output_dir()
        if not output_dir:
            return

        self._execute(project, fmt_choice, output_dir)

    # ──────────────────────────────────────────────────────────
    # 对话框
    # ──────────────────────────────────────────────────────────

    def _prompt_format(self) -> str | None:
        labels = [label for label, _key in EXPORT_FORMATS]
        choice, ok = QInputDialog.getItem(
            self._window, "导出格式", "请选择导出格式:", labels, 0, False,
        )
        if not ok:
            return None
        # 找到对应的 key
        for label, key in EXPORT_FORMATS:
            if label == choice:
                return key
        return None

    def _prompt_output_dir(self) -> str:
        return QFileDialog.getExistingDirectory(self._window, "选择导出目录")

    # ──────────────────────────────────────────────────────────
    # 执行导出
    # ──────────────────────────────────────────────────────────

    def _execute(self, project, fmt_key: str, output_dir: str) -> None:
        from app.services.export.export_manager import (
            ExportConfig,
            ExportFormat,
            ExportManager,
        )

        export_format = (
            ExportFormat.JIANYING if fmt_key == "JIANYING" else ExportFormat.MP4
        )
        config = ExportConfig(format=export_format, output_path=output_dir)

        try:
            manager = ExportManager()
            project_data = self._build_export_payload(project, export_format)
            manager.export(project_data, config)
        except Exception as e:
            self.failed.emit(str(e))
            QMessageBox.critical(
                self._window, "导出失败", f"导出过程中出错:\n{e}"
            )
            return

        QMessageBox.information(
            self._window, "导出成功", f"已导出到:\n{output_dir}"
        )
        self.exported.emit(output_dir)

    @staticmethod
    def _build_export_payload(project, export_format):
        """Build the data structure expected by ``ExportManager``."""
        from app.services.export.export_manager import ExportFormat

        if export_format == ExportFormat.JIANYING:
            from app.services.export.jianying_adapter import JianyingDraft
            from app.services.video.track_builder import build_monologue_tracks

            draft = JianyingDraft(name=project.name)
            build_monologue_tracks(
                draft=draft,
                source_video=project.source_video,
                video_duration=project.video_duration,
                segments=project.segments,
                caption_style=project.caption_style,
            )
            return draft
        # MP4 / MOV / GIF — exporter wants the project object itself.
        return project


__all__ = ["ExportController", "EXPORT_FORMATS"]
