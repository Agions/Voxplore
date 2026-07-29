#!/usr/bin/env python3
"""Project assets page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, ui_font
from .page_view_models import ASSET_SOURCE_ITEMS, ASSET_TABLE_COLUMNS
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
    from scenefab.project.manager import ProjectManager

    from ...viewmodels.assets_viewmodel import AssetsPageViewModel


class AssetsPage(QFrame):
    """Project and media assets workspace."""

    import_requested = Signal()
    navigate = Signal(str)

    def __init__(self, viewmodel: AssetsPageViewModel | None = None, parent=None, *, project_manager: ProjectManager | None = None):
        super().__init__(parent)
        self._vm = viewmodel
        self._project_manager = project_manager
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
        refresh_btn = action_button("刷新")
        refresh_btn.clicked.connect(self._on_refresh_clicked)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        columns = self._row(*ASSET_TABLE_COLUMNS, header=True)
        layout.addWidget(columns)

        # Container for dynamically added project rows
        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(6)
        layout.addWidget(self._rows_container, 1)

        # Empty state shown when no projects exist
        self._empty_state = empty_state(
            "暂无资产。导入视频素材后，系统会在这里显示拆分场景、脚本、配音和导出记录。",
            180,
            padding=24,
        )
        layout.addWidget(self._empty_state, 1)

        # Initial load
        self.refresh_projects()
        return frame

    def refresh_projects(self) -> None:
        """Query the ProjectManager and repopulate the project list."""
        # Clear existing rows
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        projects = []
        if self._project_manager is not None:
            projects = self._project_manager.scan_projects()

        if not projects:
            self._empty_state.setVisible(True)
            self._rows_container.setVisible(False)
            return

        self._empty_state.setVisible(False)
        self._rows_container.setVisible(True)

        for project in projects:
            meta = project.metadata
            type_name = (
                meta.project_type.display_name
                if hasattr(meta.project_type, "display_name")
                else str(meta.project_type)
            )
            date_str = (meta.created_at or "")[:10] or "—"
            row = self._row(type_name, meta.name or "未命名项目", date_str, file_path=project.path)
            self._rows_layout.addWidget(row)

    def add_imported_files(self, file_paths: list[str]) -> None:
        """Add imported media files to the asset list display."""
        if not file_paths:
            return
        self._empty_state.setVisible(False)
        self._rows_container.setVisible(True)

        from datetime import date
        from pathlib import Path

        today = date.today().isoformat()
        for fp in file_paths:
            p = Path(fp)
            kind = p.suffix.lstrip(".").upper() or "文件"
            row = self._row(kind, p.name, today, file_path=fp)
            self._rows_layout.addWidget(row)

    def _build_source_panel(self) -> QFrame:
        frame = panel("source_panel")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        for item in ASSET_SOURCE_ITEMS:
            layout.addWidget(self._source_item(item.label, item.value))
        layout.addStretch()
        return frame

    def _row(
        self, kind: str, name: str, status: str, header: bool = False, file_path: str = ""
    ) -> QFrame:
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
            label.setFont(ui_font(FontSizes.xs, FontWeights.Medium))
            label.setStyleSheet(
                f"color: {_C.TEXT_MUTED if header else _C.TEXT_SECONDARY};"
            )
            layout.addWidget(label, stretch)

        if not header and file_path:
            row.setProperty("file_path", file_path)
            row.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu
            )
            row.customContextMenuRequested.connect(
                lambda pos, r=row: self._show_row_context_menu(pos, r)
            )
        return row

    # 卡片标题 → 对应设置项，点击后跳转到系统设置页面
    _NAVIGATE_ON_CLICK = {"素材目录", "输出目录"}

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
        title_label.setFont(ui_font(FontSizes.xs, FontWeights.Medium))
        title_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        layout.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        desc_label.setStyleSheet(f"color: {_C.TEXT_SECONDARY};")
        layout.addWidget(desc_label)

        # "素材目录"/"输出目录" 卡片：提供选择按钮，点击跳转到系统设置
        if title in self._NAVIGATE_ON_CLICK:
            layout.addStretch(1)
            btn = QPushButton("选择目录")
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {_C.BG_ELEVATED};
                    color: {_C.TEXT_PRIMARY};
                    border: 1px solid {_C.BORDER_DEFAULT};
                    border-radius: {Radii.sm};
                    padding: 4px 10px;
                    font-size: {FontSizes.xs}px;
                }}
                QPushButton:hover {{
                    background: {_C.PRIMARY};
                    color: #ffffff;
                }}
            """)
            btn.clicked.connect(lambda: self.navigate.emit("settings"))
            layout.addWidget(btn)

        return item

    def _show_row_context_menu(self, pos, row: QFrame):
        """Show right-click context menu for an asset row."""
        file_path = row.property("file_path")
        if not file_path:
            return

        menu = QMenu(self)
        open_action = menu.addAction("打开")
        reveal_action = menu.addAction("在 Finder 中显示")
        menu.addSeparator()
        delete_action = menu.addAction("删除")

        chosen = menu.exec(row.mapToGlobal(pos))
        if chosen is None:
            return

        from pathlib import Path

        if chosen == open_action:
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        elif chosen == reveal_action:
            parent = str(Path(file_path).parent)
            QDesktopServices.openUrl(QUrl.fromLocalFile(parent))
        elif chosen == delete_action:
            reply = QMessageBox.question(
                self,
                "确认删除",
                "确定要从列表中移除该项吗？\n（不会删除磁盘上的文件）",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._rows_layout.removeWidget(row)
                row.deleteLater()
                if self._rows_layout.count() == 0:
                    self._empty_state.setVisible(True)
                    self._rows_container.setVisible(False)

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
