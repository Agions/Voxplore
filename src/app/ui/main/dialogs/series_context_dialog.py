#!/usr/bin/env python3
"""Dialogs for editing multi-video / series metadata (v2.5.0).

This module is the home for ``QDialog``-based editors that the main
window pops up to collect structured information from the user.
Currently ships with :class:`SeriesContextDialog`, the editor for
``SeriesContext`` that is used by the ``series`` multi-video strategy.

v2.5.0 视觉重设计：
- 三段式分组（基础信息 / 命名规则 / 共享上下文）
- 命名预设、题材预设 chip 化（一键点击填充）
- 字段 label 与输入对齐，placeholder 富提示
- footer 重置左 + 主操作（保存）右，符合 macOS HIG
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
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
from ...theme.ds_tokens import (
    _C,
    FontSizes,
    FontWeights,
    Radii,
    Spacing,
    ui_font,
)

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


# ═══════════════════════════════════════════════════════════════════
# 辅助小组件
# ═══════════════════════════════════════════════════════════════════


class _ChipBar(QFrame):
    """横向 chip 列表容器（用于命名预设 / 题材预设）。

    设计要点：
    - 等高 chip、横向流式布局
    - 点击 chip → 触发 on_pick(index)
    - 选中态视觉反馈（主色边框）
    """

    def __init__(
        self,
        options: tuple[str, ...],
        on_pick,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("chip_bar")
        self._on_pick = on_pick

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.xs)
        layout.addStretch(0)

        self._chips: list[QPushButton] = []
        for idx, text in enumerate(options):
            chip = QPushButton(text)
            chip.setCheckable(True)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setFixedHeight(24)
            chip.setFont(ui_font(FontSizes.xs))
            chip.clicked.connect(lambda _checked=False,
                                 i=idx: self._handle_click(i))
            self._apply_style(chip, selected=False)
            self._chips.append(chip)
            layout.addWidget(chip)
        layout.addStretch(1)

    def _handle_click(self, idx: int) -> None:
        """chip 被点击：触发回调 + 视觉选中态。"""
        self.set_active(idx)
        if self._on_pick is not None:
            self._on_pick(idx)

    def set_active(self, idx: int) -> None:
        """程序化高亮某个 chip（不影响 on_pick 回调）。"""
        for i, chip in enumerate(self._chips):
            selected = i == idx
            chip.setChecked(selected)
            self._apply_style(chip, selected=selected)

    @staticmethod
    def _apply_style(chip: QPushButton, *, selected: bool) -> None:
        if selected:
            chip.setStyleSheet(
                f"""
                QPushButton {{
                    background: {_C.PRIMARY_LIGHTEST};
                    color: {_C.PRIMARY_DARK};
                    border: 1px solid {_C.PRIMARY};
                    border-radius: {Radii.full};
                    padding: 0 10px;
                    font-weight: {FontWeights.Medium};
                }}
                """
            )
        else:
            chip.setStyleSheet(
                f"""
                QPushButton {{
                    background: {_C.BG_SURFACE};
                    color: {_C.TEXT_SECONDARY};
                    border: 1px solid {_C.BORDER_SUBTLE};
                    border-radius: {Radii.full};
                    padding: 0 10px;
                }}
                QPushButton:hover {{
                    background: {_C.BG_ELEVATED};
                    color: {_C.TEXT_PRIMARY};
                    border-color: {_C.BORDER_DEFAULT};
                }}
                """
            )

    def count(self) -> int:
        return len(self._chips)


def _section_header(title: str, description: str = "") -> QFrame:
    """段标题 + 可选描述（用于「基础信息」「命名规则」「共享上下文」分组）。"""
    frame = QFrame()
    frame.setObjectName("dialog_section_header")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(0, Spacing.xs, 0, Spacing.xs)
    layout.setSpacing(2)

    title_lbl = QLabel(title)
    title_lbl.setFont(ui_font(FontSizes.sm, FontWeights.SemiBold))
    title_lbl.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
    layout.addWidget(title_lbl)

    if description:
        desc_lbl = QLabel(description)
        desc_lbl.setFont(ui_font(FontSizes.xs))
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        layout.addWidget(desc_lbl)

    return frame


def _field_label(text: str) -> QLabel:
    """字段标签（字号 xs/Medium，对齐输入框上方）。"""
    lbl = QLabel(text)
    lbl.setFont(ui_font(FontSizes.xs, FontWeights.Medium))
    lbl.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
    return lbl


def _field_hint(text: str) -> QLabel:
    """字段说明（占位 / 占位提示，弱化）。"""
    lbl = QLabel(text)
    lbl.setFont(ui_font(FontSizes.xs))
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"color: {_C.TEXT_MUTED};")
    return lbl


# ═══════════════════════════════════════════════════════════════════
# SeriesContextDialog
# ═══════════════════════════════════════════════════════════════════


class SeriesContextDialog(QDialog):
    """编辑整季系列共享上下文的对话框（v2.5.0）。

    用法::

        dlg = SeriesContextDialog(parent, initial=existing_ctx)
        if dlg.exec() == QDialog.Accepted:
            ctx = dlg.result_ctx()  # SeriesContext 实例

    表单字段（按分组排序）：
    - **基础信息**：剧名、题材、总集数
    - **命名规则**：单集命名模板 + chip 预设
    - **共享上下文**：共享人物、剧情主线、世界观
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        initial: SeriesContext | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("production.series.dialog_title"))
        self.setMinimumWidth(620)

        self._initial = initial or SeriesContext()

        root = QVBoxLayout(self)
        root.setContentsMargins(Spacing.xl, Spacing.lg, Spacing.xl, Spacing.lg)
        root.setSpacing(Spacing.lg)

        # ── 顶部 hero：标题 + 副标题 ──
        hero = QVBoxLayout()
        hero.setContentsMargins(0, 0, 0, 0)
        hero.setSpacing(Spacing.xxs)
        hero_title = QLabel(t("production.series.dialog_title"))
        hero_title.setFont(ui_font(FontSizes.xxl, FontWeights.Bold))
        hero_title.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        hero.addWidget(hero_title)
        hero_sub = QLabel(t("production.series.dialog_intro"))
        hero_sub.setFont(ui_font(FontSizes.sm))
        hero_sub.setWordWrap(True)
        hero_sub.setStyleSheet(f"color: {_C.TEXT_MUTED}; line-height: 18px;")
        hero.addWidget(hero_sub)
        root.addLayout(hero)

        # ── 基础信息段 ──
        root.addWidget(
            _section_header(
                t("production.series.section_basic"),
                t("production.series.section_basic_desc"),
            )
        )
        root.addLayout(self._build_basic_info())

        # ── 命名规则段 ──
        root.addWidget(
            _section_header(
                t("production.series.section_naming"),
                t("production.series.section_naming_desc"),
            )
        )
        root.addLayout(self._build_naming_rule())

        # ── 共享上下文段 ──
        root.addWidget(
            _section_header(
                t("production.series.section_context"),
                t("production.series.section_context_desc"),
            )
        )
        root.addLayout(self._build_shared_context())

        # ── footer：重置（左）+ 取消/保存（右） ──
        root.addLayout(self._build_footer())

        # 全局 QSS — 对话框底色 + 输入控件统一样式
        self.setStyleSheet(
            f"""
            QDialog {{
                background: {_C.BG_BASE};
                border-radius: {Radii.lg};
            }}
            QLineEdit, QPlainTextEdit, QSpinBox {{
                background: {_C.BG_SURFACE};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
                padding: 8px 10px;
                selection-background-color: {_C.PRIMARY};
            }}
            QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{
                border-color: {_C.PRIMARY};
                background: {_C.BG_BASE};
            }}
            QLineEdit::placeholder, QPlainTextEdit::placeholder {{
                color: {_C.TEXT_DISABLED};
            }}
            """
        )

    # ──────────────────────────────────────────────────────────────
    # 内部 — 段构建器
    # ──────────────────────────────────────────────────────────────

    def _build_basic_info(self) -> QVBoxLayout:
        """基础信息：剧名 + 题材 + 总集数。"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.md)

        # 剧名
        name_row = QVBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(Spacing.xxs)
        name_row.addWidget(_field_label(t("production.series.field_title")))
        self._title_edit = QLineEdit(self._initial.series_title)
        self._title_edit.setPlaceholderText(
            t("production.series.title_placeholder")
        )
        name_row.addWidget(self._title_edit)
        layout.addLayout(name_row)

        # 题材：输入框 + chip 预设
        genre_row = QVBoxLayout()
        genre_row.setContentsMargins(0, 0, 0, 0)
        genre_row.setSpacing(Spacing.xxs)
        genre_row.addWidget(_field_label(t("production.series.field_genre")))
        self._genre_edit = QLineEdit(self._initial.genre)
        self._genre_edit.setPlaceholderText(
            t("production.series.genre_placeholder")
        )
        genre_row.addWidget(self._genre_edit)
        self._genre_chips = _ChipBar(
            _GENRE_PRESETS, self._on_genre_chip_picked
        )
        genre_row.addWidget(self._genre_chips)
        layout.addLayout(genre_row)

        # 总集数
        eps_row = QVBoxLayout()
        eps_row.setContentsMargins(0, 0, 0, 0)
        eps_row.setSpacing(Spacing.xxs)
        eps_row.addWidget(
            _field_label(t("production.series.field_total_eps"))
        )
        eps_value_row = QHBoxLayout()
        eps_value_row.setContentsMargins(0, 0, 0, 0)
        eps_value_row.setSpacing(Spacing.xs)
        self._eps_spin = QSpinBox()
        self._eps_spin.setRange(0, 999)
        self._eps_spin.setValue(int(self._initial.total_episodes))
        self._eps_spin.setSpecialValueText(
            t("production.series.eps_unknown")
        )
        self._eps_spin.setFixedWidth(120)
        eps_value_row.addWidget(self._eps_spin)
        eps_hint = _field_hint(t("production.series.eps_hint"))
        eps_value_row.addWidget(eps_hint, 1)
        eps_row.addLayout(eps_value_row)
        layout.addLayout(eps_row)

        return layout

    def _build_naming_rule(self) -> QVBoxLayout:
        """命名规则：模板输入框 + 占位符提示 + chip 预设。"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.xxs)

        layout.addWidget(_field_label(t("production.series.field_naming")))
        self._naming_edit = QLineEdit(
            self._initial.episode_naming or "{title}_EP{ep:02d}"
        )
        self._naming_edit.setPlaceholderText("{title}_EP{ep:02d}")
        layout.addWidget(self._naming_edit)
        # 占位符说明
        layout.addWidget(_field_hint(t("production.series.naming_hint")))
        # chip 预设
        self._naming_chips = _ChipBar(
            _EPISODE_NAMING_PRESETS, self._on_naming_chip_picked
        )
        # 若初始值匹配某个 preset，预选它
        self._match_initial_naming_preset()
        layout.addWidget(self._naming_chips)
        return layout

    def _build_shared_context(self) -> QVBoxLayout:
        """共享上下文：人物 + 剧情 + 世界观。"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.md)

        # 共享人物
        chars_block = QVBoxLayout()
        chars_block.setContentsMargins(0, 0, 0, 0)
        chars_block.setSpacing(Spacing.xxs)
        chars_block.addWidget(
            _field_label(t("production.series.field_characters"))
        )
        self._chars_edit = QPlainTextEdit(
            "\n".join(self._initial.shared_characters)
        )
        self._chars_edit.setPlaceholderText(
            t("production.series.characters_placeholder")
        )
        self._chars_edit.setFixedHeight(80)
        chars_block.addWidget(self._chars_edit)
        layout.addLayout(chars_block)

        # 剧情主线（更高）
        plot_block = QVBoxLayout()
        plot_block.setContentsMargins(0, 0, 0, 0)
        plot_block.setSpacing(Spacing.xxs)
        plot_block.addWidget(
            _field_label(t("production.series.field_plot"))
        )
        self._plot_edit = QPlainTextEdit(self._initial.shared_plot)
        self._plot_edit.setPlaceholderText(
            t("production.series.plot_placeholder")
        )
        self._plot_edit.setFixedHeight(100)
        plot_block.addWidget(self._plot_edit)
        layout.addLayout(plot_block)

        # 世界观设定
        world_block = QVBoxLayout()
        world_block.setContentsMargins(0, 0, 0, 0)
        world_block.setSpacing(Spacing.xxs)
        world_block.addWidget(
            _field_label(t("production.series.field_world"))
        )
        self._world_edit = QPlainTextEdit(self._initial.world_setting)
        self._world_edit.setPlaceholderText(
            t("production.series.world_placeholder")
        )
        self._world_edit.setFixedHeight(72)
        world_block.addWidget(self._world_edit)
        layout.addLayout(world_block)

        return layout

    def _build_footer(self) -> QHBoxLayout:
        """footer：左侧重置按钮 + 右侧主操作（取消/保存）。"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, Spacing.xs, 0, 0)
        layout.setSpacing(Spacing.xs)

        self._reset_btn = QPushButton(t("production.series.reset"))
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.setFixedHeight(34)
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        self._reset_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                color: {_C.TEXT_MUTED};
                border: none;
                border-radius: {Radii.sm};
                padding: 0 12px;
                font-size: {FontSizes.sm}px;
            }}
            QPushButton:hover {{
                color: {_C.PRIMARY};
                background: {_C.PRIMARY_LIGHTEST};
            }}
            """
        )
        layout.addWidget(self._reset_btn)
        layout.addStretch(1)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText(t("common.cancel"))
        cancel_btn.setFixedHeight(34)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {_C.BG_SURFACE};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                padding: 0 16px;
                font-size: {FontSizes.sm}px;
            }}
            QPushButton:hover {{
                background: {_C.BG_ELEVATED};
            }}
            """
        )
        save_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        save_btn.setText(t("common.save"))
        save_btn.setFixedHeight(34)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setDefault(True)
        save_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {_C.PRIMARY};
                color: #ffffff;
                border: none;
                border-radius: {Radii.sm};
                padding: 0 20px;
                font-size: {FontSizes.sm}px;
                font-weight: {FontWeights.SemiBold};
            }}
            QPushButton:hover {{
                background: {_C.PRIMARY_DARK};
            }}
            QPushButton:pressed {{
                background: {_C.PRIMARY_DARKER};
            }}
            """
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        return layout

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
            episode_naming=self._naming_edit.text().strip()
            or "{title}_EP{ep:02d}",
            shared_characters=shared_chars,
            shared_plot=self._plot_edit.toPlainText().strip(),
            world_setting=self._world_edit.toPlainText().strip(),
            genre=self._genre_edit.text().strip(),
            total_episodes=int(self._eps_spin.value()),
        )

    # ──────────────────────────────────────────────────────────────
    # 内部槽位
    # ──────────────────────────────────────────────────────────────

    def _on_genre_chip_picked(self, idx: int) -> None:
        """题材 chip 被点击：把对应文本写入 genre 输入框。"""
        self._genre_edit.setText(_GENRE_PRESETS[idx])

    def _on_naming_chip_picked(self, idx: int) -> None:
        """命名预设 chip 被点击：把对应模板写入 naming 输入框。"""
        self._naming_edit.setText(_EPISODE_NAMING_PRESETS[idx])

    def _match_initial_naming_preset(self) -> None:
        """初始化时若命名值匹配某个预设，预先高亮对应 chip。"""
        initial = self._initial.episode_naming
        if not initial:
            return
        for i, preset in enumerate(_EPISODE_NAMING_PRESETS):
            if preset == initial:
                self._naming_chips.set_active(i)
                return

    def _on_reset_clicked(self) -> None:
        """v2.5.0：清空表单回到默认 SeriesContext。"""
        self._title_edit.clear()
        self._naming_edit.setText("{title}_EP{ep:02d}")
        self._naming_chips.set_active(0)
        self._eps_spin.setValue(0)
        self._chars_edit.clear()
        self._plot_edit.clear()
        self._world_edit.clear()
        self._genre_edit.clear()
        # 题材 chips 全部清空选中态
        for chip in self._genre_chips._chips:
            chip.setChecked(False)
            _ChipBar._apply_style(chip, selected=False)


__all__ = ["SeriesContextDialog"]
