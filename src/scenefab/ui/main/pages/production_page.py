#!/usr/bin/env python3
"""Production workflow page."""

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
    header_panel,
    key_value_row,
    page_background_style,
    page_container,
    panel,
    scroll_area,
    section_title,
)


class ProductionPage(QFrame):
    """Structured workflow for first-person narration production."""

    start_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("production_page")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(page_background_style("production_page"))

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = scroll_area()
        container = page_container()
        layout = container.layout()

        layout.addWidget(self._build_header())

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)
        grid.addWidget(self._build_pipeline(), 0, 0, 2, 1)
        grid.addWidget(self._build_brief(), 0, 1)
        grid.addWidget(self._build_quality_gate(), 1, 1)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)
        layout.addLayout(grid)
        layout.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll)

    def _build_header(self) -> QFrame:
        start_btn = action_button("开始新流程", primary=True)
        start_btn.clicked.connect(self.start_requested.emit)
        return header_panel(
            "production_header",
            "创作流程",
            "素材导入、脚本、配音、字幕和竖屏导出集中处理",
            start_btn,
        )

    def _build_pipeline(self) -> QFrame:
        frame = panel("production_pipeline")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(section_title("流程队列"))

        steps = [
            ("01", "素材导入", "选择影视片段并记录来源"),
            ("02", "场景拆分", "识别人物、冲突和关键转折"),
            ("03", "脚本生成", "使用第一人称视角组织叙事"),
            ("04", "配音字幕", "完成音频、字幕与节奏校准"),
            ("05", "导出发布", "按竖屏平台参数生成成片"),
        ]
        for number, name, desc in steps:
            layout.addWidget(self._step_row(number, name, desc))
        layout.addStretch()
        return frame

    def _build_brief(self) -> QFrame:
        frame = panel("production_brief")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(section_title("脚本约束"))

        for label, value in [
            ("视角", "第一人称"),
            ("开头", "3 秒内给出冲突"),
            ("信息节奏", "6-10 秒推进一次"),
            ("结尾", "反转、悬念或后果"),
        ]:
            layout.addWidget(key_value_row(label, value))
        layout.addStretch()
        return frame

    def _build_quality_gate(self) -> QFrame:
        frame = panel("quality_gate")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(section_title("导出门禁"))

        checks = [
            "字幕不超过两行",
            "字幕与配音偏差小于 50ms",
            "首屏出现人物、冲突或结果预告",
            "成片默认 1080x1920",
        ]
        for item in checks:
            layout.addWidget(self._check_item(item))
        layout.addStretch()
        return frame

    def _step_row(self, number: str, name: str, desc: str) -> QFrame:
        row = QFrame()
        row.setObjectName("production_step_row")
        row.setStyleSheet(f"""
            QFrame#production_step_row {{
                background: {_C.BG_BASE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.base};
            }}
        """)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(12)

        badge = QLabel(number)
        badge.setFixedWidth(32)
        badge.setFont(QFont("", FontSizes.xs, QFont.Weight.Bold))
        badge.setStyleSheet(f"color: {_C.PRIMARY};")
        layout.addWidget(badge)

        copy = QVBoxLayout()
        copy.setSpacing(2)
        title = QLabel(name)
        title.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
        title.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        copy.addWidget(title)
        detail = QLabel(desc)
        detail.setFont(QFont("", FontSizes.xs))
        detail.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        copy.addWidget(detail)
        layout.addLayout(copy, 1)

        status = QLabel("待开始")
        status.setFont(QFont("", FontSizes.xs))
        status.setStyleSheet(f"color: {_C.TEXT_DISABLED};")
        layout.addWidget(status)
        return row

    def _check_item(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(QFont("", FontSizes.sm))
        label.setStyleSheet(f"""
            QLabel {{
                color: {_C.TEXT_SECONDARY};
                background: {_C.BG_BASE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
                padding: 8px 10px;
            }}
        """)
        return label
