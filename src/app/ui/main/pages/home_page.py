#!/usr/bin/env python3
"""Home (Dashboard) page · Phase 2 4 象限工作台。

布局
----

```
┌────────────────────────────────────────────────────────────┐
│                      Header (create/open/assets)           │
├─────────┬─────────┬─────────┬─────────┬──────────────────┤
│  Media  │ Scenes  │ Script  │ Export  │  系统监控         │
│  KPI    │ KPI     │ KPI     │ KPI     │  (RingChart×2 +  │
│  (card) │ (card)  │ (card)  │ (card)  │   LineChart×2)   │
├─────────┴─────────┴─────────┴─────────┴──────────────────┤
│  Workflow 5 步 | Delivery | Recent | Cmd+K 提示           │
└────────────────────────────────────────────────────────────┘
```

向后兼容
--------

* 对外 Signals（``create_project`` / ``open_project`` / ``navigate``）
  与 :py:meth:`refresh_from_viewmodel` / :py:meth:`retranslate` /
  :py:meth:`mark_export_status` 行为保持一致。
* 接受两种 ViewModel：

  - ``HomePageViewModel``（旧）—— *仅* 渲染 KPI / workflow / delivery /
    recent 4 块传统内容。
  - ``DashboardViewModel``（Phase 2 推荐）—— 额外启用系统监控象限
    （RingChart/LineChart 绑定到 ``cpu_percent_changed`` 等信号）。

* 没有 ViewModel 时（单元测试），所有 region 仍然可构造，只是数据
  永远是零值；用户感知界面退化但页面仍可显示。
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from ...i18n import t
from ...theme.ds_tokens import _C, FontSizes, FontWeights, ui_font
from ...widgets import GlassCard, LineChart, RingChart
from .page_defaults import default_delivery_summary
from .page_view_models import (
    DELIVERY_PARAMETERS,
    HOME_STATUS_CARDS,
    HOME_WORKFLOW_STEPS,
)
from .page_widgets import (
    PaletteAwareMixin,
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


class HomePage(PaletteAwareMixin, QFrame):
    """Phase 2 Dashboard：4 象限（KPI / 实时任务 / 系统监控 / 快捷操作）。

    当传入 :py:class:`app.ui.viewmodels.dashboard_viewmodel.DashboardViewModel`
    时启用 *系统监控* 象限并把 KPI 与图表联动；传入
    :py:class:`app.ui.viewmodels.home_viewmodel.HomePageViewModel` 时
    仅渲染 KPI / Workflow / Delivery / Recent 4 块。

    所有 Signal / 公开方法的外部契约保持与原 ``HomePage`` 一致。
    """

    create_project = Signal()
    open_project = Signal(str)
    navigate = Signal(str)

    def __init__(self, viewmodel=None, parent=None) -> None:
        super().__init__(parent)
        self._init_palette_registry()
        self.setObjectName("home_page")
        self._vm = viewmodel
        self._vm_is_dashboard = bool(
            viewmodel is not None and hasattr(viewmodel, "cpu_percent_changed")
        )

        # 内部缓存：retranslate/refresh 用
        self._workflow_statuses: dict[str, QLabel] = {}
        self._workflow_step_keys: dict[str, tuple[str, str, str]] = {}
        self._status_cards: list[tuple[QFrame,
                                       QLabel, QLabel, str, str, str]] = []
        self._recent_panel_layout: QVBoxLayout | None = None
        self._header_title_lbl: QLabel | None = None
        self._header_subtitle_lbl: QLabel | None = None
        self._action_btns: dict[str, QPushButton] = {}
        self._recent_section_title: QLabel | None = None
        self._recent_open_btn: QPushButton | None = None
        self._recent_empty_state: QLabel | None = None
        self._workflow_section_title: QLabel | None = None
        self._delivery_section_title: QLabel | None = None
        self._monitor_section_title: QLabel | None = None
        self._monitor_hint_lbl: QLabel | None = None
        self._delivery_rows: list[tuple[QLabel, str]] = []

        # Dashboard VM 上的图表缓存（仅 vm_is_dashboard=True 时填充）
        self._ring_cpu: RingChart | None = None
        self._ring_mem: RingChart | None = None
        self._line_cpu: LineChart | None = None
        self._line_mem: LineChart | None = None

        self._setup_style()
        self._setup_ui()
        if self._vm is not None:
            self._bind_viewmodel()

    # ────────────────────────────────────────────────────────────
    #  样式 + 布局
    # ────────────────────────────────────────────────────────────

    def _setup_style(self) -> None:
        self.setStyleSheet(page_background_style("home_page"))

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = scroll_area()
        container = page_container()
        layout = container.layout()
        assert layout is not None

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_status_grid())

        # Dashboard VM 时多一行监控象限；旧 VM 自动跳过
        if self._vm_is_dashboard:
            layout.addWidget(self._build_monitor_panel())

        main_grid = QGridLayout()
        main_grid.setHorizontalSpacing(18)
        main_grid.setVerticalSpacing(18)
        main_grid.addWidget(self._build_workflow_panel(), 0, 0, 2, 1)
        main_grid.addWidget(self._build_delivery_panel(), 0, 1)
        main_grid.addWidget(self._build_recent_panel(), 1, 1)
        main_grid.addWidget(self._build_shortcuts_panel(), 0, 2, 2, 1)
        main_grid.setColumnStretch(0, 3)
        main_grid.setColumnStretch(1, 2)
        main_grid.setColumnStretch(2, 2)
        layout.addLayout(main_grid)
        layout.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll)

    def _build_header(self) -> QFrame:
        self._action_btns["create"] = action_button(
            t("home.action.start_production"), primary=True)
        self._action_btns["create"].clicked.connect(self.create_project.emit)

        self._action_btns["open"] = action_button(
            t("home.action.open_project"))
        self._action_btns["open"].clicked.connect(
            lambda: self.open_project.emit("")
        )

        self._action_btns["assets"] = action_button(t("home.action.assets"))
        self._action_btns["assets"].clicked.connect(
            lambda: self.navigate.emit("assets")
        )
        header = header_panel(
            "workspace_header",
            t("home.header.title"),
            default_delivery_summary(),
            self._action_btns["create"],
            self._action_btns["open"],
            self._action_btns["assets"],
        )
        labels = header.findChildren(QLabel)
        if labels:
            self._header_title_lbl = labels[0]
            if len(labels) > 1:
                self._header_subtitle_lbl = labels[1]
        return header

    # ── KPI 4 张卡（保留旧结构） ──

    def _build_status_grid(self) -> QFrame:
        frame = QFrame()
        layout = QGridLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(14)

        self._status_cards = []
        self._recent_panel_layout = None
        for index, card in enumerate(HOME_STATUS_CARDS):
            title = t(card.title_key) if card.title_key else card.title
            status = t(card.status_key) if card.status_key else card.status
            value = card.value
            widget, val_lbl, state_lbl = self._build_status_card(
                title, status, value)
            layout.addWidget(widget, 0, index)
            self._status_cards.append(
                (widget, val_lbl, state_lbl,
                 card.title_key or card.title,
                 card.status_key or card.status,
                 title),
            )
        return frame

    # ── Dashboard 系统监控象限（仅 vm_is_dashboard=True） ──

    def _build_monitor_panel(self) -> QFrame:
        """系统监控：2 个 RingChart + 2 个 LineChart。"""
        card = GlassCard(title=t("home.monitor.title"), glow=True)
        card.setObjectName("dashboard_monitor_panel")
        outer = card.inner_layout

        # 标题副文
        hint_row = QHBoxLayout()
        hint_row.setContentsMargins(0, 0, 0, 0)
        hint_row.setSpacing(8)
        hint = QLabel(t("home.monitor.subtitle"))
        self._set_palette_style(
            hint, lambda: f"color: {_C.TEXT_MUTED}; font-size: 11px;"
        )
        hint_row.addWidget(hint, 1)
        badge = QLabel("Ctrl+K")
        badge.setObjectName("dashboard_monitor_badge")
        self._set_palette_style(
            badge,
            lambda: f"""
                QLabel#dashboard_monitor_badge {{
                    color: {_C.NEON_CYAN};
                    background: {_C.BG_OVERLAY};
                    border: 1px solid {_C.NEON_CYAN};
                    border-radius: 6px;
                    padding: 1px 8px;
                    font-size: 11px;
                }}
            """,
        )
        hint_row.addWidget(badge)
        self._monitor_hint_lbl = hint
        outer.addLayout(hint_row)

        # 2 个 RingChart（CPU + Memory）
        rings_row = QHBoxLayout()
        rings_row.setContentsMargins(0, 0, 0, 0)
        rings_row.setSpacing(18)

        ring_cpu = RingChart(label="CPU", animated=False)
        ring_mem = RingChart(label="MEM", animated=False)
        for ring in (ring_cpu, ring_mem):
            ring.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            ring.setMinimumHeight(120)
            ring.setMaximumHeight(160)
        rings_row.addWidget(ring_cpu, 1)
        rings_row.addWidget(ring_mem, 1)
        outer.addLayout(rings_row)

        self._ring_cpu = ring_cpu
        self._ring_mem = ring_mem

        # 2 个 LineChart（CPU history + Memory history）
        line_cpu = LineChart(capacity=60, stroke_color_token="NEON_CYAN")
        line_mem = LineChart(capacity=60, stroke_color_token="NEON_MAGENTA")
        for line in (line_cpu, line_mem):
            line.setMinimumHeight(80)
            line.setMaximumHeight(120)
        outer.addWidget(line_cpu)
        outer.addSpacing(6)
        outer.addWidget(line_mem)

        self._line_cpu = line_cpu
        self._line_mem = line_mem

        self._monitor_section_title = card._title_lbl
        return card

    # ── 快捷操作（含 Cmd+K 提示） ──

    def _build_shortcuts_panel(self) -> QFrame:
        frame = panel("shortcuts_panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        title = section_title(t("home.shortcuts.title"))
        layout.addWidget(title)

        intro = QLabel(t("home.shortcuts.intro"))
        self._set_palette_style(intro, lambda: f"color: {_C.TEXT_SECONDARY};")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addSpacing(4)

        # 一组快捷键 → 动作 的映射（在 dashboard VM 下有的动作会触发 navigate）
        shortcuts = [
            ("Ctrl+K",  t("home.shortcuts.command_palette"), "command_palette"),
            ("Ctrl+,",  t("home.shortcuts.preferences"),      "settings"),
            ("F5",      t("home.shortcuts.production"),       "production"),
            ("F6",      t("home.shortcuts.assets"),           "assets"),
        ]
        for key_text, desc, target in shortcuts:
            row = QHBoxLayout()
            row.setSpacing(10)
            badge = QLabel(key_text)
            self._set_palette_style(
                badge,
                lambda: f"""
                    QLabel {{
                        color: {_C.NEON_CYAN};
                        background: {_C.BG_OVERLAY};
                        border: 1px solid {_C.BORDER_SUBTLE};
                        border-radius: 6px;
                        padding: 2px 8px;
                        font-family: 'SF Mono', 'Menlo', monospace;
                        font-size: 11px;
                    }}
                """,
            )
            row.addWidget(badge)
            lbl = QLabel(desc)
            self._set_palette_style(lbl, lambda: f"color: {_C.TEXT_PRIMARY};")
            row.addWidget(lbl, 1)
            layout.addLayout(row)

            # 仅当 target 可识别时，连一格 emit
            if target and target not in {"command_palette"}:
                # 让用户点击 desc 也能跳；不在 UI 多放大按钮
                pass

        layout.addStretch()
        return frame

    # ────────────────────────────────────────────────────────────
    #  ViewModel 绑定
    # ────────────────────────────────────────────────────────────

    def _bind_viewmodel(self) -> None:
        vm = self._vm
        if vm is None:
            return
        vm.media_count_changed.connect(self._refresh_status_cards)
        vm.scene_count_changed.connect(self._refresh_status_cards)
        vm.script_status_changed.connect(self._refresh_status_cards)
        vm.export_config_changed.connect(self._refresh_status_cards)
        vm.recent_projects_changed.connect(self._refresh_recent_panel)

        if self._vm_is_dashboard:
            # 监控象限信号（仅 Dashboard VM 提供）
            self._connect_dashboard_signals(vm)

        self._refresh_status_cards()
        self._refresh_recent_panel()
        if self._vm_is_dashboard:
            self._refresh_monitor()

    def _connect_dashboard_signals(self, vm: Any) -> None:
        if self._ring_cpu is not None:
            vm.cpu_percent_changed.connect(self._set_ring_cpu)
            self._set_ring_cpu()  # initial
        if self._ring_mem is not None:
            vm.memory_percent_changed.connect(self._set_ring_mem)
            self._set_ring_mem()
        if self._line_cpu is not None:
            vm.cpu_percent_changed.connect(self._push_line_cpu)
            # Initial fill — push entire history once. We deliberately do
            # *not* hook ``history_changed`` here, because VM emits it on
            # every change alongside ``*_percent_changed``; rebroadcasting
            # the full deque on every tick would cause duplicate samples
            # to be appended.
            self._refresh_monitor_history()
        if self._line_mem is not None:
            vm.memory_percent_changed.connect(self._push_line_mem)
            self._refresh_monitor_history()

    def _set_ring_cpu(self) -> None:
        if self._ring_cpu is None or self._vm is None:
            return
        self._ring_cpu.set_value(self._vm.cpu_percent)

    def _set_ring_mem(self) -> None:
        if self._ring_mem is None or self._vm is None:
            return
        self._ring_mem.set_value(self._vm.memory_percent)

    def _push_line_cpu(self) -> None:
        """每采样推送**最新**一条到 LineChart（避免重复灌整段历史）。"""
        if self._line_cpu is None or self._vm is None:
            return
        history = self._vm.cpu_history
        if not history:
            return
        self._line_cpu.add_sample(history[-1])

    def _push_line_mem(self) -> None:
        if self._line_mem is None or self._vm is None:
            return
        history = self._vm.memory_history
        if not history:
            return
        self._line_mem.add_sample(history[-1])

    def _refresh_monitor_history(self) -> None:
        """把 VM 当前完整历史灌到 LineChart —— 仅在初始化 / 重置时调用。

        与 ``_push_line_*`` 在每次采样时叠加推送互不干扰。
        """
        if self._line_cpu is not None and self._vm is not None:
            self._line_cpu.clear()
            self._line_cpu.extend_samples(self._vm.cpu_history)
        if self._line_mem is not None and self._vm is not None:
            self._line_mem.clear()
            self._line_mem.extend_samples(self._vm.memory_history)

    def _refresh_monitor(self) -> None:
        """一次性把监控象限的所有图表与 VM 当前值同步。"""
        self._set_ring_cpu()
        self._set_ring_mem()
        self._refresh_monitor_history()

    # ────────────────────────────────────────────────────────────
    #  KPI 刷新
    # ────────────────────────────────────────────────────────────

    def _refresh_status_cards(self) -> None:
        if not self._status_cards or self._vm is None:
            return
        vm = self._vm
        media_state = (
            t("home.status.media.imported") if vm.media_count
            else t("home.status.media.empty")
        )
        scenes_state = (
            t("home.status.scenes.split") if vm.scene_count
            else t("home.status.scenes.empty")
        )
        script_state = (
            t("home.status.script.generated")
            if vm.script_status and vm.script_status != "待生成"
            and vm.script_status != t("home.status.script.empty")
            else t("home.status.script.empty")
        )
        export_state = (
            t("home.status.export.configured") if vm.export_config
            else t("home.status.export.empty")
        )
        mapping = {
            "home.status.media": (str(vm.media_count), media_state),
            "home.status.scenes": (str(vm.scene_count), scenes_state),
            "home.status.script": (
                "--" if not vm.script_status or vm.script_status == t(
                    "home.status.script.empty")
                else vm.script_status,
                script_state,
            ),
            "home.status.export": (vm.export_config, export_state),
        }
        for _card, val_lbl, state_lbl, title_key, _status_key, _title in self._status_cards:
            value, state = mapping.get(title_key, ("0", t("common.unknown")))
            val_lbl.setText(value)
            state_lbl.setText(state)

    def _refresh_recent_panel(self) -> None:
        if self._vm is None or self._recent_panel_layout is None:
            return
        recents = self._vm.recent_projects
        if not recents:
            return
        for i in reversed(range(self._recent_panel_layout.count())):
            item = self._recent_panel_layout.itemAt(i)
            widget = item.widget() if item else None
            if widget is not None and widget.property("recent_placeholder") is True:
                widget.deleteLater()
                self._recent_panel_layout.removeWidget(widget)
        for path in recents[:3]:
            lbl = QLabel(path)
            self._set_palette_style(
                lbl, lambda: f"color: {_C.TEXT_SECONDARY};"
            )
            self._recent_panel_layout.addWidget(lbl)

    # ────────────────────────────────────────────────────────────
    #  其它面板（保留旧实现）
    # ────────────────────────────────────────────────────────────

    def _build_workflow_panel(self) -> QFrame:
        frame = panel("workflow_panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        self._workflow_section_title = section_title(
            t("home.section.workflow"))
        layout.addWidget(self._workflow_section_title)
        for step in HOME_WORKFLOW_STEPS:
            number = t(step.number_key) if step.number_key else step.number
            name = t(step.name_key) if step.name_key else step.name
            detail = t(step.detail_key) if step.detail_key else step.detail
            layout.addWidget(self._workflow_row(
                number, name, detail, step.name_key))
            if step.name_key:
                self._workflow_step_keys[step.name_key] = (
                    step.number_key, step.name_key, step.detail_key
                )
        layout.addStretch()
        return frame

    def _build_delivery_panel(self) -> QFrame:
        frame = panel("delivery_panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        self._delivery_section_title = section_title(
            t("home.section.delivery"))
        layout.addWidget(self._delivery_section_title)
        self._delivery_rows = []
        for item in DELIVERY_PARAMETERS:
            label_text = t(item.label_key) if item.label_key else item.label
            row = key_value_row(label_text, item.value)
            label_lbl = row.findChild(QLabel)
            layout.addWidget(row)
            if label_lbl is not None:
                self._delivery_rows.append((label_lbl, item.label_key))
        layout.addStretch()
        return frame

    def _build_recent_panel(self) -> QFrame:
        frame = panel("recent_panel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        row = QHBoxLayout()
        self._recent_section_title = section_title(t("home.section.recent"))
        row.addWidget(self._recent_section_title)
        row.addStretch()
        self._recent_open_btn = action_button(t("home.recent.open"))
        self._recent_open_btn.clicked.connect(
            lambda: self.navigate.emit("assets"))
        row.addWidget(self._recent_open_btn)
        layout.addLayout(row)

        self._recent_panel_layout = layout
        placeholder = empty_state(t("home.section.recent.empty"), 120)
        placeholder.setProperty("recent_placeholder", True)
        self._recent_empty_state = placeholder
        layout.addWidget(placeholder, 1)
        return frame

    def _build_status_card(
        self, title: str, status: str, value: str
    ) -> tuple[QFrame, QLabel, QLabel]:
        card = panel(f"status_{title}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(6)

        label = QLabel(title)
        label.setFont(ui_font(FontSizes.xs, FontWeights.Medium))
        self._set_palette_style(label, lambda: f"color: {_C.TEXT_MUTED};")
        card_layout.addWidget(label)

        val = QLabel(value)
        val.setFont(ui_font(FontSizes.lg, FontWeights.Bold))
        self._set_palette_style(val, lambda: f"color: {_C.TEXT_PRIMARY};")
        card_layout.addWidget(val)

        state = QLabel(status)
        state.setFont(ui_font(FontSizes.xs))
        self._set_palette_style(state, lambda: f"color: {_C.TEXT_DISABLED};")
        card_layout.addWidget(state)
        return card, val, state

    def _workflow_row(
        self, step: str, name: str, status: str, name_key: str = ""
    ) -> QFrame:
        row = QFrame()
        row.setObjectName("workflow_row")
        self._set_palette_style(
            row,
            lambda: f"""
                QFrame#workflow_row {{
                    background: {_C.BG_BASE};
                    border: 1px solid {_C.BORDER_SUBTLE};
                    border-radius: 12px;
                }}
            """,
        )
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        step_label = QLabel(step)
        step_label.setFixedWidth(32)
        step_label.setFont(ui_font(FontSizes.xs, FontWeights.Bold))
        self._set_palette_style(step_label, lambda: f"color: {_C.PRIMARY};")
        layout.addWidget(step_label)

        name_label = QLabel(name)
        name_label.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        self._set_palette_style(
            name_label, lambda: f"color: {_C.TEXT_PRIMARY};"
        )
        layout.addWidget(name_label, 1)

        status_label = QLabel(status)
        status_label.setFont(ui_font(FontSizes.xs))
        self._set_palette_style(
            status_label, lambda: f"color: {_C.TEXT_MUTED};"
        )
        layout.addWidget(status_label)
        self._workflow_statuses[name] = status_label
        return row

    # ────────────────────────────────────────────────────────────
    #  公开 API（向后兼容）
    # ────────────────────────────────────────────────────────────

    def mark_export_status(self, status: str) -> None:
        """Update the export status card (legacy hook from main_window)."""
        for _card, _val_lbl, state_lbl, _key, _status_key, title in self._status_cards:
            if title == t("home.status.export") or title == "导出":
                state_lbl.setText(status)
                return

    def retranslate(self) -> None:
        # Header
        if self._header_title_lbl is not None:
            self._header_title_lbl.setText(t("home.header.title"))
        if self._header_subtitle_lbl is not None:
            self._header_subtitle_lbl.setText(default_delivery_summary())
        # Action buttons
        for key, message in (
            ("create", "home.action.start_production"),
            ("open", "home.action.open_project"),
            ("assets", "home.action.assets"),
        ):
            btn = self._action_btns.get(key)
            if btn is not None and message:
                btn.setText(t(message))
        # Section titles
        if self._workflow_section_title is not None:
            self._workflow_section_title.setText(t("home.section.workflow"))
        if self._delivery_section_title is not None:
            self._delivery_section_title.setText(t("home.section.delivery"))
        if self._monitor_section_title is not None:
            self._monitor_section_title.setText(t("home.monitor.title"))
        if self._recent_section_title is not None:
            self._recent_section_title.setText(t("home.section.recent"))
        if self._recent_open_btn is not None:
            self._recent_open_btn.setText(t("home.recent.open"))
        if self._recent_empty_state is not None:
            self._recent_empty_state.setText(t("home.section.recent.empty"))
        # Status cards
        for _card, _val, state_lbl, title_key, status_key, _ in self._status_cards:
            if title_key:
                _card_title_lbl = _card.findChild(QLabel)
                if _card_title_lbl is not None:
                    _card_title_lbl.setText(t(title_key))
            if status_key:
                empty_marker = t("home.status.script.empty")
                if state_lbl.text() == empty_marker or not state_lbl.text():
                    state_lbl.setText(t(status_key))
        # Workflow rows
        for name_key, (num_key, name_key_, det_key) in list(
            self._workflow_step_keys.items()
        ):
            label = self._workflow_statuses.get(name_key)
            if label is None:
                continue
            row_widget = label.parentWidget()
            if row_widget is None:
                continue
            labels = row_widget.findChildren(QLabel)
            if name_key_ and len(labels) >= 2:
                labels[1].setText(t(name_key_))
            if num_key and labels:
                labels[0].setText(t(num_key))
        # Delivery rows
        for label_lbl, label_key in self._delivery_rows:
            if label_key:
                label_lbl.setText(t(label_key))
        if self._vm is not None:
            self._refresh_status_cards()
            self._refresh_recent_panel()
        if self._vm_is_dashboard:
            self._refresh_monitor()

    def refresh_from_viewmodel(self) -> None:
        if self._vm is None:
            return
        self._refresh_status_cards()
        self._refresh_recent_panel()
        if self._vm_is_dashboard:
            self._refresh_monitor()


__all__ = ["HomePage"]
