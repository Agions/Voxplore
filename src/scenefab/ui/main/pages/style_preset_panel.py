#!/usr/bin/env python3
"""风格预设面板组件

从 step_preview.py 提取 StylePresetPanel
"""

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

# ── OKLCH Design Tokens ──────────────────────────────────────
from scenefab.ui.theme.ds_tokens import _C


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

    # ── UI construction (decomposed) ─────────────────────────
    def _setup_ui(self):
        self._apply_frame_style()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        layout.addWidget(self._create_title())
        layout.addLayout(self._create_style_selector())
        layout.addWidget(self._create_style_description())
        layout.addWidget(self._create_separator())
        layout.addLayout(self._create_role_input())
        layout.addLayout(self._create_param_input())
        layout.addWidget(self._create_regen_button())
        layout.addStretch()

    def _apply_frame_style(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {_C.BG_SURFACE};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: 12px;
            }}
        """)

    def _create_title(self):
        title = QLabel("风格设置")
        title.setFont(QFont("", 12, QFont.Weight.SemiBold))  # type: ignore[attr-defined]
        title.setStyleSheet(f"color: {_C.TEXT_SECONDARY};")
        return title

    def _create_style_selector(self):
        style_row = QHBoxLayout()
        style_lbl = QLabel("解说风格")
        style_lbl.setStyleSheet(f"color: {_C.TEXT_MUTED}; font-size: 12px;")
        style_row.addWidget(style_lbl)

        self._style_combo = QComboBox()
        self._style_combo.addItems(list(self.PRESET_STYLES.keys()))
        self._style_combo.currentTextChanged.connect(self._on_style_changed)
        self._style_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {_C.BG_INPUT};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {_C.BG_SURFACE};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: 8px;
                selection-background-color: {_C.BG_ELEVATED};
            }}
        """)
        style_row.addWidget(self._style_combo, stretch=1)
        return style_row

    def _create_style_description(self):
        self._style_desc = QLabel(self.PRESET_STYLES["治愈"])
        self._style_desc.setStyleSheet(f"color: {_C.TEXT_MUTED}; font-size: 11px;")
        self._style_desc.setWordWrap(True)
        return self._style_desc

    def _create_separator(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {_C.BORDER_DEFAULT}; max-height: 1px;")
        return sep

    def _create_role_input(self):
        role_row = QHBoxLayout()
        role_lbl = QLabel("主角名称")
        role_lbl.setStyleSheet(f"color: {_C.TEXT_MUTED}; font-size: 12px;")
        role_row.addWidget(role_lbl)

        self._role_input = QLineEdit()
        self._role_input.setPlaceholderText("默认为「我」")
        self._role_input.setStyleSheet(f"""
            QLineEdit {{
                background: {_C.BG_INPUT};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {_C.PRIMARY}; }}
            QLineEdit::placeholder {{ color: {_C.TEXT_MUTED}; }}
        """)
        self._role_input.textChanged.connect(self._emit_change)
        role_row.addWidget(self._role_input, stretch=1)
        return role_row

    def _create_param_input(self):
        param_row = QHBoxLayout()
        param_lbl = QLabel("角色参数")
        param_lbl.setStyleSheet(f"color: {_C.TEXT_MUTED}; font-size: 12px;")
        param_row.addWidget(param_lbl)

        self._param_input = QLineEdit()
        self._param_input.setPlaceholderText("如：年龄30、性格内向…")
        self._param_input.setStyleSheet(f"""
            QLineEdit {{
                background: {_C.BG_INPUT};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {_C.PRIMARY}; }}
            QLineEdit::placeholder {{ color: {_C.TEXT_MUTED}; }}
        """)
        self._param_input.textChanged.connect(self._emit_change)
        param_row.addWidget(self._param_input, stretch=1)
        return param_row

    def _create_regen_button(self):
        self._regen_btn = QPushButton("⟳ 重新生成")
        self._regen_btn.setObjectName("secondary_btn")
        self._regen_btn.setFixedHeight(34)
        self._regen_btn.clicked.connect(self._on_regenerate)
        return self._regen_btn

    def _on_style_changed(self, text: str):
        self._style_desc.setText(self.PRESET_STYLES.get(text, ""))
        self._emit_change()

    def _emit_change(self):
        self.style_changed.emit(
            self._style_combo.currentText(),
            self._role_input.text().strip(),
            self._param_input.text().strip(),
        )

    def _on_regenerate(self):
        """重新生成（触发父组件重新调用 AI）"""
        self.style_changed.emit(
            self._style_combo.currentText(),
            self._role_input.text().strip(),
            self._param_input.text().strip(),
        )

    def get_current_style(self) -> str:
        return self._style_combo.currentText()

    def get_role(self) -> str:
        return self._role_input.text().strip()

    def get_custom_params(self) -> str:
        return self._param_input.text().strip()
