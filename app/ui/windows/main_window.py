"""
Voxplore 主窗口 — 完整的窗口管理器 + Pipeline 集成
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStackedWidget,
    QMessageBox
)

from app.ui.components.step_indicator import StepIndicator
from app.ui.windows.upload_window import UploadWindow
from app.ui.windows.scene_window import SceneWindow
from app.ui.windows.narration_window import NarrationWindow
from app.ui.windows.export_window import ExportWindow
from app.ui.windows.projects_window import ProjectsWindow
from app.orchestration.pipeline_controller import PipelineController


class MainWindow(QMainWindow):
    """
    主窗口 + Pipeline 集成
    管理 4 步创作流程 + 步骤间数据传递
    """

    # 共享数据（各步骤产生的数据）
    _shared_data = {}  # key: "files" | "scenes" | "narration" | "export_config"

    def __init__(self):
        super().__init__()
        self._pipeline = PipelineController()
        self._projects_window = None
        self._active_project_path = None
        self._setup_ui()
        self._connect_pipeline_signals()
        self._setup_window_connections()

    def _setup_ui(self):
        self.setWindowTitle("Voxplore — AI 第一人称视频解说")
        self.setMinimumSize(1024, 700)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        # 步骤指示器（初始隐藏，等进入流程后显示）
        self.step_indicator = StepIndicator()
        self.step_indicator.hide()
        root_layout.addWidget(self.step_indicator)

        # 页面堆栈
        self.pages = QStackedWidget()
        root_layout.addWidget(self.pages)

        # 注册 4 个步骤窗口
        self.upload_win = UploadWindow()
        self.scene_win = SceneWindow()
        self.narration_win = NarrationWindow()
        self.export_win = ExportWindow()

        self.pages.addWidget(self.upload_win)    # index 0
        self.pages.addWidget(self.scene_win)     # index 1
        self.pages.addWidget(self.narration_win) # index 2
        self.pages.addWidget(self.export_win)    # index 3

        # 初始显示第一步（会触发 ProjectsWindow 入口）
        self.pages.setCurrentIndex(0)
        self._show_projects_page()

    def _setup_window_connections(self):
        """连接各窗口的信号到主窗口"""
        self.upload_win.next_requested.connect(self._on_upload_done)
        self.scene_win.next_requested.connect(self._on_scene_done)
        self.narration_win.next_requested.connect(self._on_narration_done)
        self.export_win.finished.connect(self._on_pipeline_done)

        self.step_indicator.step_changed.connect(
            lambda s: self.pages.setCurrentIndex(s)
        )

    def _connect_pipeline_signals(self):
        """连接 PipelineController 信号到窗口"""
        self._pipeline.stage_changed.connect(self._on_stage_changed)
        self._pipeline.stage_progress.connect(self._on_progress)
        self._pipeline.error_occurred.connect(self._on_error)

        # 注入 pipeline 到各窗口
        self.scene_win.set_pipeline(self._pipeline)
        self.narration_win.set_pipeline(self._pipeline)

    def _show_projects_page(self):
        """显示项目列表页面（入口）"""
        if self._projects_window is None:
            self._projects_window = ProjectsWindow()
            self._projects_window.project_selected.connect(self._on_project_selected)
            self.pages.addWidget(self._projects_window)

        # 切换到项目列表
        self.pages.setCurrentWidget(self._projects_window)
        self.step_indicator.hide()

    def _on_project_selected(self, project_path: str):
        """用户选择了一个项目（新建或打开）"""
        self._active_project_path = project_path
        # 重置各步骤窗口
        self._reset_steps()
        # 切换到上传步骤
        self._show_upload_step()

    def _show_upload_step(self):
        """进入上传步骤"""
        self.step_indicator.show()
        self.step_indicator.set_step(0)
        self.pages.setCurrentIndex(0)

    def _reset_steps(self):
        """重置所有步骤窗口"""
        self.upload_win = UploadWindow()
        self.scene_win = SceneWindow()
        self.narration_win = NarrationWindow()
        self.export_win = ExportWindow()

        # 重建页面
        indices_to_remove = []
        for i in range(self.pages.count()):
            w = self.pages.widget(i)
            if isinstance(w, (UploadWindow, SceneWindow, NarrationWindow, ExportWindow)):
                indices_to_remove.append(i)
        # 逆序删除
        for i in sorted(indices_to_remove, reverse=True):
            self.pages.removeWidget(self.pages.widget(i))

        self.pages.insertWidget(0, self.upload_win)
        self.pages.insertWidget(1, self.scene_win)
        self.pages.insertWidget(2, self.narration_win)
        self.pages.insertWidget(3, self.export_win)

        # 重新连接
        self._setup_window_connections()
        self._connect_pipeline_signals()

    def _on_upload_done(self):
        """Step 1 完成：保存文件列表，进入 Step 2"""
        data = self.upload_win.get_data()
        self._shared_data["files"] = data["files"]
        self.scene_win.set_shared_data({"files": data["files"]})
        self._go_to_step(1)

    def _on_scene_done(self):
        """Step 2 完成：保存场景数据，进入 Step 3"""
        data = self.scene_win.get_data()
        self._shared_data["scenes"] = data["scenes"]
        self.narration_win.set_shared_data({
            "files": self._shared_data.get("files", []),
            "scenes": data["scenes"],
        })
        self._go_to_step(2)

    def _on_narration_done(self):
        """Step 3 完成：保存配音数据，进入 Step 4"""
        data = self.narration_win.get_data()
        self._shared_data["narration"] = data
        self.export_win.set_shared_data({
            "files": self._shared_data.get("files", []),
            "scenes": self._shared_data.get("scenes", []),
            "narration": data,
        })
        self._go_to_step(3)

    def _on_pipeline_done(self):
        """Pipeline 完成"""
        QMessageBox.information(
            self, "🎉 完成",
            "视频导出成功！\n\n文件已保存至：~/Videos/Voxplore/"
        )
        # 返回项目列表
        self._show_projects_page()
        self._shared_data.clear()

    def _on_stage_changed(self, stage: str, desc: str):
        """Pipeline 阶段变化"""
        current = self.pages.currentWidget()
        if hasattr(current, 'on_pipeline_stage'):
            current.on_pipeline_stage(stage, desc)

    def _on_progress(self, stage: str, pct: float):
        """Pipeline 进度更新"""
        current = self.pages.currentWidget()
        if hasattr(current, 'on_pipeline_progress'):
            current.on_pipeline_progress(stage, pct)

    def _on_error(self, msg: str):
        QMessageBox.critical(self, "❌ 错误", f"Pipeline 错误：\n{msg}")

    def _go_to_step(self, step: int):
        if 0 <= step < 4:
            self.step_indicator.set_step(step)
            self.pages.setCurrentIndex(step)

    def load_project(self, project_path: str):
        """从项目路径加载项目"""
        self._active_project_path = project_path
        self._show_upload_step()
