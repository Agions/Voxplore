"""
配音编辑窗口(Step 3)
AI 生成解说词 + 情感控制 + 预览
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QScrollArea, QFrame, QGridLayout,
    QTextEdit, QSlider, QGroupBox, QComboBox,
    QSpacerItem, QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont
from app.ui.windows.base_step_window import BaseStepWindow


class NarrationWindow(BaseStepWindow):
    """
    Step 3: 配音编辑窗口
    功能:
    - AI 生成解说词文本编辑
    - 情感风格选择(平静/兴奋/悬疑/温暖/励志)
    - 语速控制滑块
    - 预览播放按钮
    - TTS 生成进度
    """

    narration_ready = Signal(dict)

    def __init__(self, parent=None):
        super().__init__("配音编辑", 2, parent)
        self._narration_text = ""
        self._emotion = "平静"
        self._speed = 1.0
        self._setup_content()

    def _setup_content(self):
        layout = QVBoxLayout()
        layout.setSpacing(16)

        # 左:文本编辑 | 右:情感控制
        split = QHBoxLayout()
        split.setSpacing(24)

        # ── 左侧:解说词编辑 ──
        left = QVBoxLayout()
        left.setSpacing(12)

        editor_label = QLabel("解说词")
        editor_label.setObjectName("section_title")
        left.addWidget(editor_label)

        self.text_editor = QTextEdit()
        self.text_editor.setPlaceholderText("AI 将根据场景自动生成解说词...\n\n或者直接在此输入自定义解说词")
        self.text_editor.setObjectName("narration_editor")
        self.text_editor.setFont(QFont("Inter", 14))
        self.text_editor.setMinimumHeight(200)
        left.addWidget(self.text_editor, stretch=1)

        # AI 生成按钮
        btn_generate = QPushButton("🤖 AI 生成解说词")
        btn_generate.setObjectName("primary")
        btn_generate.clicked.connect(self._generate_narration)
        left.addWidget(btn_generate)

        # ── 右侧:情感控制 ──
        right = QVBoxLayout()
        right.setSpacing(16)

        # 情感风格
        emotion_group = QGroupBox("情感风格")
        emotion_group.setObjectName("control_group")
        emotion_layout = QVBoxLayout(emotion_group)
        emotion_layout.setSpacing(8)

        emotions = ["平静", "兴奋", "悬疑", "温暖", "励志"]
        self.emotion_combo = QComboBox()
        self.emotion_combo.addItems(emotions)
        self.emotion_combo.setObjectName("emotion_combo")
        self.emotion_combo.currentTextChanged.connect(
            lambda t: setattr(self, '_emotion', t)
        )
        emotion_layout.addWidget(self.emotion_combo)

        # 情感描述
        self.emotion_desc = QLabel("适合日常记录、叙述性内容")
        self.emotion_desc.setObjectName("emotion_desc")
        emotion_layout.addWidget(self.emotion_desc)

        right.addWidget(emotion_group)

        # 语速控制
        speed_group = QGroupBox("语速")
        speed_group.setObjectName("control_group")
        speed_layout = QVBoxLayout(speed_group)
        speed_layout.setSpacing(8)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(25)
        self.speed_slider.valueChanged.connect(self._on_speed_change)

        speed_labels = QHBoxLayout()
        speed_labels.addWidget(QLabel("0.5x"))
        speed_labels.addStretch()
        speed_labels.addWidget(QLabel("2.0x"))
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addLayout(speed_labels)

        self.speed_label = QLabel("当前: 1.0x")
        self.speed_label.setObjectName("speed_label")
        speed_layout.addWidget(self.speed_label)

        right.addWidget(speed_group)

        # 预览按钮
        btn_preview = QPushButton("▶ 预览配音")
        btn_preview.setObjectName("secondary")
        btn_preview.clicked.connect(self._preview_audio)
        right.addWidget(btn_preview)

        right.addStretch()

        split.addLayout(left, stretch=2)
        split.addLayout(right, stretch=1)

        layout.addLayout(split)

        # ── 底部:TTS 生成进度 ──
        progress_group = QFrame()
        progress_group.setObjectName("progress_group")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(8)

        self.tts_progress = QProgressBar()
        self.tts_progress.setRange(0, 100)
        self.tts_progress.setValue(0)
        self.tts_progress.setTextVisible(True)
        self.tts_progress.hide()

        self.tts_label = QLabel("准备就绪")
        self.tts_label.setObjectName("tts_label")
        self.tts_label.hide()

        progress_layout.addWidget(self.tts_progress)
        progress_layout.addWidget(self.tts_label)

        btn_generate_tts = QPushButton("🎤 生成配音")
        btn_generate_tts.setObjectName("primary")
        btn_generate_tts.clicked.connect(self._generate_tts)
        progress_layout.addWidget(btn_generate_tts)

        layout.addWidget(progress_group)

        self._content_wrapper = QWidget()
        self._content_wrapper.setLayout(layout)
        self._main_layout.insertWidget(1, self._content_wrapper)

    def _generate_narration(self):
        """模拟 AI 生成解说词"""
        sample_text = (
            "大家好,我是今天的讲述者。\n\n"
            "画面中,一位年轻人正走在繁忙的城市街道上。\n"
            "他穿着简约,手里提着一个背包,目光中透着坚定。\n\n"
            "城市的喧嚣仿佛与他无关,他正沉浸在自己的思绪中。\n"
            "这一刻,时间仿佛静止了。"
        )
        self.text_editor.setPlainText(sample_text)
        self._narration_text = sample_text
        self.btn_next.setEnabled(True)

    def _on_speed_change(self, value):
        self._speed = value / 100
        self.speed_label.setText(f"当前: {self._speed:.1f}x")

    def _preview_audio(self):
        """预览配音(模拟)"""
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "预览", "配音预览功能开发中...")

    def _generate_tts(self):
        """模拟 TTS 生成"""
        self.tts_progress.show()
        self.tts_label.show()
        self.btn_next.setEnabled(True)

        # 模拟进度
        import time
        for i in range(0, 101, 5):
            self.tts_progress.setValue(i)
            self.tts_label.setText(f"生成中... {i}%")
            time.sleep(0.1)

        self.tts_label.setText("生成完成 ✓")

    def can_proceed(self) -> bool:
        return bool(self.text_editor.toPlainText().strip())

    def get_data(self) -> dict:
        return {
            "narration": self.text_editor.toPlainText(),
            "emotion": self._emotion,
            "speed": self._speed,
        }

    def set_pipeline(self, pipeline):
        """由 MainWindow 调用，注入 PipelineController"""
        self._pipeline = pipeline
        if pipeline:
            pipeline.stage_changed.connect(self.on_pipeline_stage)
            pipeline.stage_progress.connect(self.on_pipeline_progress)

    def on_pipeline_stage(self, stage: str, desc: str):
        """Pipeline 阶段变化回调"""
        self.tts_label.setText(desc)
        self.tts_label.show()

    def on_pipeline_progress(self, stage: str, pct: float):
        """Pipeline 进度回调"""
        self.tts_progress.setValue(int(pct * 100))
