#!/usr/bin/env python3
"""导出工作线程组件

从 step_export.py 提取 ExportWorker
"""

from PySide6.QtCore import QThread, Signal


# ── 导出工作线程 ────────────────────────────────────────────
class ExportWorker(QThread):
    """后台导出线程"""

    progress = Signal(str, int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, project, output_dir, fmt, subtitle_style, parent=None):
        super().__init__(parent)
        self._project = project
        self._output_dir = output_dir
        self._fmt = fmt
        self._subtitle_style = subtitle_style

    def run(self):
        try:
            from scenefab.services.video.monologue_maker import MonologueMaker
            maker = MonologueMaker()
            maker.set_progress_callback(self._on_progress)

            self.progress.emit("准备导出", 10)

            if self._fmt == "jianying":
                output_path = maker.export_to_jianying(
                    self._project,
                    self._output_dir,
                )
            else:
                output_path = maker.export_to_mp4(
                    self._project,
                    self._output_dir,
                    subtitle_style=self._subtitle_style,
                )

            self.progress.emit("完成", 100)
            self.finished.emit(output_path)

        except AttributeError:
            try:
                output_path = maker.export_to_jianying(
                    self._project,
                    self._output_dir,
                )
                self.finished.emit(output_path)
            except Exception as e:
                self.error.emit(str(e))
        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, stage_label: str, progress: float):
        pct = int(progress * 80) + 10
        self.progress.emit(stage_label, pct)
