"""Lightweight status bar for the bottom of the main window."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar

from app.ui.i18n import t
from app.ui.theme.ds_tokens import _C, FontSizes, Radii

# Translation key for the default status text — see ``common.ready``.
_DEFAULT_STATUS_KEY = "common.ready"


class StatusBar(QFrame):
    """轻量状态栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setObjectName("statusbar")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #statusbar {{
                background: {_C.BG_ELEVATED};
                border-top: 1px solid {_C.BORDER_SUBTLE};
            }}
        """)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)

        self._status_label = QLabel(t(_DEFAULT_STATUS_KEY))
        self._status_label.setFont(QFont("", FontSizes.xs))
        self._status_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        layout.addWidget(self._status_label)
        # Remember the i18n key for the *initial* status text so
        # ``retranslate`` can re-fetch the localized string after a
        # language flip without having to guess.
        self._status_key: str | None = _DEFAULT_STATUS_KEY

        layout.addStretch()

        # 进度条（默认隐藏，生产流程进行时显示）
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(160)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {_C.BG_OVERLAY};
                border: none;
                border-radius: {Radii.full};
            }}
            QProgressBar::chunk {{
                background: {_C.PRIMARY};
                border-radius: {Radii.full};
            }}
        """)
        self._progress_bar.hide()
        layout.addWidget(self._progress_bar)

        self._info_labels = QHBoxLayout()
        self._info_labels.setSpacing(16)
        layout.addLayout(self._info_labels)

    def set_status(self, text: str, key: str | None = None):
        """Update the status text.

        ``key`` is an optional i18n key for the *current* text. When
        provided, :py:meth:`retranslate` will re-fetch the localized
        string with the new active language and re-render the label.
        Keys are best-effort: callers that pass a plain string without
        a key still get the same behavior as before — the label just
        stays on the language it was given in.
        """
        self._status_key = key
        self._status_label.setText(text)

    def show_progress(self, current: int, total: int):
        """显示进度条并更新百分比"""
        pct = int(current / total * 100) if total > 0 else 0
        self._progress_bar.setValue(pct)
        self._progress_bar.show()

    def hide_progress(self):
        """隐藏进度条并重置"""
        self._progress_bar.hide()
        self._progress_bar.setValue(0)

    def add_info(self, text: str):
        lbl = QLabel(text)
        lbl.setFont(QFont("", FontSizes.xs))
        lbl.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        self._info_labels.addWidget(lbl)

    def clear_info(self):
        while self._info_labels.count():
            item = self._info_labels.takeAt(0)
            if item is not None and item.widget() is not None:
                item.widget().deleteLater()

    def retranslate(self) -> None:
        """Refresh the default status text — runtime state is intentionally
        preserved so in-flight progress messages stay visible across a
        language switch and are simply updated on the next emission.
        """
        if self._status_key is not None:
            # Re-resolve through the catalog so a key like
            # ``statusbar.current_page`` (which carries ``{page}``) keeps
            # working — we just use the *current* page as the parameter.
            self._status_label.setText(t(self._status_key))
        else:
            self._status_label.setText(t(_DEFAULT_STATUS_KEY))
