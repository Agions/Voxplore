"""
导出信号 Mixin — 提取 3 个文件重复的 export_system 信号连接模式

重构前: 3 个文件 (_progress_dialog.py / export_panel.py / export_monitor.py)
        各自 100% 重复实现 setup_signals():
            self.export_system.export_started.connect(self.on_export_started)
            self.export_system.export_progress.connect(self.on_export_progress)
            self.export_system.export_completed.connect(self.on_export_completed)
            self.export_system.export_failed.connect(self.on_export_failed)

重构后: 继承此 Mixin, 自动获得 setup_export_signals() 方法,
        需要监听方实现以下 4 个回调: on_export_started/progress/completed/failed
"""

from typing import Protocol


class _ExportHandler(Protocol):
    """使用此 Mixin 的 widget 需实现以下 4 个回调方法"""

    def on_export_started(self, task_id: str) -> None: ...
    def on_export_progress(self, task_id: str, progress: float) -> None: ...
    def on_export_completed(self, task_id: str, output_path: str) -> None: ...
    def on_export_failed(self, task_id: str, error_message: str) -> None: ...


class ExportSignalMixin:
    """
    导出系统信号连接 Mixin

    使用方式:
        class MyWidget(QWidget, ExportSignalMixin):
            def __init__(self, export_system, parent=None):
                super().__init__(parent)
                self.export_system = export_system
                self.setup_export_signals()  # 自动连接 4 个信号

    要求:
        - self.export_system 必须在调用 setup_export_signals() 前赋值
        - 子类必须实现 on_export_started / progress / completed / failed
    """

    def setup_export_signals(self) -> None:
        """连接 export_system 的 4 个标准信号到子类回调"""
        # type: ignore[attr-defined] — Mixin 假设子类提供 export_system + 4 个回调
        self.export_system.export_started.connect(self.on_export_started)  # type: ignore[attr-defined]
        self.export_system.export_progress.connect(self.on_export_progress)  # type: ignore[attr-defined]
        self.export_system.export_completed.connect(self.on_export_completed)  # type: ignore[attr-defined]
        self.export_system.export_failed.connect(self.on_export_failed)  # type: ignore[attr-defined]
