#!/usr/bin/env python3
"""Dialogs for editing multi-video / series metadata (v2.5.0).

This module is the home for ``QDialog``-based editors that the main
window pops up to collect structured information from the user.
Currently ships with :class:`SeriesContextDialog`, the editor for
``SeriesContext`` that is used by the ``series`` multi-video strategy.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ....models.project import SeriesContext  # v2.5.0
from ...i18n import t
from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, ui_font

_EPISODE_NAMING_PRESETS: tuple[str, ...] = (
    "{title}_EP{ep:02d}",
    "{title}_E{ep:02d}",
    "{title}_{ep:02d}",
    "EP{ep:02d}_{title}",
    "{title} 第{ep:02d}集",
)

_GENRE_PRESETS: tuple[str, ...] = (
    "短剧",
    "甜宠",
    "都市",
    "古装",
    "悬疑",
    "复仇",
    "穿越",
    "家庭",
    "校园",
    "职场",
)


class SeriesContextDialog(QDialog):
    """编辑整季系列共享上下文的对话框（v2.5.0）。

    用法::

        dlg = SeriesContextDialog(parent, initial=existing_ctx)
        if dlg.exec() == QDialog.Accepted:
            ctx = dlg.result_ctx()  # SeriesContext 实例

    表单字段：
    - ``series_title``   剧名
    - ``episode_naming`` 单集输出命名模板（含 ``{title}`` 与 ``{ep}`` 占位符）
    - ``shared_characters`` 共享人物（每行一个）
    - ``shared_plot``      全季剧情主线
    - ``world_setting``    世界观设定
    - ``genre``            题材（带预设下拉框）
    - ``total_episodes``   总集数（0=未知）
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        initial: SeriesContext | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("production.series.dialog_title"))
        self.setMinimumWidth(560)

        self._initial = initial or SeriesContext()

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(16)

        intro = QLabel(t("production.series.dialog_intro"))
        intro.setWordWrap(True)
        intro.setFont(ui_font(FontSizes.sm))
        intro.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        root.addWidget(intro)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        # 剧名
        self._title_edit = QLineEdit(self._initial.series_title)
        self._title_edit.setPlaceholderText(t("production.series.title_placeholder"))
        form.addRow(self._label(t("production.series.field_title")), self._title_edit)

        # 命名模板
        self._naming_edit = QLineEdit(
            self._initial.episode_naming or "{title}_EP{ep:02d}"
        )
        self._naming_edit.setPlaceholderText("{title}_EP{ep:02d}")
        form.addRow(self._label(t("production.series.field_naming")), self._naming_edit)

        # 命名预设下拉（仅快捷选择，点击后填到 _naming_edit）
        self._naming_preset_combo = QComboBox()
        for preset in _EPISODE_NAMING_PRESETS:
            self._naming_preset_combo.addItem(preset)
        self._naming_preset_combo.activated.connect(
            lambda idx: self._naming_edit.setText(
                self._naming_preset_combo.itemText(idx)
            )
        )
        form.addRow(
            self._label(t("production.series.field_naming_preset")),
            self._naming_preset_combo,
        )

        # 题材（带预设）
        self._genre_edit = QLineEdit(self._initial.genre)
        self._genre_edit.setPlaceholderText(t("production.series.genre_placeholder"))
        self._genre_combo = QComboBox()
        self._genre_combo.setEditable(False)
        self._genre_combo.addItem("")  # 空白选项
        for g in _GENRE_PRESETS:
            self._genre_combo.addItem(g)
        self._genre_combo.activated.connect(
            lambda idx: self._genre_edit.setText(self._genre_combo.itemText(idx))
        )
        genre_row = QWidget()
        genre_layout = QHBoxLayout(genre_row)
        genre_layout.setContentsMargins(0, 0, 0, 0)
        genre_layout.setSpacing(8)
        genre_layout.addWidget(self._genre_edit, 1)
        genre_layout.addWidget(self._genre_combo, 0)
        form.addRow(self._label(t("production.series.field_genre")), genre_row)

        # 总集数
        self._eps_spin = QSpinBox()
        self._eps_spin.setRange(0, 999)
        self._eps_spin.setValue(int(self._initial.total_episodes))
        self._eps_spin.setSpecialValueText(t("production.series.eps_unknown"))
        form.addRow(self._label(t("production.series.field_total_eps")), self._eps_spin)

        # 共享人物（多行）
        self._chars_edit = QPlainTextEdit("\n".join(self._initial.shared_characters))
        self._chars_edit.setPlaceholderText(
            t("production.series.characters_placeholder")
        )
        self._chars_edit.setFixedHeight(72)
        form.addRow(
            self._label(t("production.series.field_characters")), self._chars_edit
        )

        # 剧情主线 / 世界观（多行）
        self._plot_edit = QPlainTextEdit(self._initial.shared_plot)
        self._plot_edit.setPlaceholderText(t("production.series.plot_placeholder"))
        self._plot_edit.setFixedHeight(96)
        form.addRow(self._label(t("production.series.field_plot")), self._plot_edit)

        self._world_edit = QPlainTextEdit(self._initial.world_setting)
        self._world_edit.setPlaceholderText(t("production.series.world_placeholder"))
        self._world_edit.setFixedHeight(72)
        form.addRow(self._label(t("production.series.field_world")), self._world_edit)

        root.addLayout(form)

        # 重置按钮（v2.5.0：清空表单回到默认 SeriesContext）
        actions_row = QHBoxLayout()
        self._reset_btn = QPushButton(t("production.series.reset"))
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        actions_row.addWidget(self._reset_btn)
        actions_row.addStretch(1)
        root.addLayout(actions_row)

        # OK / Cancel
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText(t("common.save"))
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            t("common.cancel")
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        root.addWidget(button_box)

        # Round corners + 主题色
        self.setStyleSheet(
            f"""
            QDialog {{
                background: {_C.BG_BASE};
                border-radius: {Radii.lg};
            }}
            QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {{
                background: {_C.BG_SURFACE};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
                padding: 6px 8px;
                selection-background-color: {_C.PRIMARY};
            }}
            QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
                border-color: {_C.PRIMARY};
            }}
            QPushButton {{
                background: {_C.BG_SURFACE};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background: {_C.BG_ELEVATED};
            }}
            """
        )

    # ──────────────────────────────────────────────────────────────
    # 公共 API
    # ──────────────────────────────────────────────────────────────

    def result_ctx(self) -> SeriesContext:
        """返回用户在对话框中编辑好的 :class:`SeriesContext`。

        调用方应在 ``exec()`` 返回 ``Accepted`` 后再读取。
        """
        chars_raw = self._chars_edit.toPlainText().strip()
        shared_chars: list[str] = []
        for line in chars_raw.splitlines():
            s = line.strip()
            if s and s not in shared_chars:
                shared_chars.append(s)

        return SeriesContext(
            series_title=self._title_edit.text().strip(),
            episode_naming=self._naming_edit.text().strip() or "{title}_EP{ep:02d}",
            shared_characters=shared_chars,
            shared_plot=self._plot_edit.toPlainText().strip(),
            world_setting=self._world_edit.toPlainText().strip(),
            genre=self._genre_edit.text().strip(),
            total_episodes=int(self._eps_spin.value()),
        )

    # ──────────────────────────────────────────────────────────────
    # 辅助
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(ui_font(FontSizes.xs, FontWeights.Medium))
        lbl.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        return lbl

    # ──────────────────────────────────────────────────────────────
    # 内部槽位
    # ──────────────────────────────────────────────────────────────

    def _on_reset_clicked(self) -> None:
        """v2.5.0：清空表单回到默认 SeriesContext。"""
        self._title_edit.clear()
        self._naming_edit.setText("{title}_EP{ep:02d}")
        self._eps_spin.setValue(0)
        self._chars_edit.clear()
        self._plot_edit.clear()
        self._world_edit.clear()
        self._genre_edit.clear()
        self._naming_preset_combo.setCurrentIndex(0)
        self._genre_combo.setCurrentIndex(0)


__all__ = ["SeriesContextDialog"]
