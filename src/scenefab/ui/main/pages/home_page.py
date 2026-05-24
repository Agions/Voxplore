#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SceneFab 首页 v6 — 沉浸式创作中心
设计特点:
  - 全屏背景渐变+微妙光晕
  - 快捷操作大卡片网格
  - 最近项目瀑布流
  - 底部数据统计条
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QPainter, QLinearGradient, QColor

from ...theme.ds_tokens import Colors, FontSizes, FontWeights, Spacing, Radii, Shadows


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
                border: 1px solid {Colors.PRIMARY_10.replace('1A', '33')};
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

    def __init__(self, card_id: str, icon: str, title: str, desc: str,
                 accent: str = Colors.PRIMARY, parent=None):
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

    def __init__(self, project_id: str, name: str, thumbnail: str = "",
                 duration: str = "", date: str = "", parent=None):
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

class HomePage(QFrame):
    """首页"""

    create_project = Signal()
    open_project = Signal(str)
    navigate = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("home_page")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #home_page {{
                background: {Colors.BG_BASE};
            }}
        """)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("home_container")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(40, 32, 40, 24)
        container_layout.setSpacing(32)

        # ══ 欢迎区 ══════════════════════════════════════════════
        welcome = self._build_welcome()
        container_layout.addWidget(welcome)

        # ══ 快捷操作 ══════════════════════════════════════════
        quick = self._build_quick_actions()
        container_layout.addWidget(quick)

        # ══ 最近项目 ════════════════════════════════════════
        recent = self._build_recent_section()
        container_layout.addWidget(recent)

        # ══ 统计条 ══════════════════════════════════════════
        stats = self._build_stats_bar()
        container_layout.addWidget(stats)

        container_layout.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll)

    def _build_welcome(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("welcome_frame")
        layout = QVBoxLayout(frame)
        layout.setSpacing(6)

        greeting = QLabel("你好，创作人 👋")
        greeting.setFont(QFont("", FontSizes.xxl, QFont.Weight.Bold))
        greeting.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")

        sub = QLabel("今天想创作什么？")
        sub.setFont(QFont("", FontSizes.md))
        sub.setStyleSheet(f"color: {Colors.TEXT_MUTED};")

        layout.addWidget(greeting)
        layout.addWidget(sub)
        return frame

    def _build_quick_actions(self) -> QFrame:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setSpacing(16)

        # 标题行
        title_row = QHBoxLayout()
        title = QLabel("快捷操作")
        title.setFont(QFont("", FontSizes.md, QFont.Weight.SemiBold))
        title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        title_row.addWidget(title)

        title_row.addStretch()

        see_all = QPushButton("查看全部 →")
        see_all.setObjectName("link_btn")
        see_all.setStyleSheet(f"""
            QPushButton#link_btn {{
                background: transparent;
                color: {Colors.PRIMARY};
                border: none;
                font-size: {FontSizes.sm};
            }}
            QPushButton#link_btn:hover {{
                color: {Colors.PRIMARY_LIGHT};
            }}
        """)
        see_all.clicked.connect(lambda: self.navigate.emit("projects"))
        title_row.addWidget(see_all)
        layout.addLayout(title_row)

        # 卡片网格
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        actions = [
            ("new",      "＋", "新建项目",     "从零开始创作视频",     Colors.PRIMARY),
            ("template", "📋", "使用模板",      "从模板快速创建",      Colors.ACCENT),
            ("import",   "📁", "导入素材",      "使用本地视频文件",     Colors.INFO),
            ("ai",       "✨", "AI 助手",       "智能创作建议与优化",   Colors.WARNING),
        ]
        for _id, icon, title, desc, accent in actions:
            card = QuickCard(_id, icon, title, desc, accent)
            card.setFixedSize(180, 170)
            card.clicked.connect(self._on_quick_action)
            cards_layout.addWidget(card)

        cards_layout.addStretch()
        layout.addLayout(cards_layout)

        return frame

    def _build_recent_section(self) -> QFrame:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setSpacing(16)

        # 标题行
        title_row = QHBoxLayout()
        title = QLabel("最近项目")
        title.setFont(QFont("", FontSizes.md, QFont.Weight.SemiBold))
        title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        title_row.addWidget(title)

        title_row.addStretch()

        new_btn = QPushButton("＋ 新建项目")
        new_btn.setObjectName("btn_new_project")
        new_btn.setStyleSheet(f"""
            QPushButton#btn_new_project {{
                background: {Colors.PRIMARY_DARK};
                color: white;
                border: none;
                border-radius: {Radii.base};
                font-size: {FontSizes.xs};
                font-weight: {FontWeights.Medium};
                padding: 6px 14px;
            }}
            QPushButton#btn_new_project:hover {{
                background: {Colors.PRIMARY};
            }}
        """)
        new_btn.clicked.connect(self.create_project.emit)
        title_row.addWidget(new_btn)
        layout.addLayout(title_row)

        # 项目网格（空状态）
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(16)

        empty = EmptyStateCard()
        grid_layout.addWidget(empty)

        grid_layout.addStretch()
        layout.addLayout(grid_layout)

        return frame

    def _build_stats_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("stats_bar")
        frame.setStyleSheet(f"""
            QFrame#stats_bar {{
                background: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: {Radii.xl};
            }}
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(32)

        stats = [
            ("12",    "总项目数",   Colors.PRIMARY),
            ("48",    "视频总数",   Colors.ACCENT),
            ("2.3GB", "存储使用",   Colors.WARNING),
            ("99%",   "成功率",     Colors.SUCCESS),
            ("v2.0",  "当前版本",   Colors.INFO),
        ]
        for val, lbl, color in stats:
            chip = StatChip(val, lbl, color)
            layout.addWidget(chip)

        layout.addStretch()

        # 升级提示
        pro_frame = QFrame()
        pro_frame.setStyleSheet(f"""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {Colors.PRIMARY}15,
                stop:1 transparent
            );
            border-radius: {Radii.lg};
            border-left: 3px solid {Colors.PRIMARY};
        """)
        pro_layout = QVBoxLayout(pro_frame)
        pro_layout.setContentsMargins(12, 8, 12, 8)
        pro_layout.setSpacing(2)

        pro_title = QLabel("升级至 Pro")
        pro_title.setFont(QFont("", FontSizes.xs, QFont.Weight.SemiBold))
        pro_title.setStyleSheet(f"color: {Colors.PRIMARY};")
        pro_layout.addWidget(pro_title)

        pro_desc = QLabel("解锁全部高级功能")
        pro_desc.setFont(QFont("", FontSizes.xs))
        pro_desc.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        pro_layout.addWidget(pro_desc)

        layout.addWidget(pro_frame)

        return frame

    def _on_quick_action(self, action_id: str):
        if action_id == "new":
            self.create_project.emit()
        elif action_id == "template" or action_id == "import" or action_id == "ai":
            self.navigate.emit("create")


# ═══════════════════════════════════════════════════════════════════════
# 空状态卡片
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
