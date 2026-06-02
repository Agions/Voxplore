#!/usr/bin/env python3
"""
SceneFab 首页 v6 — 沉浸式创作中心
设计特点:
  - 全屏背景渐变+微妙光晕
  - 快捷操作大卡片网格
  - 最近项目瀑布流
  - 底部数据统计条
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...theme.ds_tokens import Colors, FontSizes, FontWeights, Radii

# ═══════════════════════════════════════════════════════════════════════
# 玻璃态卡片
# ═══════════════════════════════════════════════════════════════════════



class EmptyStateCard(QFrame):
    """空状态卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("empty_state")
        self.setFixedSize(240, 200)
        self.setStyleSheet(f"""
            QFrame#empty_state {{
                background: {Colors.BG_SURFACE};
                border: 2px dashed {Colors.BORDER_DEFAULT};
                border-radius: {Radii.xl};
            }}
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        icon = QLabel("📂")
        icon.setFont(QFont("", 36))
        icon.setStyleSheet(f"color: {Colors.BORDER_STRONG};")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        title = QLabel("暂无项目")
        title.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
        title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("点击上方「新建项目」\n开始你的创作之旅")
        desc.setFont(QFont("", FontSizes.xs))
        desc.setStyleSheet(f"color: {Colors.TEXT_DISABLED};")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

