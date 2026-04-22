#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解说预览 + 编辑页面

Task 2.3 UX 改善:
- 解说文案预览：QTextEdit 显示 AI 生成的解说稿
- 手动编辑：预览文案只读，编辑时切换
- 风格/角色调整：QComboBox 选择预设风格，QLineEdit 设置角色参数
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextEdit, QComboBox, QLineEdit, QCheckBox, QScrollArea,
    QSizePolicy, QProgressBar, QSplitter, QTabWidget
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont


# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    "bg_card":     "oklch(0.16 0.01 250)",
    "bg_input":    "oklch(0.13 0.01 250)",
    "bg_hover":    "oklch(0.14 0.01 250)",
    "bg_active":   "oklch(0.17 0.01 250)",
    "border":      "oklch(0.24 0.01 250)",
    "border_h":    "oklch(0.30 0.02 250)",
    "text":        "oklch(0.93 0.01 250)",
    "text_sub":    "oklch(0.75 0.01 250)",
    "text_muted":  "oklch(0.55 0.01 250)",
    "text_disabled":"oklch(0.40 0.01 250)",
    "primary":     "oklch(0.65 0.20 250)",
    "primary_l":   "oklch(0.70 0.24 250)",
    "success":     "oklch(0.65 0.22 145)",
    "warning":     "oklch(0.75 0.20 85)",
    "error":       "oklch(0.63 0.24 25)",
}


# ── 分段解说卡片 ────────────────────────────────────────────
class NarrationSegmentCard(QFrame):
    """
    单个解说分段卡片
    包含：时间段标签 + 文案预览/编辑 + 情感标记
    """
    content_changed = Signal(str)  # 发送编辑后的文案

    def __init__(self, segment_id: int, time_range: str, text: str,
                 emotion: str = "neutral", parent=None):
        super().__init__(parent)
        self._segment_id = segment_id
        self._time_range = time_range
        self._text = text
        self._emotion = emotion
        self._editing = False
        self._setup_ui()
        self._load_text(text)

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {_T['bg_card']};
                border: 1px solid {_T['border']};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # 头部行
        header = QHBoxLayout()
        header.setSpacing(8)

        # 时间段标签
        self._time_label = QLabel(self._time_range)
        self._time_label.setFont(QFont("", 11, QFont.Weight.SemiBold))
        self._time_label.setStyleSheet(f"""
            color: {_T['primary']};
            background: {_T['primary']}20;
            padding: 3px 8px;
            border-radius: 6px;
        """)
        header.addWidget(self._time_label)

        # 情感标签
        self._emotion_label = QLabel(self._get_emotion_text())
        self._emotion_label.setFont(QFont("", 10))
        self._emotion_label.setStyleSheet(f"color: {_T['text_muted']};")
        header.addWidget(self._emotion_label)

        header.addStretch()

        # 编辑/预览切换
        self._edit_btn = QPushButton("编辑")
        self._edit_btn.setObjectName("secondary_btn")
        self._edit_btn.setFixedSize(56, 26)
        self._edit_btn.clicked.connect(self._toggle_edit)
        header.addWidget(self._edit_btn)

        layout.addLayout(header)

        # ── 文案显示/编辑区 ──
        self._text_label = QLabel()
        self._text_label.setWordWrap(True)
        self._text_label.setFont(QFont("", 13))
        self._text_label.setStyleSheet(f"color: {_T['text']}; line-height: 1.6;")
        self._text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self._text_label)

        self._text_edit = QTextEdit()
        self._text_edit.setFont(QFont("", 13))
        self._text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {_T['bg_input']};
                color: {_T['text']};
                border: 1px solid {_T['border']};
                border-radius: 8px;
                padding: 10px;
                line-height: 1.6;
            }}
            QTextEdit:focus {{
                border-color: {_T['primary']};
            }}
        """)
        self._text_edit.setVisible(False)
        self._text_edit.textChanged.connect(self._on_edit_changed)
        layout.addWidget(self._text_edit)

        # 字数提示
        self._char_count = QLabel("")
        self._char_count.setStyleSheet(f"color: {_T['text_muted']}; font-size: 10px;")
        self._char_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._char_count)

    def _get_emotion_text(self) -> str:
        emotions = {
            "neutral": "😐 平静",
            "happy": "😊 开心",
            "sad": "😢 伤感",
            "excited": "🤩 激动",
            "tense": "😰 紧张",
            "nostalgic": "🌅 怀旧",
        }
        return emotions.get(self._emotion, "😐 平静")

    def _load_text(self, text: str):
        self._text = text
        self._text_label.setText(text)
        self._text_edit.setPlainText(text)
        self._update_char_count()

    def _toggle_edit(self):
        self._editing = not self._editing
        if self._editing:
            self._text_label.setVisible(False)
            self._text_edit.setVisible(True)
            self._text_edit.setPlainText(self._text)
            self._text_edit.setFocus()
            self._edit_btn.setText("保存")
            self._edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {_T['primary']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 6px 16px;
                    font-size: 12px;
                }}
            """)
        else:
            self._text_label.setVisible(True)
            self._text_edit.setVisible(False)
            self._text = self._text_edit.toPlainText()
            self._text_label.setText(self._text)
            self._edit_btn.setText("编辑")
            self._edit_btn.setObjectName("secondary_btn")
            self._edit_btn.setFixedSize(56, 26)
            self._edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {_T['text_sub']};
                    border: 1px solid {_T['border']};
                    border-radius: 8px;
                    padding: 6px 16px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    border-color: {_T['primary']};
                }}
            """)
            self.content_changed.emit(self._text)

    def _on_edit_changed(self):
        self._update_char_count()

    def _update_char_count(self):
        text = self._text_edit.toPlainText() if self._editing else self._text
        self._char_count.setText(f"{len(text)} 字")

    def set_text(self, text: str):
        self._load_text(text)

    def get_text(self) -> str:
        return self._text

    def get_segment_id(self) -> int:
        return self._segment_id


# ── 风格预设面板 ────────────────────────────────────────────
class StylePresetPanel(QFrame):
    """风格/角色参数调整面板"""
    style_changed = Signal(str, str, str)  # style, role, custom_params

    # 预设风格
    PRESET_STYLES = {
        "治愈": "温暖、柔和、抚慰人心的语调，适合生活记录",
        "悬疑": "低沉、神秘、引人入胜的叙述节奏",
        "励志": "充满能量、正向激励、鼓舞人心的表达",
        "怀旧": "温情、慢节奏、带有时光感的叙述",
        "浪漫": "细腻、温柔、充满感情的描述",
        "幽默": "轻松诙谐、自然流畅的调侃风格",
        "纪录片": "客观理性、旁白感强、信息密度高",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {_T['bg_card']};
                border: 1px solid {_T['border']};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 标题
        title = QLabel("风格设置")
        title.setFont(QFont("", 12, QFont.Weight.SemiBold))
        title.setStyleSheet(f"color: {_T['text_sub']};")
        layout.addWidget(title)

        # 风格选择
        style_row = QHBoxLayout()
        style_lbl = QLabel("解说风格")
        style_lbl.setStyleSheet(f"color: {_T['text_muted']}; font-size: 12px;")
        style_row.addWidget(style_lbl)

        self._style_combo = QComboBox()
        self._style_combo.addItems(list(self.PRESET_STYLES.keys()))
        self._style_combo.currentTextChanged.connect(self._on_style_changed)
        self._style_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {_T['bg_input']};
                color: {_T['text']};
                border: 1px solid {_T['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {_T['bg_card']};
                color: {_T['text']};
                border: 1px solid {_T['border']};
                border-radius: 8px;
                selection-background-color: {_T['bg_active']};
            }}
        """)
        style_row.addWidget(self._style_combo, stretch=1)
        layout.addLayout(style_row)

        # 风格描述
        self._style_desc = QLabel(self.PRESET_STYLES["治愈"])
        self._style_desc.setStyleSheet(f"color: {_T['text_muted']}; font-size: 11px;")
        self._style_desc.setWordWrap(True)
        layout.addWidget(self._style_desc)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {_T['border']}; max-height: 1px;")
        layout.addWidget(sep)

        # 角色名称
        role_row = QHBoxLayout()
        role_lbl = QLabel("主角名称")
        role_lbl.setStyleSheet(f"color: {_T['text_muted']}; font-size: 12px;")
        role_row.addWidget(role_lbl)

        self._role_input = QLineEdit()
        self._role_input.setPlaceholderText("默认为「我」")
        self._role_input.setStyleSheet(f"""
            QLineEdit {{
                background: {_T['bg_input']};
                color: {_T['text']};
                border: 1px solid {_T['border']};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {_T['primary']}; }}
            QLineEdit::placeholder {{ color: {_T['text_muted']}; }}
        """)
        self._role_input.textChanged.connect(self._emit_change)
        role_row.addWidget(self._role_input, stretch=1)
        layout.addLayout(role_row)

        # 自定义参数
        param_row = QHBoxLayout()
        param_lbl = QLabel("角色参数")
        param_lbl.setStyleSheet(f"color: {_T['text_muted']}; font-size: 12px;")
        param_row.addWidget(param_lbl)

        self._param_input = QLineEdit()
        self._param_input.setPlaceholderText("如：年龄30、性格内向…")
        self._param_input.setStyleSheet(f"""
            QLineEdit {{
                background: {_T['bg_input']};
                color: {_T['text']};
                border: 1px solid {_T['border']};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {_T['primary']}; }}
            QLineEdit::placeholder {{ color: {_T['text_muted']}; }}
        """)
        self._param_input.textChanged.connect(self._emit_change)
        param_row.addWidget(self._param_input, stretch=1)
        layout.addLayout(param_row)

        # 重新生成按钮
        self._regen_btn = QPushButton("⟳ 重新生成")
        self._regen_btn.setObjectName("secondary_btn")
        self._regen_btn.setFixedHeight(34)
        self._regen_btn.clicked.connect(self._on_regenerate)
        layout.addWidget(self._regen_btn)

        layout.addStretch()

    def _on_style_changed(self, text: str):
        self._style_desc.setText(self.PRESET_STYLES.get(text, ""))
        self._emit_change()

    def _emit_change(self):
        self.style_changed.emit(
            self._style_combo.currentText(),
            self._role_input.text().strip(),
            self._param_input.text().strip()
        )

    def _on_regenerate(self):
        """重新生成（触发父组件重新调用 AI）"""
        self.style_changed.emit(
            self._style_combo.currentText(),
            self._role_input.text().strip(),
            self._param_input.text().strip()
        )

    def get_current_style(self) -> str:
        return self._style_combo.currentText()

    def get_role(self) -> str:
        return self._role_input.text().strip()

    def get_custom_params(self) -> str:
        return self._param_input.text().strip()


# ── 预览文本区（带标签预览）────────────────────────────────
class PreviewTextArea(QFrame):
    """
    完整解说文案预览区
    显示所有分段，带标签装饰（开场/高潮/结尾等）
    """
    text_changed = Signal(str)  # 整个文案变更

    def __init__(self, parent=None):
        super().__init__(parent)
        self._segments = []  # list of (time_range, text, emotion)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {_T['bg_card']};
                border: 1px solid {_T['border']};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 头部
        header = QHBoxLayout()
        title = QLabel("解说文案预览")
        title.setFont(QFont("", 13, QFont.Weight.SemiBold))
        title.setStyleSheet(f"color: {_T['text']};")
        header.addWidget(title)

        self._word_count_label = QLabel("0 字")
        self._word_count_label.setStyleSheet(f"color: {_T['text_muted']}; font-size: 11px;")
        header.addWidget(self._word_count_label)
        header.addStretch()

        # 全量编辑开关
        self._bulk_edit_cb = QCheckBox("全量编辑")
        self._bulk_edit_cb.setStyleSheet(f"""
            QCheckBox {{
                color: {_T['text_sub']};
                font-size: 11px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 3px;
            }}
        """)
        self._bulk_edit_cb.toggled.connect(self._on_bulk_edit_toggled)
        header.addWidget(self._bulk_edit_cb)
        layout.addLayout(header)

        # 分段列表（可滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {_T['bg_input']};
                border-radius: 4px;
                width: 6px;
                margin: 2px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {_T['border_h']};
                border-radius: 3px;
            }}
        """)
        self._segments_container = QWidget()
        self._segments_layout = QVBoxLayout(self._segments_container)
        self._segments_layout.setSpacing(12)
        self._segments_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self._segments_container)
        layout.addWidget(scroll, stretch=1)

        # 全量编辑文本区（默认隐藏）
        self._bulk_text_edit = QTextEdit()
        self._bulk_text_edit.setFont(QFont("", 13))
        self._bulk_text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {_T['bg_input']};
                color: {_T['text']};
                border: 1px solid {_T['border']};
                border-radius: 8px;
                padding: 12px;
                line-height: 1.8;
            }}
            QTextEdit:focus {{ border-color: {_T['primary']}; }}
        """)
        self._bulk_text_edit.setVisible(False)
        self._bulk_text_edit.textChanged.connect(self._on_bulk_text_changed)
        layout.addWidget(self._bulk_text_edit, stretch=1)

        # ── 分段预览标签（段落摘要横条）────────────────────
        self._segment_tabs = QTabWidget()
        self._segment_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {_T['border']};
                border-radius: 8px;
                background: {_T['bg_input']};
            }}
            QTabBar::tab {{
                background: transparent;
                color: {_T['text_muted']};
                padding: 6px 14px;
                font-size: 11px;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {_T['primary']};
                border-bottom-color: {_T['primary']};
            }}
        """)
        self._segment_tabs.setVisible(False)
        layout.addWidget(self._segment_tabs)

    def load_segments(self, segments: list):
        """
        加载分段列表
        segments: [(time_range, text, emotion), ...]
        """
        self._segments = segments

        # 清空现有分段
        while self._segments_layout.count():
            item = self._segments_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加分段卡片
        for i, (t_range, text, emotion) in enumerate(segments):
            card = NarrationSegmentCard(i, t_range, text, emotion)
            card.content_changed.connect(self._on_segment_changed)
            self._segments_layout.addWidget(card)

        self._update_word_count()
        self._update_segment_tabs()

    def _on_segment_changed(self, text: str):
        self._update_word_count()

    def _on_bulk_edit_toggled(self, checked: bool):
        if checked:
            # 切换到全量编辑模式
            self._bulk_text_edit.setVisible(True)
            self._bulk_text_edit.setPlainText("\n\n".join(
                f"[{s[0]}] {s[1]}" for s in self._segments
            ))
            # 隐藏分段卡片
            self._segments_container.setVisible(False)
            self._segment_tabs.setVisible(False)
        else:
            self._bulk_text_edit.setVisible(False)
            self._segments_container.setVisible(True)
            self._segment_tabs.setVisible(False)

    def _on_bulk_text_changed(self):
        self._update_word_count()

    def _update_word_count(self):
        if self._bulk_edit_cb.isChecked():
            text = self._bulk_text_edit.toPlainText()
        else:
            text = "\n".join(s[1] for s in self._segments)
        count = len(text.replace(" ", "").replace("\n", ""))
        self._word_count_label.setText(f"{count} 字")

    def _update_segment_tabs(self):
        """更新段落摘要标签页"""
        self._segment_tabs.clear()
        for i, (t_range, text, emotion) in enumerate(self._segments):
            snippet = text[:60] + ("…" if len(text) > 60 else "")
            self._segment_tabs.addTab(QWidget(), f"[{t_range}] {snippet}")


# ── StepPreview 主组件 ─────────────────────────────────────
class StepPreview(QWidget):
    """
    解说预览 + 编辑页面
    整合：文案预览区 + 风格设置 + 分段编辑
    """
    back_requested = Signal()
    generate_requested = Signal(str, str, str, str)
    # back_requested: 返回上一步
    # generate_requested(style, role, params, full_text)

    def __init__(self, video_path: str = "", narration_text: str = "",
                 style: str = "治愈", parent=None):
        super().__init__(parent)
        self._video_path = video_path
        self._narration_text = narration_text
        self._current_style = style
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
        main_split.setStyleSheet(f"""
            QSplitter::handle {{
                background: transparent;
            }}
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
            ("00:40-00:55", "【转折】我抬头一看，竟然是多年未见的老朋友！", "tensed"),
            ("00:55-01:10", "【结尾】这个世界真小，缘分就是这么奇妙。", "nostalgic"),
        ]
        self._preview_area.load_segments(segments)

    def _on_style_changed(self, style: str, role: str, params: str):
        """风格改变时触发"""
        self._current_style = style
        # 可在此触发重新生成（debounce）

    def _on_save_draft(self):
        """保存草稿"""
        # TODO: 实现保存逻辑
        self._save_btn.setText("✅ 已保存")
        QTimer.singleShot(1500, lambda: self._save_btn.setText("💾 保存草稿"))

    def _on_export(self):
        """导出文案"""
        # TODO: 实现导出
        pass

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
        import threading
        t = threading.Thread(target=update, daemon=True)
        t.start()
