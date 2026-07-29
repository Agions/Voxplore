#!/usr/bin/env python3
"""Main production workspace page."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, ui_font
from .page_defaults import default_delivery_summary
from .page_view_models import (
    DELIVERY_PARAMETERS,
    HOME_WORKFLOW_STEPS,
)
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

    def __init__(self, viewmodel=None, parent=None, *, project_manager=None):
        super().__init__(parent)
        self.setObjectName("home_page")
        self._vm = viewmodel
        self._project_manager = project_manager
        self._status_values: dict[str, QLabel] = {}
        self._status_states: dict[str, QLabel] = {}
        self._workflow_statuses: dict[str, QLabel] = {}
        self._recent_layout: QVBoxLayout | None = None
        self._recent_empty: QFrame | None = None
        self._setup_style()
        self._setup_ui()
        if self._vm is not None:
            self._bind_viewmodel()

    def _setup_style(self):
        self.setStyleSheet(page_background_style("home_page"))

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = scroll_area()
        container = page_container()
        layout = container.layout()
        assert layout is not None  # for type checker

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

        open_btn = action_button("打开项目")
        open_btn.clicked.connect(lambda: self.open_project.emit(""))

        assets_btn = action_button("项目资产")
        assets_btn.clicked.connect(lambda: self.navigate.emit("assets"))
        return header_panel(
            "workspace_header",
            "第一人称短剧解说工作台",
            default_delivery_summary(),
            create_btn,
            open_btn,
            assets_btn,
        )

    def _build_status_grid(self) -> QFrame:
        frame = QFrame()
        layout = QGridLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(14)

        # 4 张状态卡 — 数据来源从 ViewModel 读
        self._status_cards: list[tuple[QFrame, QLabel, QLabel, str]] = []
        self._recent_panel_layout: QVBoxLayout | None = None
        items = [
            ("素材", "未导入", "0"),
            ("场景", "未拆分", "0"),
            ("脚本", "待生成", "--"),
            ("导出", "待配置", "1080x1920"),
        ]
        for index, (title, status, value) in enumerate(items):
            card, val_lbl, state_lbl = self._build_status_card(title, status, value)
            layout.addWidget(card, 0, index)
            self._status_cards.append((card, val_lbl, state_lbl, title))
        return frame

    # ──────────────────────────────────────────────────────────
    # ViewModel 绑定
    # ──────────────────────────────────────────────────────────

    def _bind_viewmodel(self) -> None:
        """Subscribe to VM signals and apply current state to cards."""
        vm = self._vm
        if vm is None:
            return
        vm.media_count_changed.connect(self._refresh_status_cards)
        vm.scene_count_changed.connect(self._refresh_status_cards)
        vm.script_status_changed.connect(self._refresh_status_cards)
        vm.export_config_changed.connect(self._refresh_status_cards)
        vm.recent_projects_changed.connect(self._refresh_recent_panel)
        # 立即拉一次
        self._refresh_status_cards()
        self._refresh_recent_panel()

    def _refresh_status_cards(self) -> None:
        """Update the 4 status cards from the ViewModel state."""
        if not self._status_cards or self._vm is None:
            return
        mapping = {
            "素材": (str(self._vm.media_count), "已导入" if self._vm.media_count else "未导入"),
            "场景": (str(self._vm.scene_count), "已拆分" if self._vm.scene_count else "未拆分"),
            "脚本": (
                "--" if self._vm.script_status == "待生成" else "已生成",
                self._vm.script_status,
            ),
            "导出": (self._vm.export_config, "已配置"),
        }
        for _card, val_lbl, state_lbl, title in self._status_cards:
            value, state = mapping.get(title, ("0", "未配置"))
            val_lbl.setText(value)
            state_lbl.setText(state)

    def _refresh_recent_panel(self) -> None:
        """Replace the empty-state placeholder with recent projects list."""
        if self._vm is None or self._recent_panel_layout is None:
            return
        recents = self._vm.recent_projects
        if not recents:
            return
        # Remove existing placeholder if any
        for i in reversed(range(self._recent_panel_layout.count())):
            item = self._recent_panel_layout.itemAt(i)
            widget = item.widget() if item else None
            if widget is not None and widget.property("recent_placeholder") is True:
                widget.deleteLater()
                self._recent_panel_layout.removeWidget(widget)
        for path in recents[:3]:
            lbl = QLabel(path)
            lbl.setStyleSheet(f"color: {_C.TEXT_SECONDARY};")
            self._recent_panel_layout.addWidget(lbl)

    def _build_workflow_panel(self) -> QFrame:
        frame = panel("workflow_panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        layout.addWidget(section_title("生产流程"))
        for step in HOME_WORKFLOW_STEPS:
            layout.addWidget(self._workflow_row(step.number, step.name, step.detail))
        layout.addStretch()
        return frame

    def _build_delivery_panel(self) -> QFrame:
        frame = panel("delivery_panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        layout.addWidget(section_title("交付参数"))
        for item in DELIVERY_PARAMETERS:
            layout.addWidget(key_value_row(item.label, item.value))
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

        # 暴露 layout 给 ViewModel 刷新使用
        self._recent_panel_layout = layout
        self._recent_layout = layout
        placeholder = empty_state("暂无项目资产", 120)
        placeholder.setProperty("recent_placeholder", True)
        self._recent_empty = placeholder
        layout.addWidget(placeholder, 1)
        return frame

    def _build_status_card(
        self, title: str, status: str, value: str
    ) -> tuple[QFrame, QLabel, QLabel]:
        """Build a status card and return (frame, value_label, state_label).

        The two labels are returned so the ViewModel can update them
        in-place without traversing child widgets.
        """
        card = panel(f"status_{title}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(6)

        label = QLabel(title)
        label.setFont(ui_font(FontSizes.xs, FontWeights.Medium))
        label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        card_layout.addWidget(label)

        val = QLabel(value)
        val.setFont(ui_font(FontSizes.lg, FontWeights.Bold))
        val.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        card_layout.addWidget(val)
        self._status_values[title] = val

        state = QLabel(status)
        state.setFont(ui_font(FontSizes.xs))
        state.setStyleSheet(f"color: {_C.TEXT_DISABLED};")
        card_layout.addWidget(state)
        self._status_states[title] = state
        return card, val, state

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
        step_label.setFont(ui_font(FontSizes.xs, FontWeights.Bold))
        step_label.setStyleSheet(f"color: {_C.PRIMARY};")
        layout.addWidget(step_label)

        name_label = QLabel(name)
        name_label.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        name_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        layout.addWidget(name_label, 1)

        status_label = QLabel(status)
        status_label.setFont(ui_font(FontSizes.xs))
        status_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        layout.addWidget(status_label)
        self._workflow_statuses[name] = status_label
        return row

    # ── public update API ──────────────────────────────────────────

    def update_stats(
        self,
        projects_count: int = 0,
        assets_count: int = 0,
        scenes_count: int = 0,
        script_status: str = "待生成",
    ) -> None:
        """Update dashboard status cards with real data."""
        if "素材" in self._status_values:
            self._status_values["素材"].setText(str(assets_count))
            self._status_states["素材"].setText(
                "已导入" if assets_count > 0 else "未导入"
            )
        if "场景" in self._status_values:
            self._status_values["场景"].setText(str(scenes_count))
            self._status_states["场景"].setText(
                "已拆分" if scenes_count > 0 else "未拆分"
            )
        if "脚本" in self._status_values:
            self._status_values["脚本"].setText(
                str(projects_count) if projects_count > 0 else "--"
            )
            self._status_states["脚本"].setText(script_status)

    def update_recent_projects(self, recent_projects: list[str]) -> None:
        """Populate the recent-assets panel with project paths."""
        if self._recent_layout is None:
            return
        # Remove previous dynamic rows (keep header row + empty state)
        while self._recent_layout.count() > 2:
            item = self._recent_layout.takeAt(1)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not recent_projects:
            if self._recent_empty is not None:
                self._recent_empty.setVisible(True)
            return

        if self._recent_empty is not None:
            self._recent_empty.setVisible(False)

        from pathlib import Path

        for project_path in recent_projects[:5]:
            name = Path(project_path).name
            row_btn = QPushButton(name)
            row_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            row_btn.setFont(ui_font(FontSizes.xs))
            row_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {_C.TEXT_SECONDARY};
                    background: transparent;
                    border: none;
                    text-align: left;
                    padding: 4px 0;
                }}
                QPushButton:hover {{
                    color: {_C.PRIMARY};
                }}
            """)
            row_btn.clicked.connect(
                lambda checked=False, p=project_path: self.open_project.emit(p)
            )
            self._recent_layout.insertWidget(
                self._recent_layout.count() - 1, row_btn
            )

    def refresh_stats(self) -> None:
        """Re-query ProjectManager and update all dashboard cards."""
        pm = self._project_manager
        if pm is None:
            return
        projects = pm.scan_projects()
        self.update_stats(
            projects_count=len(projects),
            assets_count=sum(
                len(p.media_files) for p in pm.get_all_projects()
            ),
        )
        self.update_recent_projects(pm.get_recent_projects())

    def update_export_status(self, status: str) -> None:
        """Update the export status card."""
        if "导出" in self._status_states:
            self._status_states["导出"].setText(status)
