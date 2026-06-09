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

# ═══════════════════════════════════════════════════════════════════════
# 玻璃态卡片
# ═══════════════════════════════════════════════════════════════════════
from scenefab.ui.main.pages._cards import QuickCard, StatChip
from scenefab.ui.main.pages._empty_state import EmptyStateCard

from ...theme.ds_tokens import Colors, FontSizes, FontWeights, Radii


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
            ("new", "＋", "新建项目", "从零开始创作视频", Colors.PRIMARY),
            ("template", "📋", "使用模板", "从模板快速创建", Colors.ACCENT),
            ("import", "📁", "导入素材", "使用本地视频文件", Colors.INFO),
            ("ai", "✨", "AI 助手", "智能创作建议与优化", Colors.WARNING),
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
            ("12", "总项目数", Colors.PRIMARY),
            ("48", "视频总数", Colors.ACCENT),
            ("2.3GB", "存储使用", Colors.WARNING),
            ("99%", "成功率", Colors.SUCCESS),
            ("v2.0", "当前版本", Colors.INFO),
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
