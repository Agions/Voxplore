#!/usr/bin/env python3
"""
AI 分析步骤页面
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...main.pages.step_base import ContentCard, StepPage
from ...theme.ds_tokens import Colors, FontSizes, Radii


class AIOptionCard(QFrame):
    """AI 选项卡片"""

    toggled = Signal(bool)

    def __init__(
        self, icon: str, title: str, desc: str, enabled: bool = True, parent=None
    ):
        super().__init__(parent)
        self._icon = icon
        self._title = title
        self._enabled = enabled
        self.setFixedHeight(80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("ai_card")
        self._setup_style()
        self._setup_ui(title, desc)

    def _setup_style(self):
        self.setStyleSheet(f"""
            #ai_card {{
                background: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: {Radii.base};
            }}
            #ai_card:hover {{
                border-color: {Colors.PRIMARY_500};
            }}
        """)

    def _setup_ui(self, title: str, desc: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self._enabled)
        self.checkbox.setStyleSheet(f"""
            QCheckBox {{
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid {Colors.BORDER_DEFAULT};
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {Colors.PRIMARY_500};
                border-color: {Colors.PRIMARY_500};
            }}
        """)
        self.checkbox.stateChanged.connect(self.toggled.emit)
        layout.addWidget(self.checkbox)

        icon_label = QLabel(self._icon)
        icon_label.setFont(QFont("", 24))
        icon_label.setFixedWidth(40)
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
        title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        text_layout.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setFont(QFont("", FontSizes.xs))
        desc_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)
        layout.addStretch()


class AnalysisProgress(QFrame):
    """分析进度显示"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0
        self.setFixedHeight(100)
        self.setObjectName("analysis_progress")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #analysis_progress {{
                background: {Colors.BG_SURFACE};
                border: 1px solid {Colors.PRIMARY_500};
                border-radius: {Radii.lg};
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title = QLabel("✨ AI 正在分析中...")
        title.setFont(QFont("", FontSizes.md, QFont.Weight.Medium))
        title.setStyleSheet(f"color: {Colors.PRIMARY_400};")
        header_layout.addWidget(title)
        header_layout.addStretch()
        self._percent_label = QLabel("0%")
        self._percent_label.setFont(QFont("", FontSizes.sm))
        self._percent_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        header_layout.addWidget(self._percent_label)
        layout.addLayout(header_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {Colors.BG_ELEVATED};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.PRIMARY_500},
                    stop:1 {Colors.ACCENT_500}
                );
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        self._stage_label = QLabel("正在提取音频...")
        self._stage_label.setFont(QFont("", FontSizes.xs))
        self._stage_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        layout.addWidget(self._stage_label)

    def set_progress(self, value: int, stage: str = ""):
        self._progress = value
        self.progress_bar.setValue(value)
        self._percent_label.setText(f"{value}%")
        if stage:
            self._stage_label.setText(stage)


class StepAnalysisPage(StepPage):
    """AI 分析步骤页 (step 1)"""

    def __init__(self, parent=None):
        super().__init__(1, parent)
        self._analyzing = False

    def _build_content(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(24)

        # 分析选项
        options_card = ContentCard("AI 分析选项")
        opts_layout = options_card.layout()

        self.options = [
            ("🎙️", "语音识别", "自动提取视频中的语音内容", True),
            ("✂️", "精彩片段检测", "智能识别高光时刻", True),
            ("👤", "人脸识别", "检测画面中的人物", False),
            ("📝", "字幕生成", "自动生成同步字幕", True),
            ("🏷️", "场景分类", "自动识别场景类型", False),
            ("🎭", "情感分析", "分析视频情感基调", False),
        ]

        for icon, title, desc, default in self.options:
            opt = AIOptionCard(icon, title, desc, default)
            opts_layout.addWidget(opt)

        layout.addWidget(options_card)

        # 高级设置
        advanced_card = ContentCard("高级设置")
        adv_layout = advanced_card.layout()

        adv_row = QHBoxLayout()
        adv_row.addWidget(QLabel("分析线程数"))
        adv_row.addStretch()

        thread_spin = QSpinBox()
        thread_spin.setRange(1, 8)
        thread_spin.setValue(4)
        thread_spin.setFixedWidth(80)
        adv_row.addWidget(thread_spin)
        adv_layout.addLayout(adv_row)

        layout.addWidget(advanced_card)

        # 进度区（初始隐藏）
        self.progress_widget = AnalysisProgress()
        self.progress_widget.setVisible(False)
        layout.addWidget(self.progress_widget)

        layout.addStretch()

        # 开始分析按钮
        start_btn = QPushButton("🚀 开始 AI 分析")
        start_btn.setObjectName("btn_primary")
        start_btn.setFixedSize(180, 44)
        start_btn.setFont(QFont("", FontSizes.md, QFont.Weight.Medium))
        start_btn.clicked.connect(self._start_analysis)
        layout.addWidget(start_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        return container

    def _start_analysis(self):
        if self._analyzing:
            return

        self._analyzing = True
        self.progress_widget.setVisible(True)
        self._simulate_progress()

    def _simulate_progress(self):
        from PySide6.QtCore import (
            QTimer,  # noqa: F811  # local import needed to avoid top-level Qt overhead
        )

        self._stage_idx = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_progress)
        self._timer.start(400)

    def _update_progress(self):
        val = self.progress_widget.progress_bar.value() + 2
        if val > 100:
            val = 100
        stages = [
            "正在提取音频...",
            "正在识别语音...",
            "正在检测精彩片段...",
            "正在生成字幕...",
            "正在分析场景...",
            "分析完成！",
        ]
        stage_idx = min((val // 20), len(stages) - 1)
        self.progress_widget.set_progress(val, stages[stage_idx])
        if val >= 100:
            self._timer.stop()
            self._analyzing = False
