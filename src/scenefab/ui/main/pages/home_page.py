#!/usr/bin/env python3
"""Main production workspace page."""

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from ...theme.ds_tokens import _C, FontSizes, Radii
from .page_widgets import (
    action_button,
    empty_state,
    header_panel,
    key_value_row,
    page_background_style,
    page_container,
    panel,
    scroll_area,
    section_title,
)


class HomePage(QFrame):
    """Production dashboard for first-person narration work."""

    create_project = Signal()
    open_project = Signal(str)
    navigate = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("home_page")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(page_background_style("home_page"))

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = scroll_area()
        container = page_container()
        layout = container.layout()

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_status_grid())

        main_grid = QGridLayout()
        main_grid.setHorizontalSpacing(18)
        main_grid.setVerticalSpacing(18)
        main_grid.addWidget(self._build_workflow_panel(), 0, 0, 2, 1)
        main_grid.addWidget(self._build_delivery_panel(), 0, 1)
        main_grid.addWidget(self._build_recent_panel(), 1, 1)
        main_grid.setColumnStretch(0, 3)
        main_grid.setColumnStretch(1, 2)
        layout.addLayout(main_grid)
        layout.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll)

    def _build_header(self) -> QFrame:
        create_btn = action_button("开始生产", primary=True)
        create_btn.clicked.connect(self.create_project.emit)

        assets_btn = action_button("项目资产")
        assets_btn.clicked.connect(lambda: self.navigate.emit("assets"))
        return header_panel(
            "workspace_header",
            "第一人称短剧解说工作台",
            "竖屏 1080x1920 · 30 fps · H.264 · 8000k",
            create_btn,
            assets_btn,
        )

    def _build_status_grid(self) -> QFrame:
        frame = QFrame()
        layout = QGridLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(14)

        items = [
            ("素材", "未导入", "0"),
            ("场景", "未拆分", "0"),
            ("脚本", "待生成", "--"),
            ("导出", "待配置", "1080x1920"),
        ]
        for index, (title, status, value) in enumerate(items):
            layout.addWidget(self._status_card(title, status, value), 0, index)
        return frame

    def _build_workflow_panel(self) -> QFrame:
        frame = panel("workflow_panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        layout.addWidget(section_title("生产流程"))
        rows = [
            ("01", "素材采集", "未开始"),
            ("02", "场景拆分", "未开始"),
            ("03", "第一人称脚本", "未开始"),
            ("04", "配音与字幕", "未开始"),
            ("05", "竖屏导出", "未开始"),
        ]
        for step, name, status in rows:
            layout.addWidget(self._workflow_row(step, name, status))
        layout.addStretch()
        return frame

    def _build_delivery_panel(self) -> QFrame:
        frame = panel("delivery_panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        layout.addWidget(section_title("交付参数"))
        for label, value in [
            ("画布", "1080x1920"),
            ("视频码率", "8000k"),
            ("音频码率", "192k"),
            ("平台", "Shorts / TikTok / Reels"),
        ]:
            layout.addWidget(key_value_row(label, value))
        layout.addStretch()
        return frame

    def _build_recent_panel(self) -> QFrame:
        frame = panel("recent_panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        row = QHBoxLayout()
        row.addWidget(section_title("最近资产"))
        row.addStretch()
        open_btn = action_button("打开")
        open_btn.clicked.connect(lambda: self.navigate.emit("assets"))
        row.addWidget(open_btn)
        layout.addLayout(row)

        layout.addWidget(empty_state("暂无项目资产", 120), 1)
        return frame

    def _status_card(self, title: str, status: str, value: str) -> QFrame:
        card = panel(f"status_{title}")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        label = QLabel(title)
        label.setFont(QFont("", FontSizes.xs, QFont.Weight.Medium))
        label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        layout.addWidget(label)

        val = QLabel(value)
        val.setFont(QFont("", FontSizes.lg, QFont.Weight.Bold))
        val.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        layout.addWidget(val)

        state = QLabel(status)
        state.setFont(QFont("", FontSizes.xs))
        state.setStyleSheet(f"color: {_C.TEXT_DISABLED};")
        layout.addWidget(state)
        return card

    def _workflow_row(self, step: str, name: str, status: str) -> QFrame:
        row = QFrame()
        row.setObjectName("workflow_row")
        row.setStyleSheet(f"""
            QFrame#workflow_row {{
                background: {_C.BG_BASE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.base};
            }}
        """)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        step_label = QLabel(step)
        step_label.setFixedWidth(32)
        step_label.setFont(QFont("", FontSizes.xs, QFont.Weight.Bold))
        step_label.setStyleSheet(f"color: {_C.PRIMARY};")
        layout.addWidget(step_label)

        name_label = QLabel(name)
        name_label.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
        name_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        layout.addWidget(name_label, 1)

        status_label = QLabel(status)
        status_label.setFont(QFont("", FontSizes.xs))
        status_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        layout.addWidget(status_label)
        return row
