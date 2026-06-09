#!/usr/bin/env python3
"""解说分段卡片组件

从 step_preview.py 提取 NarrationSegmentCard
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    "bg_card": "oklch(0.16 0.01 250)",
    "bg_input": "oklch(0.13 0.01 250)",
    "border": "oklch(0.24 0.01 250)",
    "primary": "oklch(0.65 0.20 250)",
    "text": "oklch(0.93 0.01 250)",
    "text_sub": "oklch(0.75 0.01 250)",
    "text_muted": "oklch(0.55 0.01 250)",
}


# ── 分段解说卡片 ────────────────────────────────────────────
class NarrationSegmentCard(QFrame):
    """
    单个解说分段卡片
    包含：时间段标签 + 文案预览/编辑 + 情感标记
    """

    content_changed = Signal(str)  # 发送编辑后的文案

    def __init__(
        self,
        segment_id: int,
        time_range: str,
        text: str,
        emotion: str = "neutral",
        parent=None,
    ):
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
                background: {_T["bg_card"]};
                border: 1px solid {_T["border"]};
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
        self._time_label.setFont(QFont("", 11, QFont.Weight.SemiBold))  # type: ignore[attr-defined]
        self._time_label.setStyleSheet(f"""
            color: {_T["primary"]};
            background: {_T["primary"]}20;
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
        self._text_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self._text_label)

        self._text_edit = QTextEdit()
        self._text_edit.setFont(QFont("", 13))
        self._text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {_T["bg_input"]};
                color: {_T["text"]};
                border: 1px solid {_T["border"]};
                border-radius: 8px;
                padding: 10px;
                line-height: 1.6;
            }}
            QTextEdit:focus {{
                border-color: {_T["primary"]};
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
                    background: {_T["primary"]};
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
                    color: {_T["text_sub"]};
                    border: 1px solid {_T["border"]};
                    border-radius: 8px;
                    padding: 6px 16px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    border-color: {_T["primary"]};
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
        """获取当前编辑后的文本"""
        return self._text

    def get_segment_id(self) -> int:
        return self._segment_id
