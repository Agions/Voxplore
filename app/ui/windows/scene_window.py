"""
场景理解窗口（Step 2）
AI 分析视频场景，生成场景描述卡片
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QScrollArea, QFrame, QProgressBar
)
from PySide6.QtCore import Signal
from app.ui.windows.base_step_window import BaseStepWindow


class SceneWindow(BaseStepWindow):
    """
    Step 2: 场景理解窗口
    功能：
    - 显示 AI 分析进度
    - 场景卡片列表（时间范围 + 描述）
    - 可编辑场景描述
    - 点击场景跳转视频位置
    """

    scenes_generated = Signal(list)

    def __init__(self, parent=None):
        super().__init__("场景理解", 1, parent)
        self._scenes = []
        self._pipeline = None
        self._setup_content()

    def _setup_content(self):
        layout = QVBoxLayout()
        layout.setSpacing(16)

        # 提示文字
        hint = QLabel("AI 正在分析视频内容，识别场景、人物行为和环境...")
        hint.setObjectName("hint_text")
        layout.addWidget(hint)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        layout.addWidget(self.progress)

        # 进度文字
        self.progress_label = QLabel("准备就绪")
        self.progress_label.setObjectName("progress_label")
        layout.addWidget(self.progress_label)

        # 场景卡片区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("scene_scroll")

        scroll_content = QWidget()
        self.scenes_layout = QVBoxLayout(scroll_content)
        self.scenes_layout.setSpacing(12)
        self.scenes_layout.addStretch()

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, stretch=1)

        # 模拟分析按钮
        btn_area = QHBoxLayout()
        btn_analyze = QPushButton("🎬 开始 AI 分析")
        btn_analyze.setObjectName("primary")
        btn_analyze.clicked.connect(self._simulate_analysis)
        btn_area.addWidget(btn_analyze)
        btn_area.addStretch()

        layout.addLayout(btn_area)

        self._content_wrapper = QWidget()
        self._content_wrapper.setLayout(layout)
        self._main_layout.insertWidget(1, self._content_wrapper)

    def _on_shared_data_set(self, data: dict):
        """当 MainWindow 设置共享数据时调用（来自上一步骤）"""
        files = data.get("files", [])
        if files:
            self.progress_label.setText(f"已加载 {len(files)} 个视频文件，可点击「开始分析」")

    def _simulate_analysis(self):
        """模拟 AI 分析过程（真实场景中替换为实际 AI 调用）"""
        import random
        self._scenes = []
        # 模拟 3-5 个场景
        for i in range(random.randint(3, 5)):
            self._scenes.append({
                "id": i,
                "start": i * 15,
                "end": (i + 1) * 15,
                "description": f"场景 {i+1}：主角 '{'走在街上' if i % 2 == 0 else '进入房间'}'，周围环境 '{'城市街道' if i % 2 == 0 else '室内空间'}'",
            })

        # 模拟进度动画
        self._animate_progress(0, 100, 2000)

    def _animate_progress(self, start, end, duration_ms):
        import time
        steps = 20
        step_ms = duration_ms // steps
        for i in range(steps + 1):
            value = start + (end - start) * i // steps
            self.progress.setValue(value)
            self.progress_label.setText(f"分析进度: {value}%")
            time.sleep(step_ms / 1000)

        # 分析完成，渲染场景卡片
        self._render_scene_cards()

    def _render_scene_cards(self):
        """渲染场景卡片"""
        # 清除现有卡片
        while self.scenes_layout.count() > 1:
            item = self.scenes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for scene in self._scenes:
            card = SceneCard(scene)
            # 在 stretch 之前插入
            self.scenes_layout.insertWidget(
                self.scenes_layout.count() - 1, card
            )

        self.btn_next.setEnabled(True)

    def can_proceed(self) -> bool:
        return len(self._scenes) > 0

    def get_data(self) -> dict:
        return {"scenes": self._scenes}

    def set_pipeline(self, pipeline):
        """由 MainWindow 调用，注入 PipelineController"""
        self._pipeline = pipeline
        if pipeline:
            pipeline.stage_changed.connect(self.on_pipeline_stage)
            pipeline.stage_progress.connect(self.on_pipeline_progress)

    def on_pipeline_stage(self, stage: str, desc: str):
        """Pipeline 阶段变化回调"""
        self.progress_label.setText(desc)

    def on_pipeline_progress(self, stage: str, pct: float):
        """Pipeline 进度回调"""
        self.progress.setValue(int(pct * 100))


class SceneCard(QFrame):
    """
    场景卡片
    显示单个场景的时间范围和描述
    """

    def __init__(self, scene: dict, parent=None):
        super().__init__(parent)
        self.scene = scene
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("scene_card")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 时间范围
        time_label = QLabel(f"⏱ {self.scene['start']:02d}:00 — {self.scene['end']:02d}:00")
        time_label.setObjectName("scene_time")

        # 描述
        desc = QLabel(self.scene["description"])
        desc.setObjectName("scene_desc")
        desc.setWordWrap(True)

        layout.addWidget(time_label)
        layout.addWidget(desc)
