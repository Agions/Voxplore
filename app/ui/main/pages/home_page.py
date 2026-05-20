#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voxplore 首页 — 简洁现代布局
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QPainter, QColor, QLinearGradient

from app.ui.theme.ds_tokens import Colors, FontSizes, FontWeights, Spacing, Radii, Shadows


# ═══════════════════════════════════════════════════════════════
# 快捷操作卡片
# ═══════════════════════════════════════════════════════════════

class QuickActionCard(QFrame):
    """快捷操作卡片"""

    clicked = Signal(str)

    def __init__(self, action_id: str, icon: str, title: str, desc: str, parent=None):
        super().__init__(parent)
        self._action_id = action_id
        self.setFixedSize(200, 140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("quick_card")
        self._setup_style()
        self._setup_ui(icon, title, desc)

    def _setup_style(self):
        self.setStyleSheet(f"""
            #quick_card {{
                background: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: {Radii.lg};
            }}
            #quick_card:hover {{
                background: {Colors.BG_ELEVATED};
                border-color: {Colors.PRIMARY_500};
            }}
        """)

    def _setup_ui(self, icon: str, title: str, desc: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 图标
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("", 28))
        icon_label.setStyleSheet(f"color: {Colors.PRIMARY_400};")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(icon_label)

        # 标题
        title_label = QLabel(title)
        title_label.setFont(QFont("", FontSizes.md, QFont.Weight.Semibold))
        title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title_label)

        # 描述
        desc_label = QLabel(desc)
        desc_label.setFont(QFont("", FontSizes.xs))
        desc_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._action_id)


# ═══════════════════════════════════════════════════════════════
# 项目卡片
# ═══════════════════════════════════════════════════════════════

class ProjectCard(QFrame):
    """最近项目卡片"""

    clicked = Signal(str)

    def __init__(self, project_id: str, name: str, thumbnail: str, date: str, parent=None):
        super().__init__(parent)
        self._project_id = project_id
        self.setFixedSize(220, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("project_card")
        self._setup_style()
        self._setup_ui(name, thumbnail, date)

    def _setup_style(self):
        self.setStyleSheet(f"""
            #project_card {{
                background: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: {Radii.lg};
            }}
            #project_card:hover {{
                border-color: {Colors.PRIMARY_500};
            }}
        """)

    def _setup_ui(self, name: str, thumbnail: str, date: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 缩略图区
        thumb = QFrame()
        thumb.setFixedHeight(120)
        thumb.setStyleSheet(f"""
            background: {Colors.BG_ELEVATED};
            border-top-left-radius: {Radii.lg};
            border-top-right-radius: {Radii.lg};
        """)
        thumb_layout = QVBoxLayout(thumb)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        placeholder = QLabel("🎬")
        placeholder.setFont(QFont("", 32))
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_layout.addWidget(placeholder)
        layout.addWidget(thumb)

        # 信息区
        info = QFrame()
        info.setStyleSheet(f"border-top: 1px solid {Colors.BORDER_SUBTLE};")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(12, 8, 12, 8)
        info_layout.setSpacing(2)

        name_label = QLabel(name)
        name_label.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
        name_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        name_label.setElideMode(Qt.TextElideMode.ElideRight)
        info_layout.addWidget(name_label)

        date_label = QLabel(date)
        date_label.setFont(QFont("", FontSizes.xs))
        date_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        info_layout.addWidget(date_label)

        layout.addWidget(info)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._project_id)


# ═══════════════════════════════════════════════════════════════
# 统计卡片
# ═══════════════════════════════════════════════════════════════

class StatCard(QFrame):
    """统计卡片"""

    def __init__(self, value: str, label: str, icon: str, color: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setObjectName("stat_card")
        self._setup_style(color)
        self._setup_ui(value, label, icon)

    def _setup_style(self, color: str):
        self.setStyleSheet(f"""
            #stat_card {{
                background: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-left: 3px solid {color};
                border-radius: {Radii.base};
            }}
        """)

    def _setup_ui(self, value: str, label: str, icon: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        # 图标
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("", 24))
        icon_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        icon_label.setFixedWidth(40)
        layout.addWidget(icon_label)

        # 数值+标签
        val_layout = QVBoxLayout()
        val_layout.setSpacing(2)

        val = QLabel(value)
        val.setFont(QFont("", FontSizes.xl, QFont.Weight.Bold))
        val.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        val_layout.addWidget(val)

        lbl = QLabel(label)
        lbl.setFont(QFont("", FontSizes.xs))
        lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        val_layout.addWidget(lbl)

        layout.addLayout(val_layout)
        layout.addStretch()


# ═══════════════════════════════════════════════════════════════
# 首页
# ═══════════════════════════════════════════════════════════════

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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(32, 32, 32, 32)
        container_layout.setSpacing(32)

        # ── 欢迎区 ──────────────────────────────────
        welcome = self._build_welcome_section()
        container_layout.addWidget(welcome)

        # ── 快捷操作 ─────────────────────────────────
        quick_section = self._build_quick_section()
        container_layout.addWidget(quick_section)

        # ── 最近项目 ─────────────────────────────────
        recent_section = self._build_recent_section()
        container_layout.addWidget(recent_section)

        # ── 统计数据 ─────────────────────────────────
        stats_section = self._build_stats_section()
        container_layout.addWidget(stats_section)

        container_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _build_welcome_section(self) -> QFrame:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)

        greeting = QLabel("欢迎使用 Voxplore")
        greeting.setFont(QFont("", FontSizes.xxxl, QFont.Weight.Bold))
        greeting.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(greeting)

        subtitle = QLabel("智能视频创作平台，让创意更简单")
        subtitle.setFont(QFont("", FontSizes.md))
        subtitle.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        layout.addWidget(subtitle)

        return frame

    def _build_quick_section(self) -> QFrame:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setSpacing(16)

        # 标题行
        title_row = QHBoxLayout()
        title = QLabel("快捷操作")
        title.setFont(QFont("", FontSizes.lg, QFont.Weight.Semibold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        title_row.addWidget(title)
        title_row.addStretch()
        layout.addLayout(title_row)

        # 卡片网格
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        actions = [
            ("new",      "＋", "新建项目",     "创建新视频项目"),
            ("template", "📋", "使用模板",     "从模板快速开始"),
            ("import",   "📁", "导入素材",     "导入本地视频文件"),
            ("ai",       "✨", "AI 助手",      "智能创作建议"),
        ]
        for _id, icon, title, desc in actions:
            card = QuickActionCard(_id, icon, title, desc)
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
        title.setFont(QFont("", FontSizes.lg, QFont.Weight.Semibold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        title_row.addWidget(title)

        view_all = QPushButton("查看全部")
        view_all.setObjectName("text_btn")
        view_all.setStyleSheet(f"""
            QPushButton#text_btn {{
                background: transparent;
                color: {Colors.PRIMARY_400};
                border: none;
                font-size: {FontSizes.sm};
            }}
            QPushButton#text_btn:hover {{
                color: {Colors.PRIMARY_300};
            }}
        """)
        view_all.clicked.connect(lambda: self.navigate.emit("projects"))
        title_row.addWidget(view_all)
        layout.addLayout(title_row)

        # 项目列表
        projects_layout = QHBoxLayout()
        projects_layout.setSpacing(16)

        # 空状态
        empty = QFrame()
        empty.setFixedHeight(120)
        empty.setStyleSheet(f"""
            background: {Colors.BG_SURFACE};
            border: 2px dashed {Colors.BORDER_SUBTLE};
            border-radius: {Radii.lg};
        """)
        empty_layout = QVBoxLayout(empty)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_icon = QLabel("📂")
        empty_icon.setFont(QFont("", 24))
        empty_layout.addWidget(empty_icon)
        empty_text = QLabel("暂无项目，点击上方「新建项目」开始创作")
        empty_text.setFont(QFont("", FontSizes.sm))
        empty_text.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        empty_layout.addWidget(empty_text)
        projects_layout.addWidget(empty)

        projects_layout.addStretch()
        layout.addLayout(projects_layout)

        return frame

    def _build_stats_section(self) -> QFrame:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setSpacing(16)

        title = QLabel("数据统计")
        title.setFont(QFont("", FontSizes.lg, QFont.Weight.Semibold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(title)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        stats = [
            ("12",   "总项目数",    "📁", Colors.PRIMARY_500),
            ("48",   "视频总数",    "🎬", Colors.ACCENT_500),
            ("2.3GB", "占用空间",   "💾", Colors.WARNING),
            ("99%",  "成功率",     "✓",  Colors.SUCCESS),
        ]
        for val, lbl, icon, color in stats:
            card = StatCard(val, lbl, icon, color)
            stats_layout.addWidget(card)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        return frame

    def _on_quick_action(self, action_id: str):
        if action_id == "new":
            self.create_project.emit()
        elif action_id == "template":
            self.navigate.emit("create")
        elif action_id == "import":
            self.navigate.emit("create")
        elif action_id == "ai":
            self.navigate.emit("create")
