#!/usr/bin/env python3
"""Project assets page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ...theme.ds_tokens import _C, FontSizes, Radii
from .page_widgets import (
    action_button,
    empty_state,
    header_panel,
    page_background_style,
    page_container,
    panel,
    scroll_area,
    section_title,
)

if TYPE_CHECKING:
    from ...viewmodels.assets_viewmodel import AssetsPageViewModel


class AssetsPage(QFrame):
    """Project and media assets workspace.

    Phase 2C: shows real recent projects list + current project asset
    summary read from :class:`AssetsPageViewModel`. The empty state is
    only shown when both the current project has 0 assets AND there are
    0 recent projects.
    """

    import_requested = Signal()

    def __init__(self, viewmodel: AssetsPageViewModel | None = None, parent=None):
        super().__init__(parent)
        self._vm = viewmodel
        self.setObjectName("assets_page")
        self._setup_style()
        self._setup_ui()
        if self._vm is not None:
            self._bind_viewmodel()

    def _setup_style(self):
        self.setStyleSheet(page_background_style("assets_page"))

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = scroll_area()
        container = page_container()
        layout = container.layout()
        assert layout is not None  # for type checker

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_asset_table(), 1)
        layout.addWidget(self._build_source_panel())
        layout.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll)

    def _build_header(self) -> QFrame:
        import_btn = action_button("导入素材", primary=True)
        # Phase 2D+: import button triggers file dialog directly (was: signal)
        import_btn.clicked.connect(self._on_import_requested)
        return header_panel(
            "assets_header",
            "项目资产",
            "管理素材、脚本、配音、字幕与导出文件",
            import_btn,
        )

    def _build_asset_table(self) -> QFrame:
        frame = panel("asset_table")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header.addWidget(section_title("资产列表"))
        header.addStretch()
        # Phase 2C: 刷新按钮接 VM.refresh()
        refresh_btn = action_button("刷新")
        refresh_btn.clicked.connect(self._on_refresh_clicked)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        columns = self._row("类型", "名称", "状态", header=True)
        layout.addWidget(columns)

        # Phase 2C: empty state 只在 VM 显示"无任何资产"时显示
        # 默认无 VM 时仍显示原 empty state,保证向后兼容
        if self._vm is None:
            layout.addWidget(
                empty_state(
                    "暂无资产。导入视频素材后，系统会在这里显示拆分场景、脚本、配音和导出记录。",
                    180,
                    padding=24,
                ),
                1,
            )
        else:
            # 容器:可显示最近项目列表或 empty state
            self._asset_placeholder = QLabel("加载中…")
            self._asset_placeholder.setObjectName("asset_placeholder")
            self._asset_placeholder.setAlignment(self._asset_placeholder.alignment() | 0x0084)  # AlignCenter
            self._asset_placeholder.setStyleSheet(f"color: {_C.TEXT_MUTED};")
            layout.addWidget(self._asset_placeholder, 1)
        return frame

    def _build_source_panel(self) -> QFrame:
        frame = panel("source_panel")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # Phase 2C: 最近项目列表(最多 3 个) 取代原本的素材目录/输出目录/资源规范
        # 无 VM 时保留原结构
        if self._vm is None:
            for title, desc in [
                ("素材目录", "未设置"),
                ("输出目录", "~/SceneFab/exports"),
                ("资源规范", "显式打包 resources/"),
            ]:
                layout.addWidget(self._source_item(title, desc))
        else:
            self._recent_summary_label = QLabel("暂无最近项目")
            self._recent_summary_label.setObjectName("recent_summary_label")
            self._recent_summary_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
            layout.addWidget(self._recent_summary_label, 1)
        layout.addStretch()
        return frame

    def _row(self, kind: str, name: str, status: str, header: bool = False) -> QFrame:
        row = QFrame()
        row.setObjectName("asset_row")
        bg = _C.BG_ELEVATED if header else _C.BG_BASE
        row.setStyleSheet(f"""
            QFrame#asset_row {{
                background: {bg};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
            }}
        """)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        for text, stretch in [(kind, 1), (name, 3), (status, 1)]:
            label = QLabel(text)
            label.setFont(QFont("", FontSizes.xs, QFont.Weight.Medium))
            label.setStyleSheet(
                f"color: {_C.TEXT_MUTED if header else _C.TEXT_SECONDARY};"
            )
            layout.addWidget(label, stretch)
        return row

    def _source_item(self, title: str, desc: str) -> QFrame:
        item = QFrame()
        item.setObjectName("source_item")
        item.setStyleSheet(f"""
            QFrame#source_item {{
                background: {_C.BG_BASE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
            }}
        """)
        layout = QVBoxLayout(item)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setFont(QFont("", FontSizes.xs, QFont.Weight.Medium))
        title_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        layout.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
        desc_label.setStyleSheet(f"color: {_C.TEXT_SECONDARY};")
        layout.addWidget(desc_label)
        return item

    # ──────────────────────────────────────────────────────────
    # ViewModel 绑定 (Phase 2C)
    # ──────────────────────────────────────────────────────────

    def _bind_viewmodel(self) -> None:
        vm = self._vm
        if vm is None:
            return
        vm.current_assets_changed.connect(self._refresh_assets_view)
        vm.recent_projects_changed.connect(self._refresh_recent_summary)
        self._refresh_assets_view()
        self._refresh_recent_summary()

    def _refresh_assets_view(self) -> None:
        """Update asset placeholder from VM state."""
        if self._vm is None or not hasattr(self, "_asset_placeholder"):
            return
        summary = self._vm.current_assets
        if summary.is_empty:
            self._asset_placeholder.setText(
                "暂无资产。导入视频素材后,系统会在这里显示拆分场景、脚本、配音和导出记录。"
            )
        else:
            parts = []
            if summary.media_count:
                parts.append(f"素材 {summary.media_count}")
            if summary.script_count:
                parts.append(f"脚本 {summary.script_count}")
            if summary.audio_count:
                parts.append(f"配音 {summary.audio_count}")
            if summary.export_count:
                parts.append(f"导出 {summary.export_count}")
            self._asset_placeholder.setText(" · ".join(parts) or "暂无资产")

    def _refresh_recent_summary(self) -> None:
        """Update recent projects summary line from VM state."""
        if self._vm is None or not hasattr(self, "_recent_summary_label"):
            return
        recents = self._vm.recent_projects
        if not recents:
            self._recent_summary_label.setText("暂无最近项目")
            return
        # 最多显示 3 个
        shown = recents[:3]
        names = [r.name for r in shown]
        suffix = f" 等 {len(recents)} 个" if len(recents) > 3 else ""
        self._recent_summary_label.setText(
            f"最近项目: {', '.join(names)}{suffix}"
        )

    def _on_refresh_clicked(self) -> None:
        """Refresh button: forward to VM."""
        if self._vm is not None:
            self._vm.refresh()

    # ──────────────────────────────────────────────────────────
    # 公共入口 (Phase 2C: import 转发到 VM)
    # ──────────────────────────────────────────────────────────

    def import_media(self, files: list[str]) -> int:
        """Forward import request to ViewModel."""
        if self._vm is None:
            return 0
        return self._vm.import_media(files)

    # ──────────────────────────────────────────────────────────
    # Phase 2D+: 拖拽导入素材 (file dialog 触发)
    # ──────────────────────────────────────────────────────────

    def _on_import_requested(self) -> None:
        """Slot for the '导入素材' button — show a file picker.

        The picked paths are forwarded to ``vm.import_media``. If the
        page has no VM bound (e.g. smoke test mode), the dialog still
        opens but nothing is recorded — the user just gets a no-op.
        """
        paths = self._show_import_dialog(parent=self.window())
        if paths:
            self.import_media(paths)

    def _show_import_dialog(self, parent: QWidget | None = None) -> list[str]:
        """Open a multi-select file picker. Returns the chosen paths.

        The dialog accepts common video / audio formats used by the
        first-person narration pipeline. Returns an empty list if the
        user cancels.

        Splitting this out from :meth:`_on_import_requested` makes it
        easy to mock the dialog in tests (just monkey-patch the method
        to return a fixed list).
        """
        filter_str = (
            "媒体文件 (*.mp4 *.mov *.mkv *.avi *.flv *.wmv "
            "*.mp3 *.wav *.m4a *.flac);;所有文件 (*)"
        )
        result: list[str] = []
        # Use getOpenFileNames (static) so the dialog doesn't block the
        # page on a non-Qt event loop. Returns ([paths], selectedFilter).
        result, _ = QFileDialog.getOpenFileNames(
            parent,
            "选择要导入的素材",
            "",
            filter_str,
        )
        return list(result)
