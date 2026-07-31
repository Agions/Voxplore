#!/usr/bin/env python3
"""Production workflow page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from ...i18n import t
from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, ui_font
from ..controls import ComboBox
from .page_view_models import (
    EXPORT_QUALITY_CHECKS,
    SCRIPT_BRIEF_RULES,
)
from .page_widgets import (
    PaletteAwareMixin,
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


_EMOTION_KEYS = (
    "production.emotion.neutral",
    "production.emotion.nostalgic",
    "production.emotion.melancholy",
    "production.emotion.cheerful",
    "production.emotion.calm",
    "production.emotion.gentle",
    "production.emotion.excited",
)


class VideoDropzoneFrame(PaletteAwareMixin, QFrame):
    """Interactive drag and drop container for source video files."""

    file_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_palette_registry()
        self.setAcceptDrops(True)
        self.selected_path: str = ""
        # Track whether the file has been selected so retranslate() can refresh
        # the title / browse button labels appropriately.
        self._file_present = False
        self._setup_ui()

    def _setup_ui(self):
        self._set_palette_style(self, lambda: f"""
            QFrame {{
                background: {_C.BG_BASE};
                border: 2px dashed {_C.PRIMARY};
                border-radius: {Radii.lg};
                padding: 16px;
            }}
            QFrame:hover {{
                background: {_C.BG_SURFACE};
                border-color: {_C.PRIMARY};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self._icon_lbl = QLabel("🎬")
        self._icon_lbl.setFont(ui_font(32))
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon_lbl)

        self._title_lbl = QLabel(t("production.drop_hint"))
        self._title_lbl.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        self._set_palette_style(
            self._title_lbl, lambda: f"color: {_C.TEXT_PRIMARY};")
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_lbl)

        self._path_lbl = QLabel(t("production.format_supported"))
        self._path_lbl.setFont(ui_font(FontSizes.xs))
        self._set_palette_style(
            self._path_lbl, lambda: f"color: {_C.TEXT_MUTED};")
        self._path_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._path_lbl)

        self._browse_btn = action_button(t("production.browse_button"))
        self._browse_btn.clicked.connect(self._on_browse)
        layout.addWidget(self._browse_btn, 0, Qt.AlignmentFlag.AlignCenter)

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("production.browse_dialog_title"),
            "",
            t("production.video_filter"),
        )
        if path:
            self.set_file(path)

    def set_file(self, path: str):
        self.selected_path = path
        import os

        basename = os.path.basename(path)
        self._icon_lbl.setText("📹")
        self._title_lbl.setText(
            t("production.video_selected").format(name=basename))
        self._path_lbl.setText(path)
        self._browse_btn.setText(t("production.replace_video"))
        self._file_present = True
        self.file_selected.emit(path)

    def retranslate(self) -> None:
        """Refresh all user-visible strings after a language change."""
        if self._file_present:
            # selected state — show file path line, replace button label, file name in title
            basename = ""
            if self.selected_path:
                import os
                basename = os.path.basename(self.selected_path)
            self._title_lbl.setText(
                t("production.video_selected").format(name=basename))
            self._path_lbl.setText(self.selected_path)
            self._browse_btn.setText(t("production.replace_video"))
        else:
            self._title_lbl.setText(t("production.drop_hint"))
            self._path_lbl.setText(t("production.format_supported"))
            self._browse_btn.setText(t("production.browse_button"))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(
                    (".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv")
                ):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(
                (".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv")
            ):
                self.set_file(path)
                event.acceptProposedAction()
                break


class ProductionPage(PaletteAwareMixin, QFrame):
    """Structured workflow for first-person narration production.

    Phase 2B: 5-step pipeline + per-step status are read from
    :class:`ProductionPageViewModel`. The view renders them declaratively
    and forwards ``start_requested`` clicks to ``vm.start_pipeline()``.
    """

    start_requested = Signal()
    cancel_requested = Signal()

    def __init__(self, viewmodel: ProductionPageViewModel | None = None, parent=None):
        super().__init__(parent)
        self._init_palette_registry()
        self.setAcceptDrops(True)
        self._vm = viewmodel
        self.setObjectName("production_page")
        self._step_statuses: dict[str, QLabel] = {}
        self._step_status_keys: dict[str, str] = {}
        # Cached header references for retranslate()
        self._header_title_key = "home.header.title"
        self._header_subtitle_key = "production.header.subtitle"
        self._header_title_lbl: QLabel | None = None
        self._header_subtitle_lbl: QLabel | None = None
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
        self._start_btn = action_button(t("production.start_ai"), primary=True)
        self._start_btn.clicked.connect(self._on_start_clicked)

        self._cancel_btn = action_button(t("production.run.cancel"))
        self._cancel_btn.clicked.connect(self.cancel_requested.emit)
        self._cancel_btn.hide()

        header = header_panel(
            "production_header",
            t(self._header_title_key),
            t(self._header_subtitle_key),
            self._start_btn,
            self._cancel_btn,
        )
        # Locate the title / subtitle labels inside the header for retranslate().
        labels = header.findChildren(QLabel)
        if labels:
            self._header_title_lbl = labels[0]
            if len(labels) > 1:
                self._header_subtitle_lbl = labels[1]
        return header

    def _on_start_clicked(self) -> None:
        video_path = getattr(self.dropzone, "selected_path", "")
        context = self._context_input.text().strip() or t("production.theme_default")
        emotion = self._emotion_combo.currentText().split()[0]

        self.start_requested.emit()
        window = self.window()
        if window is not None and hasattr(window, "_start_production_with_video"):
            if not video_path:
                from PySide6.QtWidgets import QFileDialog

                video_path, _ = QFileDialog.getOpenFileName(
                    self,
                    t("production.browse_dialog_title"),
                    "",
                    t("production.video_filter"),
                )
                if not video_path:
                    return
                self.dropzone.set_file(video_path)

            window._start_production_with_video(video_path, context, emotion)

    def _build_pipeline(self) -> QFrame:
        frame = panel("production_pipeline")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        self._pipeline_section = section_title(
            t("production.section.media_import"))
        layout.addWidget(self._pipeline_section)

        # 视频拖拽区域
        self.dropzone = VideoDropzoneFrame(self)
        layout.addWidget(self.dropzone)

        # 行内参数配置面板
        config_frame = QFrame()
        self._set_palette_style(config_frame, lambda: f"""
            QFrame {{
                background: {_C.BG_BASE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.base};
                padding: 12px;
            }}
        """)
        config_layout = QVBoxLayout(config_frame)
        config_layout.setSpacing(10)

        # 解说主题输入
        context_box = QHBoxLayout()
        self._ctx_label = QLabel(t("production.theme_label"))
        self._ctx_label.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        self._set_palette_style(
            self._ctx_label, lambda: f"color: {_C.TEXT_PRIMARY};")
        self._context_input = QLineEdit(t("production.theme_default"))
        self._context_input.setPlaceholderText(
            t("production.theme_placeholder"))
        self._set_palette_style(self._context_input, lambda: f"""
            QLineEdit {{
                background: {_C.BG_SURFACE};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
                padding: 6px 10px;
            }}
        """)
        context_box.addWidget(self._ctx_label)
        context_box.addWidget(self._context_input, 1)
        config_layout.addLayout(context_box)

        # 情感风格下拉选择
        emotion_box = QHBoxLayout()
        self._emo_label = QLabel(t("production.tone_label"))
        self._emo_label.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        self._set_palette_style(
            self._emo_label, lambda: f"color: {_C.TEXT_PRIMARY};")
        self._emotion_combo = ComboBox()
        self._emotion_combo.addItems([t(key) for key in _EMOTION_KEYS])
        self._set_palette_style(self._emotion_combo, lambda: f"""
            QComboBox {{
                background: {_C.BG_SURFACE};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
                padding: 6px 32px 6px 10px;
            }}
            QComboBox::down-arrow {{
                image: none;
            }}
        """)
        emotion_box.addWidget(self._emo_label)
        emotion_box.addWidget(self._emotion_combo, 1)
        config_layout.addLayout(emotion_box)

        layout.addWidget(config_frame)

        self._steps_section = section_title(
            t("production.section.workflow_steps"))
        layout.addWidget(self._steps_section)

        # Phase 2B: read 5 steps from VM (falls back to canon if no VM)
        steps = self._step_definitions()
        self._step_rows: list[tuple[QFrame, QLabel | None,
                                    QLabel | None, QLabel | None, str, str]] = []
        for number, name, desc in steps:
            row = self._step_row(number, name, desc)
            layout.addWidget(row)
            badge = row.findChild(QLabel, "step_badge")
            title = row.findChild(QLabel, "step_title")
            status_lbl = row.findChild(QLabel, "step_status")
            self._step_rows.append(
                (row, badge, title, status_lbl, number, name))
            # Cache the initial pending translation so retranslate() can detect
            # labels still in the default state and refresh only those.
            self._step_status_keys[name] = t("production.status.pending")
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
        self._brief_section = section_title(t("production.section.brief"))
        layout.addWidget(self._brief_section)

        for rule in SCRIPT_BRIEF_RULES:
            layout.addWidget(key_value_row(rule.label, rule.value))
        layout.addStretch()
        return frame

    def _build_quality_gate(self) -> QFrame:
        frame = panel("quality_gate")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        self._quality_section = section_title(
            t("production.section.quality_gate"))
        layout.addWidget(self._quality_section)

        for item in EXPORT_QUALITY_CHECKS:
            layout.addWidget(self._check_item(item))
        layout.addStretch()
        return frame

    def _step_row(self, number: str, name: str, desc: str) -> QFrame:
        row = QFrame()
        row.setObjectName("production_step_row")
        self._set_palette_style(row, lambda: f"""
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
        self._set_palette_style(badge, lambda: f"color: {_C.PRIMARY};")
        layout.addWidget(badge)

        copy = QVBoxLayout()
        copy.setSpacing(2)
        title = QLabel(name)
        title.setObjectName("step_title")
        title.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        self._set_palette_style(title, lambda: f"color: {_C.TEXT_PRIMARY};")
        copy.addWidget(title)
        detail = QLabel(desc)
        detail.setFont(ui_font(FontSizes.xs))
        self._set_palette_style(detail, lambda: f"color: {_C.TEXT_MUTED};")
        copy.addWidget(detail)
        layout.addLayout(copy, 1)

        status = QLabel(t("production.status.pending"))
        status.setObjectName("step_status")
        status.setFont(ui_font(FontSizes.xs))
        self._set_palette_style(status, lambda: f"color: {_C.TEXT_DISABLED};")
        layout.addWidget(status)
        self._step_statuses[name] = status
        return row

    def _check_item(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(ui_font(FontSizes.sm))
        self._set_palette_style(label, lambda: f"""
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
        """Reset all step status labels to the default pending state."""
        pending = t("production.status.pending")
        for label in self._step_statuses.values():
            label.setText(pending)
            label.setStyleSheet(f"color: {_C.TEXT_DISABLED};")

    def retranslate(self) -> None:
        """Refresh all user-visible strings after a language change."""
        # Header
        if self._header_title_lbl is not None:
            self._header_title_lbl.setText(t(self._header_title_key))
        if self._header_subtitle_lbl is not None:
            self._header_subtitle_lbl.setText(t(self._header_subtitle_key))
        # Top action buttons
        self._start_btn.setText(t("production.start_ai"))
        self._cancel_btn.setText(t("production.run.cancel"))
        # Section titles
        if hasattr(self, "_pipeline_section"):
            self._pipeline_section.setText(
                t("production.section.media_import"))
        if hasattr(self, "_steps_section"):
            self._steps_section.setText(t("production.section.workflow_steps"))
        if hasattr(self, "_brief_section"):
            self._brief_section.setText(t("production.section.brief"))
        if hasattr(self, "_quality_section"):
            self._quality_section.setText(t("production.section.quality_gate"))
        # Form labels
        if hasattr(self, "_ctx_label"):
            self._ctx_label.setText(t("production.theme_label"))
        if hasattr(self, "_emo_label"):
            self._emo_label.setText(t("production.tone_label"))
        # Placeholder only (don't clobber user input)
        self._context_input.setPlaceholderText(
            t("production.theme_placeholder"))
        # Emotion combo: rebuild every visible item from the canonical
        # ``_EMOTION_KEYS`` so language switches update both label and
        # placeholder/selectable text. ``setItemText`` keeps the existing
        # data slot intact so user selections survive the retranslate.
        for index, key in enumerate(_EMOTION_KEYS):
            if index < self._emotion_combo.count():
                self._emotion_combo.setItemText(index, t(key))
        # Dropzone
        self.dropzone.retranslate()
        # Step status: VM is the source of truth for runtime state. We only
        # refresh labels still displaying the initial pending text (matched by
        # their cached previous translation) so an in-flight pipeline isn't
        # flashed back to pending mid-run.
        if self._step_status_keys:
            for name, label in self._step_statuses.items():
                previous = self._step_status_keys.get(name)
                if previous and label.text() == previous:
                    label.setText(t("production.status.pending"))
            self._step_status_keys = {
                name: t("production.status.pending")
                for name in self._step_statuses
            }

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
