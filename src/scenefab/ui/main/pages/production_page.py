#!/usr/bin/env python3
"""Production workflow page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, ui_font
from .page_view_models import (
    EXPORT_QUALITY_CHECKS,
    SCRIPT_BRIEF_RULES,
)
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

if TYPE_CHECKING:
    from ...viewmodels.production_viewmodel import ProductionPageViewModel


class ProductionPage(QFrame):
    """Structured workflow for first-person narration production.

    Phase 2B: 5-step pipeline + per-step status are read from
    :class:`ProductionPageViewModel`. The view renders them declaratively
    and forwards ``start_requested`` clicks to ``vm.start_pipeline()``.
    """

    start_requested = Signal()
    cancel_requested = Signal()

    def __init__(self, viewmodel: ProductionPageViewModel | None = None, parent=None):
        super().__init__(parent)
        self._vm = viewmodel
        self.setObjectName("production_page")
        self._step_statuses: dict[str, QLabel] = {}
        self._setup_style()
        self._setup_ui()
        if self._vm is not None:
            self._bind_viewmodel()

    def _setup_style(self):
        self.setStyleSheet(page_background_style("production_page"))

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = scroll_area()
        container = page_container()
        layout = container.layout()
        assert layout is not None  # for type checker

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
        self._start_btn = action_button("开始新流程", primary=True)
        self._start_btn.clicked.connect(self.start_requested.emit)

        self._cancel_btn = action_button("取消")
        self._cancel_btn.clicked.connect(self.cancel_requested.emit)
        self._cancel_btn.hide()

        return header_panel(
            "production_header",
            "创作流程",
            "素材导入、脚本、配音、字幕和竖屏导出集中处理",
            self._start_btn,
            self._cancel_btn,
        )

    def _build_pipeline(self) -> QFrame:
        frame = panel("production_pipeline")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(section_title("流程队列"))

        # Phase 2B: read 5 steps from VM (falls back to canon if no VM)
        steps = self._step_definitions()
        self._step_rows: list[tuple[QFrame, QLabel | None, QLabel | None, QLabel | None, str, str]] = []
        for number, name, desc in steps:
            row = self._step_row(number, name, desc)
            layout.addWidget(row)
            badge = row.findChild(QLabel, "step_badge")
            title = row.findChild(QLabel, "step_title")
            status_lbl = row.findChild(QLabel, "step_status")
            self._step_rows.append((row, badge, title, status_lbl, number, name))
        layout.addStretch()
        return frame

    def _step_definitions(self) -> list[tuple[str, str, str]]:
        if self._vm is not None:
            return self._vm.step_definitions
        from ...viewmodels.production_viewmodel import STEP_DEFINITIONS
        return STEP_DEFINITIONS

    def _build_brief(self) -> QFrame:
        frame = panel("production_brief")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(section_title("脚本约束"))

        for rule in SCRIPT_BRIEF_RULES:
            layout.addWidget(key_value_row(rule.label, rule.value))
        layout.addStretch()
        return frame

    def _build_quality_gate(self) -> QFrame:
        frame = panel("quality_gate")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        layout.addWidget(section_title("导出门禁"))

        for item in EXPORT_QUALITY_CHECKS:
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
        badge.setObjectName("step_badge")
        badge.setFixedWidth(32)
        badge.setFont(ui_font(FontSizes.xs, FontWeights.Bold))
        badge.setStyleSheet(f"color: {_C.PRIMARY};")
        layout.addWidget(badge)

        copy = QVBoxLayout()
        copy.setSpacing(2)
        title = QLabel(name)
        title.setObjectName("step_title")
        title.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        title.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        copy.addWidget(title)
        detail = QLabel(desc)
        detail.setFont(ui_font(FontSizes.xs))
        detail.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        copy.addWidget(detail)
        layout.addLayout(copy, 1)

        status = QLabel("待开始")
        status.setObjectName("step_status")
        status.setFont(ui_font(FontSizes.xs))
        status.setStyleSheet(f"color: {_C.TEXT_DISABLED};")
        layout.addWidget(status)
        self._step_statuses[name] = status
        return row

    def _check_item(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(ui_font(FontSizes.sm))
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

    # ── public update API ──────────────────────────────────────────

    def set_running(self, running: bool) -> None:
        """Toggle running state: show cancel button, disable start button."""
        self._cancel_btn.setVisible(running)
        self._start_btn.setEnabled(not running)

    def update_step_status(self, step_name: str, status: str, color: str) -> None:
        """Update the status label of a specific production step."""
        label = self._step_statuses.get(step_name)
        if label is not None:
            label.setText(status)
            label.setStyleSheet(f"color: {color};")

    def reset_steps(self) -> None:
        """Reset all step status labels to the default '待开始' state."""
        for label in self._step_statuses.values():
            label.setText("待开始")
            label.setStyleSheet(f"color: {_C.TEXT_DISABLED};")

    def _bind_viewmodel(self) -> None:
        vm = self._vm
        if vm is None:
            return
        vm.step_status_changed.connect(self._refresh_step_status)
        vm.pipeline_state_changed.connect(self._refresh_pipeline_state)
        self._refresh_step_status()
        self._refresh_pipeline_state()

    def _refresh_step_status(self) -> None:
        """Update each step row's status label from VM."""
        if self._vm is None or not self._step_rows:
            return
        statuses = self._vm.step_status
        for index, (_row, _badge, _title, status_lbl, _num, _name) in enumerate(self._step_rows):
            raw = statuses[index] if index < len(statuses) else "pending"
            label = self._vm.get_status_label(raw)
            color = {
                "pending": _C.TEXT_DISABLED,
                "active": _C.PRIMARY,
                "done": "#10b981",
                "error": "#ef4444",
            }.get(raw, _C.TEXT_MUTED)
            if status_lbl is not None:
                status_lbl.setText(label)
                status_lbl.setStyleSheet(f"color: {color};")

    def _refresh_pipeline_state(self) -> None:
        """Update the header / start button enabled state from VM."""
        if self._vm is None:
            return
        _ = self._vm.pipeline_state

    def start_pipeline(self, source_video: str, context: str) -> None:
        """Forward start request to ViewModel (no-op if no VM bound)."""
        if self._vm is not None:
            self._vm.start_pipeline(source_video, context)
