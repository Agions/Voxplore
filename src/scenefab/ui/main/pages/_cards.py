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
    QVBoxLayout,
)

from ...theme.ds_tokens import Colors, FontSizes, Radii

# ═══════════════════════════════════════════════════════════════════════
# 玻璃态卡片
# ═══════════════════════════════════════════════════════════════════════


class GlassCard(QFrame):
    """带微妙玻璃模糊效果的卡片"""

    clicked = Signal(str)

    def __init__(self, card_id: str, parent=None):
        super().__init__(parent)
        self._card_id = card_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName(f"glass_card_{card_id}")
        self._hovered = False
        self._setup_style()

    def _setup_style(self):
        self.setStyleSheet(f"""
            QFrame#glass_card_{self._card_id} {{
                background: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: {Radii.xl};
            }}
        """)

    def enterEvent(self, event):
        self._hovered = True
        self.setStyleSheet(f"""
            QFrame#glass_card_{self._card_id} {{
                background: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.PRIMARY_10.replace("1A", "33")};
                border-radius: {Radii.xl};
            }}
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._setup_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._card_id)


# ═══════════════════════════════════════════════════════════════════════
# 快捷操作卡片
# ═══════════════════════════════════════════════════════════════════════


class QuickCard(GlassCard):
    """快捷操作卡片"""

    def __init__(
        self,
        card_id: str,
        icon: str,
        title: str,
        desc: str,
        accent: str = Colors.PRIMARY,
        parent=None,
    ):
        super().__init__(card_id, parent)
        self._icon = icon
        self._title = title
        self._desc = desc
        self._accent = accent
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 顶部：图标 + 装饰圆点
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        icon_frame = QFrame()
        icon_frame.setFixedSize(48, 48)
        icon_frame.setStyleSheet(f"""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 {self._accent}33,
                stop:1 {self._accent}11
            );
            border-radius: {Radii.lg};
        """)
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl = QLabel(self._icon)
        icon_lbl.setFont(QFont("", 22))
        icon_lbl.setStyleSheet(f"color: {self._accent};")
        icon_layout.addWidget(icon_lbl)
        top_layout.addWidget(icon_frame)
        top_layout.addStretch()

        # 装饰点
        dot = QLabel("●")
        dot.setFont(QFont("", 8))
        dot.setStyleSheet(f"color: {self._accent}; opacity: 0.4;")
        top_layout.addWidget(dot)

        layout.addLayout(top_layout)

        # 标题
        title_lbl = QLabel(self._title)
        title_lbl.setFont(QFont("", FontSizes.md, QFont.Weight.SemiBold))
        title_lbl.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title_lbl)

        # 描述
        desc_lbl = QLabel(self._desc)
        desc_lbl.setFont(QFont("", FontSizes.xs))
        desc_lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        desc_lbl.setWordWrap(True)
        desc_lbl.setMinimumHeight(36)
        layout.addWidget(desc_lbl, 1)

        # 底部箭头
        arrow_layout = QHBoxLayout()
        arrow_layout.addStretch()
        arrow = QLabel("→")
        arrow.setFont(QFont("", 14))
        arrow.setStyleSheet(f"color: {Colors.TEXT_DISABLED};")
        arrow_layout.addWidget(arrow)
        layout.addLayout(arrow_layout)


# ═══════════════════════════════════════════════════════════════════════
# 项目卡片
# ═══════════════════════════════════════════════════════════════════════


class ProjectCard(GlassCard):
    """项目卡片"""

    def __init__(
        self,
        project_id: str,
        name: str,
        thumbnail: str = "",
        duration: str = "",
        date: str = "",
        parent=None,
    ):
        super().__init__(f"proj_{project_id}", parent)
        self._project_id = project_id
        self._name = name
        self._duration = duration
        self._date = date
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 缩略图
        thumb = QFrame()
        thumb.setFixedHeight(130)
        thumb.setStyleSheet(f"""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 {Colors.BG_ELEVATED},
                stop:1 {Colors.BG_OVERLAY}
            );
            border-top-left-radius: {Radii.xl};
            border-top-right-radius: {Radii.xl};
        """)
        thumb_layout = QVBoxLayout(thumb)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        thumb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 图标/缩略图
        icon_lbl = QLabel("🎬")
        icon_lbl.setFont(QFont("", 36))
        icon_lbl.setStyleSheet(f"color: {Colors.BORDER_STRONG};")
        thumb_layout.addWidget(icon_lbl)
        layout.addWidget(thumb)

        # 信息区
        info = QFrame()
        info.setStyleSheet(f"""
            border-top: 1px solid {Colors.BORDER_SUBTLE};
            border-bottom-left-radius: {Radii.xl};
            border-bottom-right-radius: {Radii.xl};
        """)
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(14, 10, 14, 10)
        info_layout.setSpacing(4)

        name_lbl = QLabel(self._name)
        name_lbl.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
        name_lbl.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        name_lbl.setElideMode(Qt.TextElideMode.ElideRight)
        info_layout.addWidget(name_lbl)

        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(8)

        if self._duration:
            dur_lbl = QLabel(self._duration)
            dur_lbl.setFont(QFont("", FontSizes.xs))
            dur_lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
            meta_layout.addWidget(dur_lbl)

        if self._date:
            date_lbl = QLabel(self._date)
            date_lbl.setFont(QFont("", FontSizes.xs))
            date_lbl.setStyleSheet(f"color: {Colors.TEXT_DISABLED};")
            meta_layout.addWidget(date_lbl)

        meta_layout.addStretch()
        info_layout.addLayout(meta_layout)

        layout.addWidget(info)


# ═══════════════════════════════════════════════════════════════════════
# 统计数字卡
# ═══════════════════════════════════════════════════════════════════════


class StatChip(QFrame):
    """小型统计卡片"""

    def __init__(self, value: str, label: str, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("stat_chip")
        self.setStyleSheet(f"""
            QFrame#stat_chip {{
                background: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: {Radii.lg};
            }}
        """)
        self._setup_ui(value, label, color)

    def _setup_ui(self, value: str, label: str, color: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        val_lbl = QLabel(value)
        val_lbl.setFont(QFont("", FontSizes.xl, QFont.Weight.Bold))
        val_lbl.setStyleSheet(f"color: {color};")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(val_lbl)

        lbl = QLabel(label)
        lbl.setFont(QFont("", FontSizes.xs))
        lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)


# ═══════════════════════════════════════════════════════════════════════
# 首页
# ═══════════════════════════════════════════════════════════════════════
