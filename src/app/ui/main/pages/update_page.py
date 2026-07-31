#!/usr/bin/env python3
"""Software update page (v2.5).

Renders the full upgrade pipeline UI driven by :class:`UpdaterService`:

* Channel selector (stable/beta)
* Check button → triggers ``UpdaterService.check()`` in a worker thread
* Download/Install button → triggers the full pipeline
* Retry / Skip / Rollback buttons to recover from failure
* Progress bar, stage label, speed readout
* Release notes (when the manifest provides them)
* Backup list (from :py:meth:`UpdaterService.list_backups`)

All state changes flow through QObject signals exposed by the service,
so the page never has to touch worker threads or REST endpoints
directly.  When PySide6 is unavailable (e.g. unit tests) the page
degrades to a stub widget that prints the i18n key.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...i18n import t
from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, ui_font
from .page_widgets import (
    PaletteAwareMixin,
    action_button_style,
    header_panel,
    page_background_style,
    page_container,
    panel,
    scroll_area,
    section_title,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Worker threads — long-running calls (check / download / rollback)
# ─────────────────────────────────────────────────────────────────────


class _UpdateWorker(QThread):
    """Wrapper around :class:`UpdaterService` methods running off the UI thread.

    Emits ``finished_ok(bool)`` and ``failed(str)`` so the page can react
    in the GUI thread.  We reuse :class:`QThread` (rather than
    :class:`threading.Thread`) so the worker shares the Qt event loop
    boundary and signal/slot marshalling works out of the box.
    """

    failed = Signal(str)
    finished_ok = Signal(bool)

    def __init__(
        self,
        service: Any,
        action: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self._service = service
        self._action = action
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:  # noqa: D401 — Qt override
        try:
            method = getattr(self._service, self._action)
            result = method(*self._args, **self._kwargs)
            self.finished_ok.emit(
                bool(result)) if result is not None else self.finished_ok.emit(True)
        except Exception as exc:  # pragma: no cover - safety net
            logger.exception("Updater worker %s failed", self._action)
            self.failed.emit(str(exc))


# ─────────────────────────────────────────────────────────────────────
# Page widget
# ─────────────────────────────────────────────────────────────────────


class UpdatePage(PaletteAwareMixin, QFrame):
    """Upgrade UI bound to a single :class:`UpdaterService` instance."""

    # Navigational intents (consumed by the main window).
    navigate = Signal(str)

    def __init__(self, service: Any | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._init_palette_registry()
        self.setObjectName("update_page")
        self._service = service
        self._worker: _UpdateWorker | None = None
        self._skipped_versions: set[str] = set()

        # i18n bookkeeping for retranslate
        self._i18n_labels: list[tuple[QLabel, str]] = []
        self._i18n_buttons: list[tuple[QPushButton, str]] = []
        self._header_title_lbl: QLabel | None = None
        self._header_subtitle_lbl: QLabel | None = None

        # widget references
        self._channel_combo: QComboBox | None = None
        self._current_version_lbl: QLabel | None = None
        self._latest_version_lbl: QLabel | None = None
        self._stage_lbl: QLabel | None = None
        self._speed_lbl: QLabel | None = None
        self._progress_bar: QProgressBar | None = None
        self._release_notes: QPlainTextEdit | None = None
        self._error_lbl: QLabel | None = None
        self._check_btn: QPushButton | None = None
        self._download_btn: QPushButton | None = None
        self._retry_btn: QPushButton | None = None
        self._skip_btn: QPushButton | None = None
        self._rollback_btn: QPushButton | None = None
        self._backups_panel: QFrame | None = None
        self._backups_layout: QVBoxLayout | None = None

        self._setup_style()
        self._setup_ui()
        self._wire_service_signals()
        self._refresh_state()

    # ──────────────────────────────────────────────────────────────────
    # 样式 & 布局
    # ──────────────────────────────────────────────────────────────────

    def _setup_style(self) -> None:
        self.setStyleSheet(page_background_style("update_page"))

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = scroll_area()
        container = page_container()
        layout = container.layout()
        assert layout is not None

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_status_panel())
        layout.addWidget(self._build_actions_panel())
        layout.addWidget(self._build_release_notes_panel())
        layout.addWidget(self._build_backups_panel())
        layout.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll)

    def _build_header(self) -> QFrame:
        header = header_panel(
            "update_header",
            t("update.header.title"),
            t("update.header.subtitle"),
        )
        labels = header.findChildren(QLabel)
        if labels:
            self._header_title_lbl = labels[0]
            if len(labels) > 1:
                self._header_subtitle_lbl = labels[1]
        return header

    def _build_status_panel(self) -> QFrame:
        frame = panel("update_status")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        title = section_title(t("update.progress.label"))
        layout.addWidget(title)
        self._i18n_labels.append((title, "update.progress.label"))

        # 进度条
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setTextVisible(True)
        progress.setFixedHeight(18)
        progress.setStyleSheet(self._progress_style())
        self._progress_bar = progress
        layout.addWidget(progress)

        # 阶段 + 速度 横向显示
        info_row = QHBoxLayout()
        info_row.setSpacing(16)

        stage_lbl = QLabel(t("update.status.idle"))
        stage_lbl.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        stage_lbl.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        self._stage_lbl = stage_lbl

        speed_lbl = QLabel("")
        speed_lbl.setFont(ui_font(FontSizes.xs))
        speed_lbl.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        self._speed_lbl = speed_lbl

        info_row.addWidget(stage_lbl)
        info_row.addSpacing(12)
        info_row.addWidget(speed_lbl)
        info_row.addStretch()
        layout.addLayout(info_row)

        # 版本信息
        version_row = QHBoxLayout()
        version_row.setSpacing(12)

        current_box, current_lbl = self._key_value_box(
            "update.version.current", self._current_version_text()
        )
        latest_box, latest_lbl = self._key_value_box(
            "update.version.latest", self._latest_version_text()
        )
        channel_box, channel_combo = self._channel_selector()

        self._current_version_lbl = current_lbl
        self._latest_version_lbl = latest_lbl
        self._channel_combo = channel_combo

        version_row.addWidget(current_box, 1)
        version_row.addWidget(latest_box, 1)
        version_row.addWidget(channel_box, 1)
        layout.addLayout(version_row)

        # 错误展示
        error_lbl = QLabel("")
        error_lbl.setObjectName("update_error_label")
        error_lbl.setWordWrap(True)
        error_lbl.setStyleSheet(f"""
            color: {_C.ERROR};
            background: rgba(220, 38, 38, 0.08);
            border: 1px solid rgba(220, 38, 38, 0.18);
            border-radius: {Radii.sm};
            padding: 8px 12px;
        """)
        error_lbl.hide()
        self._error_lbl = error_lbl
        layout.addWidget(error_lbl)

        return frame

    def _build_actions_panel(self) -> QFrame:
        frame = panel("update_actions")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        check_btn = self._make_button(
            "update.button.check", primary=True, slot=self._on_check_clicked
        )
        download_btn = self._make_button(
            "update.button.download", primary=False, slot=self._on_download_clicked
        )
        retry_btn = self._make_button(
            "update.button.retry", primary=False, slot=self._on_retry_clicked
        )
        skip_btn = self._make_button(
            "update.button.skip", primary=False, slot=self._on_skip_clicked
        )

        layout.addWidget(check_btn)
        layout.addWidget(download_btn)
        layout.addWidget(retry_btn)
        layout.addWidget(skip_btn)
        layout.addStretch()

        self._check_btn = check_btn
        self._download_btn = download_btn
        self._retry_btn = retry_btn
        self._skip_btn = skip_btn

        # 默认禁用次要按钮
        self._set_button_enabled(download_btn, False)
        self._set_button_enabled(retry_btn, False)
        self._set_button_enabled(skip_btn, False)
        return frame

    def _build_release_notes_panel(self) -> QFrame:
        frame = panel("update_release_notes")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        title = section_title(t("update.release_notes"))
        self._i18n_labels.append((title, "update.release_notes"))
        layout.addWidget(title)

        notes = QPlainTextEdit()
        notes.setReadOnly(True)
        notes.setMinimumHeight(140)
        notes.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {_C.BG_ELEVATED};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
                color: {_C.TEXT_SECONDARY};
                padding: 10px 12px;
                font-size: {FontSizes.xs}px;
            }}
        """)
        self._release_notes = notes
        layout.addWidget(notes)
        return frame

    def _build_backups_panel(self) -> QFrame:
        frame = panel("update_backups")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title = section_title(t("update.backups.label"))
        title_row.addWidget(title)
        title_row.addStretch()

        rollback_btn = self._make_button(
            "update.button.rollback",
            primary=False,
            slot=self._on_rollback_first_clicked,
        )
        title_row.addWidget(rollback_btn)
        self._rollback_btn = rollback_btn

        layout.addLayout(title_row)
        self._i18n_labels.append((title, "update.backups.label"))

        self._backups_panel = frame
        self._backups_layout = layout

        # 初始占位
        placeholder = QLabel(t("update.backups.empty"))
        placeholder.setStyleSheet(f"color: {_C.TEXT_DISABLED};")
        self._i18n_labels.append((placeholder, "update.backups.empty"))
        layout.addWidget(placeholder)
        return frame

    # ──────────────────────────────────────────────────────────────────
    # 微件构造辅助
    # ──────────────────────────────────────────────────────────────────

    def _key_value_box(
        self, key: str, value: str
    ) -> tuple[QFrame, QLabel]:
        wrapper = QFrame()
        wrapper.setStyleSheet(f"""
            QFrame {{
                background: {_C.BG_ELEVATED};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
            }}
            QFrame QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        key_lbl = QLabel(t(key))
        key_lbl.setFont(ui_font(FontSizes.xs))
        key_lbl.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        self._i18n_labels.append((key_lbl, key))

        val_lbl = QLabel(value)
        val_lbl.setFont(ui_font(FontSizes.sm, FontWeights.SemiBold))
        val_lbl.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")

        layout.addWidget(key_lbl)
        layout.addWidget(val_lbl)
        return wrapper, val_lbl

    def _channel_selector(self) -> tuple[QFrame, QComboBox]:
        wrapper = QFrame()
        wrapper.setStyleSheet(f"""
            QFrame {{
                background: {_C.BG_ELEVATED};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
            }}
            QFrame QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        key_lbl = QLabel(t("update.channel.label"))
        key_lbl.setFont(ui_font(FontSizes.xs))
        key_lbl.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        self._i18n_labels.append((key_lbl, "update.channel.label"))

        combo = QComboBox()
        combo.addItem(t("update.channel.stable"), "stable")
        combo.addItem(t("update.channel.beta"), "beta")
        combo.currentIndexChanged.connect(self._on_channel_changed)
        combo.setStyleSheet(self._input_style())
        layout.addWidget(combo)

        # 重绘时回填
        # type: ignore[attr-defined]
        self._channel_labels: list[QPushButton] = []
        return wrapper, combo

    def _make_button(
        self,
        key: str,
        *,
        primary: bool,
        slot: Any,
    ) -> QPushButton:
        btn = QPushButton(t(key))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(34)
        btn.setStyleSheet(action_button_style(primary=primary))
        btn.clicked.connect(slot)
        self._i18n_buttons.append((btn, key))
        return btn

    # ──────────────────────────────────────────────────────────────────
    # 状态分发
    # ──────────────────────────────────────────────────────────────────

    def _wire_service_signals(self) -> None:
        service = self._service
        if service is None or service.signals is None:
            return
        signals = service.signals
        if signals is None:
            return
        try:
            signals.stage_changed.connect(self._on_stage_changed)
            signals.progress_changed.connect(self._on_progress_changed)
            signals.update_available.connect(self._on_update_available)
            signals.update_unavailable.connect(self._on_update_unavailable)
            signals.install_complete.connect(self._on_install_complete)
            signals.rolled_back.connect(self._on_rolled_back)
            signals.error_occurred.connect(self._on_error_occurred)
        except (AttributeError, TypeError):
            logger.debug("UpdaterService signals not fully available")

    def set_service(self, service: Any) -> None:
        """替换底层 service（主要用于测试）。"""
        self._service = service
        self._wire_service_signals()
        self._refresh_state()

    # ──────────────────────────────────────────────────────────────────
    # Slot — service 信号回调
    # ──────────────────────────────────────────────────────────────────

    @Slot(str)
    def _on_stage_changed(self, stage: str) -> None:
        # stage 是 UpdateStage.value，比如 "checking", "downloading"
        stage_key = f"update.status.{stage}"
        try:
            translated = t(stage_key)
        except Exception:
            translated = stage
        if self._stage_lbl is not None:
            self._stage_lbl.setText(translated)
        self._refresh_state()

    @Slot(int, str)
    def _on_progress_changed(self, percent: int, message: str) -> None:
        if self._progress_bar is not None:
            self._progress_bar.setValue(max(0, min(100, int(percent))))
        service = self._service
        if self._speed_lbl is not None and service is not None:
            try:
                speed = max(0.0, float(
                    getattr(service.state, "progress_speed_bps", 0.0)))
            except Exception:
                speed = 0.0
            if speed > 0:
                self._speed_lbl.setText(
                    f"{t('update.progress.speed')}: {self._format_speed(speed)}"
                )
            else:
                self._speed_lbl.setText("")

    @Slot(object)
    def _on_update_available(self, manifest: Any) -> None:
        if self._latest_version_lbl is not None:
            version = getattr(manifest, "version", "") or ""
            if version in self._skipped_versions:
                self._latest_version_lbl.setText(version + " (skipped)")
            else:
                self._latest_version_lbl.setText(version)
        if self._release_notes is not None:
            notes = getattr(manifest, "release_notes", "") or ""
            self._release_notes.setPlainText(notes)
        if self._error_lbl is not None:
            self._error_lbl.hide()
        self._refresh_state()
        self._maybe_show_install_dialog(manifest)

    @Slot()
    def _on_update_unavailable(self) -> None:
        if self._latest_version_lbl is not None:
            self._latest_version_lbl.setText(t("update.status.idle"))
        if self._release_notes is not None:
            self._release_notes.setPlainText("")
        self._refresh_state()

    @Slot(str)
    def _on_install_complete(self, version: str) -> None:
        QMessageBox.information(
            self,
            t("update.header.title"),
            t("update.notification.downloaded", version=version),
        )
        if self._current_version_lbl is not None:
            self._current_version_lbl.setText(version)
        if self._progress_bar is not None:
            self._progress_bar.setValue(100)
        self._refresh_state()
        self._reload_backups()

    @Slot(str)
    def _on_rolled_back(self, version: str) -> None:
        QMessageBox.information(
            self,
            t("update.header.title"),
            t("update.status.rolled_back") + f": v{version}",
        )
        if self._current_version_lbl is not None:
            self._current_version_lbl.setText(version)
        self._refresh_state()
        self._reload_backups()

    @Slot(str, str)
    def _on_error_occurred(self, code: str, message: str) -> None:
        if self._error_lbl is None:
            return
        msg = t(
            "update.error." + self._error_message_key(code),
            error=message,
        )
        self._error_lbl.setText(f"[{code}] {msg}")
        self._error_lbl.show()
        # 校验失败 — 给一个 modal 弹窗让用户选 retry / 切全量
        if code == "UPDATE_VERIFY_FAILED":
            QMessageBox.warning(
                self,
                t("update.dialog.verify_failed.title"),
                t("update.dialog.verify_failed.message"),
            )

    # ──────────────────────────────────────────────────────────────────
    # Slot — 按钮回调
    # ──────────────────────────────────────────────────────────────────

    def _on_check_clicked(self) -> None:
        service = self._service
        if service is None:
            return
        self._run_worker(service, "check", timeout=10.0)
        self._set_button_enabled(self._check_btn, False)

    def _on_download_clicked(self) -> None:
        service = self._service
        if service is None:
            return
        manifest = service.state.manifest
        if manifest is None:
            QMessageBox.warning(
                self,
                t("update.error.no_manifest"),
                t("update.error.no_manifest"),
            )
            return
        self._run_worker(service, "download_and_install", manifest)

    def _on_retry_clicked(self) -> None:
        """重试当前失败阶段（直接重新触发 download_and_install）。"""
        service = self._service
        if service is None:
            return
        manifest = service.state.manifest
        if manifest is None:
            self._on_check_clicked()
            return
        if self._error_lbl is not None:
            self._error_lbl.hide()
        self._run_worker(service, "download_and_install", manifest)

    def _on_skip_clicked(self) -> None:
        service = self._service
        if service is None:
            return
        manifest = service.state.manifest
        if manifest is None:
            return
        version = getattr(manifest, "version", None)
        if version:
            self._skipped_versions.add(version)
        if self._latest_version_lbl is not None:
            self._latest_version_lbl.setText(version + " (skipped)")
        self._refresh_state()

    def _on_rollback_first_clicked(self) -> None:
        service = self._service
        if service is None:
            return
        records = self._safe_list_backups(service)
        if not records:
            QMessageBox.information(
                self,
                t("update.dialog.confirm_rollback.title"),
                t("update.backups.empty"),
            )
            return
        target = records[0]
        self._confirm_and_rollback(service, target.version)

    def _on_rollback_specific_clicked(self, version: str) -> None:
        service = self._service
        if service is None:
            return
        self._confirm_and_rollback(service, version)

    # ──────────────────────────────────────────────────────────────────
    # Worker 调度
    # ──────────────────────────────────────────────────────────────────

    def _run_worker(self, service: Any, action: str, *args: Any, **kwargs: Any) -> None:
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(
                self,
                t("update.header.title"),
                t("update.status.downloading"),
            )
            return
        worker = _UpdateWorker(service, action, *args, **kwargs)
        worker.finished_ok.connect(
            lambda ok: self._on_worker_finished(worker, ok))
        worker.failed.connect(lambda exc: self._on_worker_failed(worker, exc))
        worker.finished.connect(lambda: self._on_worker_cleared(worker))
        self._worker = worker
        worker.start()

    def _on_worker_finished(self, worker: _UpdateWorker, ok: bool) -> None:
        if self._progress_bar is not None:
            self._progress_bar.setValue(
                100 if ok else self._progress_bar.value())
        self._refresh_state()
        if worker is self._worker:
            self._worker = None

    def _on_worker_failed(self, worker: _UpdateWorker, exc: str) -> None:
        if self._error_lbl is not None:
            self._error_lbl.setText(exc)
            self._error_lbl.show()
        self._refresh_state()
        if worker is self._worker:
            self._worker = None

    def _on_worker_cleared(self, worker: _UpdateWorker) -> None:
        worker.deleteLater()

    # ──────────────────────────────────────────────────────────────────
    # 备份管理
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_list_backups(service: Any) -> list[Any]:
        installer = getattr(service, "_installer", None)
        if installer is None:
            return []
        try:
            return list(installer.list_backups())
        except Exception:
            return []

    def _reload_backups(self) -> None:
        if self._backups_layout is None:
            return
        # 清空旧内容（保留 title row 已经在 _build_backups_panel 内，
        # 实际我们重置整个面板内容更安全）
        while self._backups_layout.count():
            item = self._backups_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        title_row = QHBoxLayout()
        title = section_title(t("update.backups.label"))
        title_row.addWidget(title)
        title_row.addStretch()

        rollback_btn = self._make_button(
            "update.button.rollback",
            primary=False,
            slot=self._on_rollback_first_clicked,
        )
        title_row.addWidget(rollback_btn)
        self._rollback_btn = rollback_btn
        self._backups_layout.addLayout(title_row)
        self._i18n_labels.append((title, "update.backups.label"))

        records = self._safe_list_backups(
            self._service) if self._service else []
        if not records:
            placeholder = QLabel(t("update.backups.empty"))
            placeholder.setStyleSheet(f"color: {_C.TEXT_DISABLED};")
            self._i18n_labels.append((placeholder, "update.backups.empty"))
            self._backups_layout.addWidget(placeholder)
            return

        for record in records:
            self._backups_layout.addWidget(self._build_backup_row(record))
        self._backups_layout.addStretch()

    def _build_backup_row(self, record: Any) -> QFrame:
        row = QFrame()
        row.setStyleSheet(f"""
            QFrame#update_backup_row {{
                background: {_C.BG_ELEVATED};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
            }}
        """)
        row.setObjectName("update_backup_row")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(2)

        version_lbl = QLabel(t("update.backup.version") +
                             f": {record.version}")
        version_lbl.setStyleSheet(
            f"color: {_C.TEXT_PRIMARY}; font-weight: {FontWeights.SemiBold};")
        info.addWidget(version_lbl)

        created_lbl = QLabel(t("update.backup.created") +
                             f": {record.created_at}")
        created_lbl.setStyleSheet(
            f"color: {_C.TEXT_MUTED}; font-size: {FontSizes.xs}px;")
        info.addWidget(created_lbl)
        layout.addLayout(info, 1)

        btn = QPushButton(t("update.backup.rollback"))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(28)
        btn.setStyleSheet(action_button_style(primary=False, padding=10))
        btn.clicked.connect(
            lambda _=False, v=record.version: self._on_rollback_specific_clicked(v))
        self._i18n_buttons.append((btn, "update.backup.rollback"))
        layout.addWidget(btn)
        return row

    # ──────────────────────────────────────────────────────────────────
    # 杂项
    # ──────────────────────────────────────────────────────────────────

    def _confirm_and_rollback(self, service: Any, version: str) -> None:
        confirmed = QMessageBox.question(
            self,
            t("update.dialog.confirm_rollback.title"),
            t("update.dialog.confirm_rollback.message", version=version),
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return
        self._run_worker(service, "rollback_to", version)

    def _maybe_show_install_dialog(self, manifest: Any) -> None:
        confirmed = QMessageBox.question(
            self,
            t("update.dialog.confirm_install.title"),
            t("update.dialog.confirm_install.message",
              version=getattr(manifest, "version", "")),
        )
        if confirmed == QMessageBox.StandardButton.Yes:
            service = self._service
            if service is not None:
                self._run_worker(service, "download_and_install", manifest)

    def _on_channel_changed(self, index: int) -> None:
        if self._channel_combo is None or self._service is None:
            return
        channel = self._channel_combo.itemData(index)
        try:
            from app.updater import UpdateChannel, UpdaterService

            if channel in {c.value for c in UpdateChannel}:
                # 重建 service 时切 channel（最简方案：调 setter 或重实例化）
                current = getattr(self._service, "_channel",
                                  UpdateChannel.STABLE)
                if current.value != channel:
                    new_service = UpdaterService.from_settings(
                        channel=UpdateChannel(channel))
                    self.set_service(new_service)
        except Exception:
            logger.debug("Failed to switch channel", exc_info=True)

    def _refresh_state(self) -> None:
        service = self._service
        state = getattr(service, "state",
                        None) if service is not None else None
        stage = getattr(state, "stage", None) if state is not None else None

        # IDLE → 仅 check 可点；AVAILABLE → check + download + skip；
        # DOWNLOADING/VERIFYING/INSTALLING → 仅 retry 可点；
        # DONE/ROLLED_BACK → 重置为 IDLE
        if stage is None:
            self._set_button_enabled(self._check_btn, True)
            self._set_button_enabled(self._download_btn, False)
            self._set_button_enabled(self._retry_btn, False)
            self._set_button_enabled(self._skip_btn, False)
            return

        stage_value = getattr(stage, "value", str(stage))
        busy = stage_value in {"downloading",
                               "verifying", "installing", "checking"}
        available = stage_value == "available"
        failed = stage_value in {"failed", "rolled_back"}

        self._set_button_enabled(self._check_btn, not busy)
        self._set_button_enabled(self._download_btn, available)
        self._set_button_enabled(self._retry_btn, failed)
        self._set_button_enabled(self._skip_btn, available)

    @staticmethod
    def _set_button_enabled(btn: QPushButton | None, enabled: bool) -> None:
        if btn is not None:
            btn.setEnabled(enabled)

    # ──────────────────────────────────────────────────────────────────
    # 文本格式
    # ──────────────────────────────────────────────────────────────────

    def _current_version_text(self) -> str:
        service = self._service
        if service is None:
            return t("common.unknown")
        return getattr(service, "_current_version", "") or t("common.unknown")

    def _latest_version_text(self) -> str:
        service = self._service
        if service is None:
            return "—"
        state = getattr(service, "state", None)
        manifest = getattr(state, "manifest",
                           None) if state is not None else None
        if manifest is None:
            return "—"
        return getattr(manifest, "version", "") or "—"

    @staticmethod
    def _error_message_key(code: str) -> str:
        mapping = {
            "UPDATE_CHECK_FAILED": "check_failed",
            "UPDATE_FAILED": "install_failed",
            "UPDATE_NETWORK": "network",
            "UPDATE_VERIFY_FAILED": "verify_failed",
            "ROLLBACK_FAILED": "rollback_failed",
            "NO_MANIFEST": "no_manifest",
            "NO_BACKUP": "rollback_failed",
        }
        return mapping.get(code, "check_failed")

    @staticmethod
    def _format_speed(bps: float) -> str:
        units = ("B/s", "KB/s", "MB/s", "GB/s")
        value = bps
        idx = 0
        while value >= 1024 and idx < len(units) - 1:
            value /= 1024
            idx += 1
        return f"{value:.1f} {units[idx]}"

    # ──────────────────────────────────────────────────────────────────
    # 样式表生成
    # ──────────────────────────────────────────────────────────────────

    def _progress_style(self) -> str:
        return f"""
            QProgressBar {{
                background: {_C.BG_ELEVATED};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
                text-align: center;
                color: {_C.TEXT_SECONDARY};
            }}
            QProgressBar::chunk {{
                background: {_C.PRIMARY};
                border-radius: {Radii.sm};
            }}
        """

    def _input_style(self) -> str:
        return f"""
            QComboBox {{
                background: {_C.BG_BASE};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                padding: 6px 12px;
                color: {_C.TEXT_PRIMARY};
            }}
            QComboBox:focus {{
                border-color: {_C.PRIMARY};
            }}
        """

    # ──────────────────────────────────────────────────────────────────
    # i18n retranslate
    # ──────────────────────────────────────────────────────────────────

    def retranslate(self) -> None:
        if self._header_title_lbl is not None:
            self._header_title_lbl.setText(t("update.header.title"))
        if self._header_subtitle_lbl is not None:
            self._header_subtitle_lbl.setText(t("update.header.subtitle"))
        for label, key in self._i18n_labels:
            try:
                label.setText(t(key))
            except Exception:
                pass
        for btn, key in self._i18n_buttons:
            try:
                btn.setText(t(key))
            except Exception:
                pass
        if self._channel_combo is not None:
            for index in range(self._channel_combo.count()):
                data = self._channel_combo.itemData(index)
                if data == "stable":
                    self._channel_combo.setItemText(
                        index, t("update.channel.stable"))
                elif data == "beta":
                    self._channel_combo.setItemText(
                        index, t("update.channel.beta"))


__all__ = ["UpdatePage"]
