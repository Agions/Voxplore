#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 2: Pipeline 执行 — OKLCH Design Tokens"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextEdit, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QCursor

from ...components import MacCard
from app.orchestration.pipeline_controller import PipelineStage

# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    # Surface
    "bg_card":   "oklch(0.16 0.01 250)",   # 卡片背景
    "bg_input":  "oklch(0.13 0.01 250)",   # 输入/日志背景
    "bg_active": "oklch(0.17 0.01 250)",   # 运行中背景
    "bg_base":   "oklch(0.13 0.01 250)",   # 页面背景
    # Border
    "border":    "oklch(0.24 0.01 250)",   # 默认边框
    # Text
    "text":      "oklch(0.93 0.01 250)",   # 主要文字
    "text_sub":  "oklch(0.75 0.01 250)",   # 次要文字
    "text_muted":"oklch(0.55 0.01 250)",   # 辅助文字
    # Stage state colors
    "idle":      "oklch(0.24 0.01 250)",   # #2e2e2e 闲置
    "running":   "oklch(0.65 0.20 250)",   # #388BFD 运行中
    "running_l":  "oklch(0.70 0.24 250)",  # 运行中亮色（脉冲用）
    "done":      "oklch(0.65 0.22 145)",   # #2EA043 完成
    "error":     "oklch(0.75 0.20 85)",    # #D29922 错误
    "skip_c":    "oklch(0.40 0.01 250)",   # 跳过/灰显
    # Gradient
    "primary_g1": "oklch(0.65 0.20 250)",
    "primary_g2": "oklch(0.72 0.22 200)",
}

_STAGE_COLORS = {"idle": _T["idle"], "running": _T["running"], "done": _T["done"], "error": _T["error"], "skip": _T["skip_c"]}
_STAGE_ICONS  = {"idle": "⏸", "running": "⚡", "done": "✓", "error": "✗", "skip": "⊘"}


class StageCard(QFrame):
    """Pipeline 阶段卡片 — OKLCH: 圆角12px · 脉冲动画"""
    stage_clicked = Signal(PipelineStage)

    def __init__(self, stage: PipelineStage, label: str, parent=None):
        super().__init__(parent)
        self._stage = stage
        self._label = label
        self._state = "idle"
        self._anim_toggle = False
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedSize(160, 100)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._apply_style()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label = QLabel(_STAGE_ICONS["idle"])
        self.icon_label.setFont(QFont("", 20))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)
        self.name_label = QLabel(self._label)
        self.name_label.setFont(QFont("", 12, QFont.Weight.Bold))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet(f"color: {_T['text_sub']};")
        layout.addWidget(self.name_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {_T['idle']};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {_T['primary_g1']},
                    stop:1 {_T['primary_g2']});
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self.progress_bar)
        self.sub_label = QLabel("")
        self.sub_label.setFont(QFont("", 10))
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet(f"color: {_T['text_muted']};")
        layout.addWidget(self.sub_label)
        self.clicked.connect(lambda: self.stage_clicked.emit(self._stage))

    def _apply_style(self):
        color = _STAGE_COLORS.get(self._state, _T["idle"])
        bg = _T["bg_active"] if self._state == "running" else _T["bg_card"]
        border_w = "2px" if self._state == "running" else "1px"
        self.setStyleSheet(f"QFrame {{ background: {bg}; border: {border_w} solid {color}; border-radius: 12px; }}")

    def set_state(self, state: str, sub: str = ""):
        self._state = state
        self._apply_style()
        self.icon_label.setText(_STAGE_ICONS.get(state, "⏸"))
        self.sub_label.setText(sub)
        if state == "running":
            self._start_animation()
        else:
            self._stop_animation()

    def set_progress(self, value: float):
        self.progress_bar.setValue(int(value * 1000))
        self.sub_label.setText(f"{int(value * 100)}%")

    def _start_animation(self):
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._pulse_border)
        self._anim_timer.start(500)

    def _pulse_border(self):
        self._anim_toggle = not self._anim_toggle
        color = _T["running_l"] if self._anim_toggle else _T["running"]
        self.setStyleSheet(f"QFrame {{ background: {_T['bg_active']}; border: 2px solid {color}; border-radius: 12px; }}")

    def _stop_animation(self):
        if hasattr(self, "_anim_timer"):
            self._anim_timer.stop()


class ScriptEditor(QWidget):
    """解说词编辑器 — OKLCH"""
    script_changed = Signal(str)
    retry_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel("解说词")
        title.setFont(QFont("", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_T['text']};")
        header.addWidget(title)
        self.word_count_label = QLabel("0 字")
        self.word_count_label.setStyleSheet(f"color: {_T['text_muted']}; font-size: 12px;")
        header.addWidget(self.word_count_label)
        header.addStretch()
        self.edit_btn = QPushButton("✏️ 编辑")
        self.edit_btn.setObjectName("secondary_btn")
        self.edit_btn.setFixedSize(56, 26)
        self.edit_btn.clicked.connect(self._toggle_edit)
        header.addWidget(self.edit_btn)
        self.retry_btn = QPushButton("🔄 重试")
        self.retry_btn.setObjectName("secondary_btn")
        self.retry_btn.setFixedSize(72, 26)
        self.retry_btn.hide()
        self.retry_btn.clicked.connect(lambda: self.retry_requested.emit())
        header.addWidget(self.retry_btn)
        layout.addLayout(header)
        self.editor = QTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setMinimumHeight(200)
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background: {_T['bg_input']};
                color: {_T['text']};
                border: 1px solid {_T['border']};
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.6;
            }}
            QTextEdit:focus {{ border-color: {_T['running']}; }}
        """)
        self.editor.textChanged.connect(lambda: (
            self.word_count_label.setText(f"{len(self.editor.toPlainText())} 字"),
            self.script_changed.emit(self.editor.toPlainText())
        ))
        layout.addWidget(self.editor)

    def _toggle_edit(self):
        if self.editor.isReadOnly():
            self.editor.setReadOnly(False)
            self.editor.setFocus()
            self.edit_btn.setText("✓ 完成")
            self.retry_btn.show()
        else:
            self.editor.setReadOnly(True)
            self.edit_btn.setText("✏️ 编辑")
            self.retry_btn.hide()

    def set_segments(self, segments: list):
        lines = [f"[{i}] {s.get('script', '')}" for i, s in enumerate(segments, 1)]
        self.editor.setPlainText("\n\n".join(lines))

    def get_text(self) -> str:
        return self.editor.toPlainText()


class StepPipeline(QWidget):
    """Step 2 — OKLCH Design Tokens"""
    finished = Signal(str)

    _STAGES = [
        (PipelineStage.ANALYZING, "场景理解"),
        (PipelineStage.SCRIPT,  "解说生成"),
        (PipelineStage.VOICE,    "配音合成"),
        (PipelineStage.CAPTION,  "字幕制作"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._controller = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        title = QLabel("正在创作...")
        title.setFont(QFont("", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_T['text']};")
        layout.addWidget(title)

        stage_layout = QHBoxLayout()
        stage_layout.addStretch()
        self.stage_cards = {}
        for stage, label in self._STAGES:
            card = StageCard(stage, label)
            card.stage_clicked.connect(lambda s: None)
            self.stage_cards[stage.value] = card
            stage_layout.addWidget(card)
        stage_layout.addStretch()
        layout.addLayout(stage_layout)

        self.script_editor = ScriptEditor()
        self.script_editor.retry_requested.connect(self._on_retry)
        layout.addWidget(self.script_editor, 1)

        log_card = MacCard()
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(12, 12, 12, 12)
        log_header = QLabel("处理日志")
        log_header.setStyleSheet(f"color: {_T['text_muted']}; font-size: 12px; font-weight: 600;")
        log_layout.addWidget(log_header)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(120)
        self.log_area.setStyleSheet(f"""
            QTextEdit {{
                background: {_T['bg_input']};
                color: {_T['text_muted']};
                border: 1px solid {_T['border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 11px;
            }}
        """)
        log_layout.addWidget(self.log_area)
        layout.addWidget(log_card)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.back_btn = QPushButton("← 上一步")
        self.back_btn.setObjectName("secondary_btn")
        self.back_btn.setFixedSize(120, 40)
        self.back_btn.clicked.connect(lambda: self.finished.emit("back"))
        btn_layout.addWidget(self.back_btn)
        self.next_btn = QPushButton("导出视频 →")
        self.next_btn.setObjectName("primary_btn")
        self.next_btn.setFixedSize(140, 44)
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(lambda: self.finished.emit("export"))
        btn_layout.addWidget(self.next_btn)
        layout.addLayout(btn_layout)

    def bind_controller(self, controller):
        self._controller = controller

    def _on_retry(self):
        if self._controller:
            self._controller.retry_stage(PipelineStage.SCRIPT)

    def append_log(self, text: str):
        self.log_area.append(text)

    def set_stage_state(self, stage_value: int, state: str, sub: str = ""):
        card = self.stage_cards.get(stage_value)
        if card:
            card.set_state(state, sub)

    def set_stage_progress(self, stage_value: int, value: float):
        card = self.stage_cards.get(stage_value)
        if card:
            card.set_progress(value)

    def enable_export(self):
        self.next_btn.setEnabled(True)
