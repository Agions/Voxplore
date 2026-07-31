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

from ...i18n import t
from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, ui_font
from .page_view_models import ASSET_SOURCE_ITEMS, ASSET_TABLE_COLUMNS
from .page_widgets import (
    PaletteAwareMixin,
    action_button,
    empty_state,
    header_panel,
    page_background_style,
    page_container,
    panel,
    scroll_area,
    section_title,
)
from .page_defaults import DEFAULT_EXPORT_DIR

if TYPE_CHECKING:
    from app.project.manager import ProjectManager

    from ...viewmodels.assets_viewmodel import AssetsPageViewModel


class AssetsPage(PaletteAwareMixin, QFrame):
    """Project and media assets workspace."""

    import_requested = Signal()
    navigate = Signal(str)

    def __init__(self, viewmodel: AssetsPageViewModel | None = None, parent=None, *, project_manager: ProjectManager | None = None):
        super().__init__(parent)
        self._init_palette_registry()
        self._vm = viewmodel
        self._project_manager = project_manager
        self.setObjectName("assets_page")
        # Cached widget references for retranslate()
        self._header_title_lbl: QLabel | None = None
        self._header_subtitle_lbl: QLabel | None = None
        self._header_action_btn = None
        self._asset_list_section: QLabel | None = None
        self._refresh_btn = None
        self._empty_state_widget = None
        self._column_labels: list[QLabel] = []
        # Track source items so retranslate can refresh them. Stores
        # (frame, title_label, desc_label, navigate_to, choose_btn).
        self._source_items: list[tuple[QFrame, QLabel,
                                       QLabel, str | None, QPushButton | None]] = []
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
        self._header_action_btn = action_button(
            t("assets.import_button"), primary=True)
        self._header_action_btn.clicked.connect(self._on_import_requested)
        header = header_panel(
            "assets_header",
            t("assets.header.title"),
            t("assets.header.subtitle"),
            self._header_action_btn,
        )
        labels = header.findChildren(QLabel)
        if labels:
            self._header_title_lbl = labels[0]
            if len(labels) > 1:
                self._header_subtitle_lbl = labels[1]
        return header

    def _build_asset_table(self) -> QFrame:
        frame = panel("asset_table")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        self._asset_list_section = section_title(
            t("assets.section.asset_list"))
        header_layout.addWidget(self._asset_list_section)
        header_layout.addStretch()
        self._refresh_btn = action_button(t("assets.refresh_button"))
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        header_layout.addWidget(self._refresh_btn)
        layout.addLayout(header_layout)

        columns = self._row(*ASSET_TABLE_COLUMNS, header=True, kind_keys=True)
        layout.addWidget(columns)

        # Container for dynamically added project rows
        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(6)
        layout.addWidget(self._rows_container, 1)

        # Empty state shown when no projects exist
        self._empty_state_widget = empty_state(
            t("assets.empty.placeholder"),
            180,
            padding=24,
        )
        layout.addWidget(self._empty_state_widget, 1)

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
            if self._empty_state_widget is not None:
                self._empty_state_widget.setVisible(True)
            self._rows_container.setVisible(False)
            return

        if self._empty_state_widget is not None:
            self._empty_state_widget.setVisible(False)
        self._rows_container.setVisible(True)

        for project in projects:
            meta = project.metadata
            type_name = (
                meta.project_type.display_name
                if hasattr(meta.project_type, "display_name")
                else str(meta.project_type)
            )
            date_str = (meta.created_at or "")[:10] or "—"
            row = self._row(type_name, meta.name or t("assets.unnamed_project"),
                            date_str, file_path=project.path)
            self._rows_layout.addWidget(row)

    def add_imported_files(self, file_paths: list[str]) -> None:
        """Add imported media files to the asset list display."""
        if not file_paths:
            return
        if self._empty_state_widget is not None:
            self._empty_state_widget.setVisible(False)
        self._rows_container.setVisible(True)

        from datetime import date
        from pathlib import Path

        today = date.today().isoformat()
        for fp in file_paths:
            p = Path(fp)
            kind = p.suffix.lstrip(".").upper() or t("assets.kind.file")
            row = self._row(kind, p.name, today, file_path=fp)
            self._rows_layout.addWidget(row)

    def _build_source_panel(self) -> QFrame:
        frame = panel("source_panel")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        for label_key, navigate_to, value_key in ASSET_SOURCE_ITEMS:
            layout.addWidget(self._source_item(
                label_key, value_key, navigate_to=navigate_to))
        layout.addStretch()
        return frame

    def _row(
        self,
        kind: str,
        name: str,
        status: str,
        header: bool = False,
        file_path: str = "",
        kind_keys: bool = False,
    ) -> QFrame:
        row = QFrame()
        row.setObjectName("asset_row")
        self._set_palette_style(row, lambda: f"""
            QFrame#asset_row {{
                background: {_C.BG_ELEVATED if header else _C.BG_BASE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
            }}
        """)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        labels: list[QLabel] = []
        for text, stretch in [(kind, 1), (name, 3), (status, 1)]:
            # For the table header row, treat values as i18n keys.
            display = t(text) if (header and kind_keys) else text
            label = QLabel(display)
            label.setFont(ui_font(FontSizes.xs, FontWeights.Medium))
            self._set_palette_style(
                label, lambda h=header: f"color: {_C.TEXT_MUTED if h else _C.TEXT_SECONDARY};")
            layout.addWidget(label, stretch)
            labels.append(label)

        if header:
            # Cache the header labels for retranslate()
            self._column_labels = labels
        elif file_path:
            row.setProperty("file_path", file_path)
            row.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu
            )
            row.customContextMenuRequested.connect(
                lambda pos, r=row: self._show_row_context_menu(pos, r)
            )
        return row

    # 卡片标题 → 导航到指定页（用结构化标记代替原文匹配）
    _NAVIGATE_PREFIX = ""

    def _source_item(self, label_key: str, value_key: str, *, navigate_to: str | None = None) -> QFrame:
        item = QFrame()
        item.setObjectName("source_item")
        self._set_palette_style(item, lambda: f"""
            QFrame#source_item {{
                background: {_C.BG_BASE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
            }}
        """)
        layout = QVBoxLayout(item)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(t(label_key))
        title_label.setFont(ui_font(FontSizes.xs, FontWeights.Medium))
        self._set_palette_style(
            title_label, lambda: f"color: {_C.TEXT_MUTED};")
        title_label.setProperty("i18n_key", label_key)
        layout.addWidget(title_label)

        # Display value: some keys are plain text, export_dir default uses path substitution
        if value_key == "assets.source.export_dir.value_default":
            desc_text = t(value_key).format(path=DEFAULT_EXPORT_DIR)
        else:
            desc_text = t(value_key)
        desc_label = QLabel(desc_text)
        desc_label.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        self._set_palette_style(
            desc_label, lambda: f"color: {_C.TEXT_SECONDARY};")
        desc_label.setProperty("i18n_key", value_key)
        layout.addWidget(desc_label)

        choose_btn: QPushButton | None = None
        if navigate_to:
            layout.addStretch(1)
            choose_btn = QPushButton(t("assets.choose_directory"))
            choose_btn.setFixedHeight(28)
            choose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._set_palette_style(choose_btn, lambda: f"""
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
            choose_btn.clicked.connect(lambda: self.navigate.emit(navigate_to))
            layout.addWidget(choose_btn)

        self._source_items.append(
            (item, title_label, desc_label, navigate_to, choose_btn))
        return item

    def _show_row_context_menu(self, pos, row: QFrame):
        """Show right-click context menu for an asset row."""
        file_path = row.property("file_path")
        if not file_path:
            return

        menu = QMenu(self)
        open_action = menu.addAction(t("assets.action.open"))
        reveal_action = menu.addAction(t("assets.action.reveal_finder"))
        menu.addSeparator()
        delete_action = menu.addAction(t("assets.action.delete"))

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
                t("assets.confirm_delete.title"),
                t("assets.confirm_delete.message"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._rows_layout.removeWidget(row)
                row.deleteLater()
                if self._rows_layout.count() == 0:
                    if self._empty_state_widget is not None:
                        self._empty_state_widget.setVisible(True)
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
                t("assets.empty.placeholder")
            )
        else:
            parts = []
            if summary.media_count:
                parts.append(f"{t('assets.kind.media')} {summary.media_count}")
            if summary.script_count:
                parts.append(
                    f"{t('assets.kind.script')} {summary.script_count}")
            if summary.audio_count:
                parts.append(f"{t('assets.kind.audio')} {summary.audio_count}")
            if summary.export_count:
                parts.append(
                    f"{t('assets.kind.export')} {summary.export_count}")
            self._asset_placeholder.setText(" · ".join(
                parts) or t("assets.placeholder.empty"))

    def _refresh_recent_summary(self) -> None:
        """Update recent projects summary line from VM state."""
        if self._vm is None or not hasattr(self, "_recent_summary_label"):
            return
        recents = self._vm.recent_projects
        if not recents:
            self._recent_summary_label.setText(t("assets.recent.empty"))
            return
        # 最多显示 3 个
        shown = recents[:3]
        names = [r.name for r in shown]
        if len(recents) > 3:
            suffix = t("assets.recent.summary_more").format(count=len(recents))
        else:
            suffix = ""
        self._recent_summary_label.setText(
            t("assets.recent.summary").format(
                names=", ".join(names), suffix=suffix)
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
        filter_str = t("assets.choose_files.filter")
        result: list[str] = []
        # Use getOpenFileNames (static) so the dialog doesn't block the
        # page on a non-Qt event loop. Returns ([paths], selectedFilter).
        result, _ = QFileDialog.getOpenFileNames(
            parent,
            t("assets.choose_files.title"),
            "",
            filter_str,
        )
        return list(result)

    def retranslate(self) -> None:
        """Refresh all user-visible strings after a language change."""
        # Header
        if self._header_title_lbl is not None:
            self._header_title_lbl.setText(t("assets.header.title"))
        if self._header_subtitle_lbl is not None:
            self._header_subtitle_lbl.setText(t("assets.header.subtitle"))
        if self._header_action_btn is not None:
            self._header_action_btn.setText(t("assets.import_button"))
        # Asset list section title + refresh button
        if self._asset_list_section is not None:
            self._asset_list_section.setText(t("assets.section.asset_list"))
        if self._refresh_btn is not None:
            self._refresh_btn.setText(t("assets.refresh_button"))
        # Empty state
        if self._empty_state_widget is not None:
            self._empty_state_widget.setText(t("assets.empty.placeholder"))
        # Column header row (assumes header layout order: kind, name, created)
        if self._column_labels:
            keys = ("assets.table.column.kind",
                    "assets.table.column.name", "assets.table.column.created")
            for lbl, key in zip(self._column_labels, keys):
                lbl.setText(t(key))
        # Source panel cards
        for _item, title_label, desc_label, _nav, choose_btn in self._source_items:
            # The labels were created from a (label_key, navigate_to, value_key) tuple
            # and we stash the keys on the labels themselves for retranslate.
            label_key = title_label.property("i18n_key")
            value_key = desc_label.property("i18n_key")
            if label_key:
                title_label.setText(t(label_key))
            if value_key:
                desc_text = (
                    t(value_key).format(path=DEFAULT_EXPORT_DIR)
                    if value_key == "assets.source.export_dir.value_default"
                    else t(value_key)
                )
                desc_label.setText(desc_text)
            if choose_btn is not None:
                choose_btn.setText(t("assets.choose_directory"))
