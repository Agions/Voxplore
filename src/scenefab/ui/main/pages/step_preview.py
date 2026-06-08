#!/usr/bin/env python3
"""解说预览 + 编辑页面

Task 2.3 UX 改善:
- 解说文案预览：QTextEdit 显示 AI 生成的解说稿
- 手动编辑：预览文案只读，编辑时切换
- 风格/角色调整：QComboBox 选择预设风格，QLineEdit 设置角色参数

组件拆分:
- NarrationSegmentCard -> narration_segment_card.py
- StylePresetPanel -> style_preset_panel.py
- PreviewTextArea -> preview_text_area.py
"""

import threading

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .preview_text_area import PreviewTextArea
from .style_preset_panel import StylePresetPanel

# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    "bg_card":     "oklch(0.16 0.01 250)",
    "bg_input":    "oklch(0.13 0.01 250)",
    "border":      "oklch(0.24 0.01 250)",
    "primary":     "oklch(0.65 0.20 250)",
    "primary_l":   "oklch(0.70 0.24 250)",
    "text":        "oklch(0.93 0.01 250)",
    "text_sub":    "oklch(0.75 0.01 250)",
    "text_muted":  "oklch(0.55 0.01 250)",
}


# ── StepPreview 主组件 ─────────────────────────────────────
class StepPreview(QWidget):
    """
    解说预览 + 编辑页面
    整合：文案预览区 + 风格设置 + 分段编辑
    """
    back_requested = Signal()
    generate_requested = Signal(str, str, str, str)
    # back_requested: 返回上一步


    def __init__(self, video_path: str = "", narration_text: str = "",
                 style: str = "治愈", parent=None):
        super().__init__(parent)
        self._video_path = video_path
        self._narration_text = narration_text
        self._current_style = style
        self._project_id = None
        self._setup_ui()

        if narration_text:
            self._load_demo_segments(narration_text)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # ── 标题栏 ──
        header = QHBoxLayout()
        back_btn = QPushButton("← 分组")
        back_btn.setObjectName("secondary_btn")
        back_btn.setFixedSize(90, 36)
        back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(back_btn)

        title = QLabel("解说预览")
        title.setFont(QFont("", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_T['text']};")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # ── 主内容区：左侧预览 + 右侧设置 ──────────────────
        main_split = QSplitter(Qt.Orientation.Horizontal)
        main_split.setHandleWidth(16)
        main_split.setStyleSheet("""
            QSplitter::handle {
                background: transparent;
            }
        """)

        # 左侧：文案预览
        self._preview_area = PreviewTextArea()
        self._preview_area.setSizePolicy(QSizePolicy.Policy.Expanding,
                                         QSizePolicy.Policy.Expanding)
        main_split.addWidget(self._preview_area)

        # 右侧：风格设置
        self._style_panel = StylePresetPanel()
        self._style_panel.setFixedWidth(240)
        self._style_panel.style_changed.connect(self._on_style_changed)
        main_split.addWidget(self._style_panel)

        main_split.setStretchFactor(0, 1)
        main_split.setStretchFactor(1, 0)
        layout.addWidget(main_split)

        # ── 进度条（生成进度）──────────────────────────────
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {_T['bg_input']};
                border: 1px solid {_T['border']};
                border-radius: 6px;
                height: 8px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {_T['primary']}, stop:1 {_T['primary_l']});
                border-radius: 6px;
            }}
        """)
        layout.addWidget(self._progress_bar)

        # ── 底部操作 ────────────────────────────────────────
        btn_layout = QHBoxLayout()

        # 保存草稿
        self._save_btn = QPushButton("💾 保存草稿")
        self._save_btn.setObjectName("secondary_btn")
        self._save_btn.setFixedSize(110, 40)
        self._save_btn.clicked.connect(self._on_save_draft)
        btn_layout.addWidget(self._save_btn)

        btn_layout.addStretch()

        # 导出文案
        self._export_btn = QPushButton("📤 导出文案")
        self._export_btn.setObjectName("secondary_btn")
        self._export_btn.setFixedSize(110, 40)
        self._export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(self._export_btn)

        # 生成配音
        self._generate_btn = QPushButton("🎙 生成配音 →")
        self._generate_btn.setObjectName("primary_btn")
        self._generate_btn.setFixedSize(140, 44)
        self._generate_btn.clicked.connect(self._on_generate)
        btn_layout.addWidget(self._generate_btn)
        layout.addLayout(btn_layout)

    def _load_demo_segments(self, text: str):
        """加载示例分段（演示用）"""
        # 模拟分段
        segments = [
            ("00:00-00:10", "【开场】今天天气真好，阳光从窗户洒进来，让人心情格外舒畅。", "happy"),
            ("00:10-00:25", "【叙述】我独自坐在咖啡馆里工作，周围的氛围安静而温馨。", "neutral"),
            ("00:25-00:40", "【高潮】突然，一位陌生人走过来，问我能否借用一下充电宝...", "excited"),
            ("00:40-00:55", "【转折】我抬头一看，竟然是多年未见的老朋友！", "tense"),
            ("00:55-01:10", "【结尾】这个世界真小，缘分就是这么奇妙。", "nostalgic"),
        ]
        self._preview_area.load_segments(segments)

    def _on_style_changed(self, style: str, role: str, params: str):
        """风格改变时触发"""
        self._current_style = style
        # 可在此触发重新生成（debounce）

    def _on_save_draft(self):
        """保存草稿到项目"""
        # 获取当前文本内容
        if self._preview_area._bulk_edit_cb.isChecked():
            text = self._preview_area._bulk_text_edit.toPlainText()
        else:
            # 从分段卡片收集文本
            segments = self._preview_area.get_segments()
            text = "\n".join(seg[1] for seg in segments)

        if not text.strip():
            QMessageBox.warning(self, "保存失败", "解说文案为空，请先生成或输入文案")
            return

        # 如果有当前项目，直接保存
        if hasattr(self, '_project_id') and self._project_id:
            self._save_to_project(text)
            return

        # 否则弹出文件保存对话框
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存解说文案",
            "narrations.txt",
            "文本文件 (*.txt);;所有文件 (*.*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                self._save_btn.setText("✅ 已保存")
                QTimer.singleShot(1500, lambda: self._save_btn.setText("💾 保存草稿"))
            except Exception as e:
                QMessageBox.warning(self, "保存失败", f"无法保存文件：{e}")

    def _save_to_project(self, text: str):
        """保存到当前项目"""
        try:
            # 获取 ProjectManager
            from scenefab.services.orchestration import ProjectManager
            manager = ProjectManager()
            project = manager.get_project(self._project_id)
            if project:
                project.settings.narration_text = text
                manager.save(project)
                self._save_btn.setText("✅ 已保存")
                QTimer.singleShot(1500, lambda: self._save_btn.setText("💾 保存草稿"))
            else:
                QMessageBox.warning(self, "保存失败", "无法获取项目信息")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存项目失败：{e}")

    def _on_export(self):
        """导出文案为独立文件"""
        if self._preview_area._bulk_edit_cb.isChecked():
            text = self._preview_area._bulk_text_edit.toPlainText()
        else:
            segments = self._preview_area.get_segments()
            text = "\n".join(seg[1] for seg in segments)

        if not text.strip():
            QMessageBox.warning(self, "导出失败", "解说文案为空")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出解说文案",
            "narrations.txt",
            "文本文件 (*.txt);;Markdown (*.md);;所有文件 (*.*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                QMessageBox.information(self, "导出成功", f"文案已导出至：\n{file_path}")
            except Exception as e:
                QMessageBox.warning(self, "导出失败", f"无法导出文件：{e}")

    def _on_generate(self):
        """触发生成配音"""
        style = self._style_panel.get_current_style()
        role = self._style_panel.get_role()
        params = self._style_panel.get_custom_params()
        self.generate_requested.emit(style, role, params, self._narration_text)

    def set_narration_text(self, text: str):
        """外部设置解说文案（由 AI 生成后调用）"""
        self._narration_text = text
        self._load_demo_segments(text)

    def set_generating(self, generating: bool):
        """设置生成状态（显示进度条）"""
        self._progress_bar.setVisible(generating)
        self._generate_btn.setEnabled(not generating)
        if generating:
            self._animate_progress()

    def _animate_progress(self):
        """动画进度条（演示用）"""
        def update():
            for i in range(0, 101, 2):
                self._progress_bar.setValue(i)
                import time
                time.sleep(0.03)
            self._progress_bar.setVisible(False)
        t = threading.Thread(target=update, daemon=True)
        t.start()
