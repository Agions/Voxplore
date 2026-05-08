#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""风格预设面板组件

从 step_preview.py 提取 StylePresetPanel
"""

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QComboBox, QLineEdit)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont


# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    "bg_card":     "oklch(0.16 0.01 250)",
    "bg_input":    "oklch(0.13 0.01 250)",
    "bg_active":   "oklch(0.17 0.01 250)",
    "border":      "oklch(0.24 0.01 250)",
    "primary":     "oklch(0.65 0.20 250)",
    "text":        "oklch(0.93 0.01 250)",
    "text_sub":    "oklch(0.75 0.01 250)",
    "text_muted":  "oklch(0.55 0.01 250)",
}


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
