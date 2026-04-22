"""
导出窗口（Step 4）
格式选择 + 预览 + 导出进度
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QProgressBar, QGroupBox,
    QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal
from app.ui.windows.base_step_window import BaseStepWindow


class ExportWindow(BaseStepWindow):
    """
    Step 4: 导出窗口
    功能：
    - 输出格式选择（MP4 / 剪映草稿）
    - 质量预设（720p / 1080p / 4K）
    - 预览合成效果
    - 导出进度条
    - 完成通知
    """

    export_finished = Signal(str)

    def __init__(self, parent=None):
        super().__init__("导出", 3, parent)
        self._format = "mp4"
        self._quality = "1080p"
        self._setup_content()

    def _setup_content(self):
        layout = QVBoxLayout()
        layout.setSpacing(24)

        # ── 格式选择 ──
        format_group = QGroupBox("输出格式")
        format_group.setObjectName("option_group")
        format_layout = QHBoxLayout(format_group)
        format_layout.setSpacing(12)

        self.format_group = QButtonGroup(self)
        formats = [("MP4", "mp4"), ("剪映草稿", "jianian")]
        for label, value in formats:
            btn = QRadioButton(label)
            btn.setChecked(value == self._format)
            btn.value = value
            btn.toggled.connect(
                lambda checked, v=value: self._on_format_change(v) if checked else None
            )
            self.format_group.addButton(btn)
            format_layout.addWidget(btn)

        format_layout.addStretch()
        layout.addWidget(format_group)

        # ── 质量选择 ──
        quality_group = QGroupBox("输出质量")
        quality_group.setObjectName("option_group")
        quality_layout = QHBoxLayout(quality_group)
        quality_layout.setSpacing(12)

        self.quality_group = QButtonGroup(self)
        qualities = [("720p", "720p"), ("1080p", "1080p"), ("4K", "4k")]
        for label, value in qualities:
            btn = QRadioButton(label)
            btn.setChecked(value == self._quality)
            btn.value = value
            btn.toggled.connect(
                lambda checked, v=value: self._on_quality_change(v) if checked else None
            )
            self.quality_group.addButton(btn)
            quality_layout.addWidget(btn)

        quality_layout.addStretch()
        layout.addWidget(quality_group)

        # ── 预览区 ──
        preview_group = QFrame()
        preview_group.setObjectName("preview_area")
        preview_layout = QVBoxLayout(preview_group)

        preview_title = QLabel("合成预览")
        preview_title.setObjectName("section_title")
        preview_layout.addWidget(preview_title)

        self.preview_placeholder = QLabel("🎬 视频预览区域\n\n点击「开始导出」生成最终视频")
        self.preview_placeholder.setAlignment(Qt.AlignCenter)
        self.preview_placeholder.setObjectName("preview_placeholder")
        self.preview_placeholder.setMinimumHeight(200)
        preview_layout.addWidget(self.preview_placeholder)

        layout.addWidget(preview_group, stretch=1)

        # ── 导出进度 ──
        self.progress_group = QFrame()
        self.progress_group.setObjectName("export_progress")
        self.progress_group.hide()

        progress_layout = QVBoxLayout(self.progress_group)
        progress_layout.setSpacing(12)

        self.export_progress = QProgressBar()
        self.export_progress.setRange(0, 100)
        self.export_progress.setValue(0)
        self.export_progress.setTextVisible(True)

        self.export_label = QLabel("准备就绪")
        self.export_label.setObjectName("export_label")

        progress_layout.addWidget(self.export_progress)
        progress_layout.addWidget(self.export_label)
        layout.addWidget(self.progress_group)

        # ── 导出按钮 ──
        btn_layout = QHBoxLayout()
        btn_export = QPushButton("📤 开始导出")
        btn_export.setObjectName("primary")
        btn_export.clicked.connect(self._start_export)
        btn_layout.addWidget(btn_export)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        self._content_wrapper = QWidget()
        self._content_wrapper.setLayout(layout)
        self._main_layout.insertWidget(1, self._content_wrapper)

    def _on_format_change(self, fmt: str):
        self._format = fmt

    def _on_quality_change(self, quality: str):
        self._quality = quality

    def _start_export(self):
        """模拟导出过程"""
        self.progress_group.show()

        import time
        steps = [
            ("正在合成音视频...", 20),
            ("正在处理字幕...", 45),
            ("正在编码...", 70),
            ("正在生成缩略图...", 90),
            ("导出完成!", 100),
        ]

        for label_text, pct in steps:
            self.export_progress.setValue(pct)
            self.export_label.setText(label_text)
            time.sleep(0.8)

        self.preview_placeholder.setText("✅ 导出完成!\n\n文件已保存至：~/Videos/Voxplore/")
        self.finished.emit()

    def can_proceed(self) -> bool:
        return True

    def get_data(self) -> dict:
        return {
            "format": self._format,
            "quality": self._quality,
            "output_path": "~/Videos/Voxplore/",
        }
