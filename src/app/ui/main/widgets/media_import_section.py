#!/usr/bin/env python3
"""素材导入 section 专用 UI 组件（v2.5.0 视觉重设计）。

将 ``ProductionPage`` 中「素材导入」一栏拆成 3 个可复用小组件：

1. :class:`MediaSummaryBar` — 已选视频的紧凑统计栏（数量 / 总时长 / 文件大小）。
2. :class:`StrategyChoiceCards` — 4 卡片可视化策略选择器（替代 QComboBox）。
3. :class:`SeriesContextPreview` — series 策略选中后的 SeriesContext 摘要卡。

设计原则（取自 ui-designer skill）：

* **视觉层级清晰** — 标题用 xxl/SemiBold、副标题用 sm/Muted，与正文区分。
* **间距系统化** — 全部 8/12/16/24px（``Spacing.xs/sm/md/lg``）。
* **配色克制** — 仅用 Primary/Neutral 两个色族 + 1 个强调色（series 卡）。
* **可选渐进** — series 选中后才展开 SeriesContext 摘要。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ....models.project import SeriesContext
from ...i18n import t
from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, Spacing, ui_font

if TYPE_CHECKING:
    from ....models.project import MultiVideoStrategy


# ═══════════════════════════════════════════════════════════════════
# MediaSummaryBar
# ═══════════════════════════════════════════════════════════════════


class MediaSummaryBar(QFrame):
    """已选视频的紧凑统计栏。

    设计要点：
    - 横向 3 列等宽（数量 / 时长 / 大小）
    - 数字用 ``FontWeights.SemiBold`` 强化可读性
    - 单位用 ``TEXT_MUTED`` 弱化
    - 空态（count=0）整栏隐藏，由父控件决定

    Signals:
        add_more_clicked: 触发「添加更多」按钮
    """

    add_more_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("media_summary_bar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            Spacing.md, Spacing.sm, Spacing.md, Spacing.sm
        )
        layout.setSpacing(Spacing.md)

        # ── 数量 ──
        self._count_label = QLabel("0")
        self._count_label.setFont(
            ui_font(FontSizes.lg, FontWeights.SemiBold)
        )
        self._count_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        self._count_unit = QLabel(t("production.media.unit.videos"))
        self._count_unit.setFont(ui_font(FontSizes.xs))
        self._count_unit.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        self._count_divider = self._make_divider()
        layout.addWidget(self._count_label)
        layout.addWidget(self._count_unit)
        layout.addWidget(self._count_divider)

        # ── 总时长 ──
        self._duration_label = QLabel("0:00")
        self._duration_label.setFont(
            ui_font(FontSizes.lg, FontWeights.SemiBold)
        )
        self._duration_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        self._duration_unit = QLabel(t("production.media.unit.duration"))
        self._duration_unit.setFont(ui_font(FontSizes.xs))
        self._duration_unit.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        self._duration_divider = self._make_divider()
        layout.addWidget(self._duration_label)
        layout.addWidget(self._duration_unit)
        layout.addWidget(self._duration_divider)

        # ── 文件大小 ──
        self._size_label = QLabel("0 B")
        self._size_label.setFont(
            ui_font(FontSizes.lg, FontWeights.SemiBold)
        )
        self._size_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        self._size_unit = QLabel(t("production.media.unit.size"))
        self._size_unit.setFont(ui_font(FontSizes.xs))
        self._size_unit.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        layout.addWidget(self._size_label)
        layout.addWidget(self._size_unit)

        layout.addStretch(1)

        # ── 「添加更多」按钮（次要操作）──
        self._add_more_btn = QPushButton(
            t("production.media.action.add_more")
        )
        self._add_more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_more_btn.setFixedHeight(28)
        self._add_more_btn.clicked.connect(self.add_more_clicked)
        self._add_more_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                color: {_C.PRIMARY};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
                padding: 0 12px;
                font-size: {FontSizes.xs}px;
                font-weight: {FontWeights.Medium};
            }}
            QPushButton:hover {{
                background: {_C.PRIMARY_LIGHTEST};
                border-color: {_C.PRIMARY};
            }}
            """
        )
        layout.addWidget(self._add_more_btn)

        # 整体样式 — 弱化边框 + 浅背景，区别于主操作 dropzone
        self.setStyleSheet(
            f"""
            QFrame#media_summary_bar {{
                background: {_C.BG_INPUT};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
            }}
            """
        )

    def _make_divider(self) -> QFrame:
        """水平分隔线（用于视觉分组）。"""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFixedWidth(1)
        line.setFixedHeight(20)
        line.setStyleSheet(
            f"color: {_C.BORDER_SUBTLE}; background: {_C.BORDER_SUBTLE};"
        )
        return line

    def update_stats(
        self,
        count: int,
        total_duration_seconds: float,
        total_size_bytes: int,
    ) -> None:
        """更新统计信息；空态时整栏隐藏。"""
        if count <= 0:
            self.setVisible(False)
            return
        self.setVisible(True)
        self._count_label.setText(str(count))
        self._duration_label.setText(
            _format_duration(total_duration_seconds)
        )
        self._size_label.setText(_format_size(total_size_bytes))

    def retranslate(self) -> None:
        """i18n 刷新：单位标签文案。"""
        self._count_unit.setText(t("production.media.unit.videos"))
        self._duration_unit.setText(t("production.media.unit.duration"))
        self._size_unit.setText(t("production.media.unit.size"))
        self._add_more_btn.setText(t("production.media.action.add_more"))


def _format_duration(seconds: float) -> str:
    """把秒数渲染成 ``H:MM:SS`` / ``M:SS`` 紧凑格式。"""
    total = int(max(0, seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _format_size(size_bytes: int) -> str:
    """人类可读的文件大小（B / KB / MB / GB）。"""
    size = float(max(0, size_bytes))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"  # pragma: no cover - 防御性


# ═══════════════════════════════════════════════════════════════════
# StrategyChoiceCards
# ═══════════════════════════════════════════════════════════════════


class StrategyChoiceCards(QFrame):
    """4 卡片可视化策略选择器（替代下拉框）。

    设计要点：
    - 2x2 grid，每张卡片等高
    - 选中态：主色边框 + 主色淡背景
    - 未选中态：中性边框 + 浅背景
    - 每张卡片左侧大 icon + 右侧标题 + 描述
    - 鼠标悬停轻微提升对比度（hover 态）

    Signals:
        strategy_changed: 用户切换策略时发射（值 ``"single"|"concat"|"batch"|"series"``）
    """

    strategy_changed = Signal(str)

    _STRATEGIES: tuple[tuple[str, str, str, str], ...] = (
        # (value, icon, title_key, desc_key)
        ("single", "▶", "production.strategy.single",
         "production.strategy.single.desc"),
        ("concat", "↔", "production.strategy.concat",
         "production.strategy.concat.desc"),
        ("batch",  "▤", "production.strategy.batch",
         "production.strategy.batch.desc"),
        ("series", "📺", "production.strategy.series",
         "production.strategy.series.desc"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("strategy_choice_cards")

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(Spacing.sm)
        layout.setVerticalSpacing(Spacing.sm)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._cards: dict[str, _StrategyCard] = {}

        # 2x2 grid
        for i, (value, icon, title_key, desc_key) in enumerate(self._STRATEGIES):
            card = _StrategyCard(value, icon, title_key, desc_key)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            self._button_group.addButton(card, i)
            self._cards[value] = card
            row, col = divmod(i, 2)
            layout.addWidget(card, row, col)

        self._button_group.idClicked.connect(self._on_button_clicked)

        # 默认选中 batch
        self.set_strategy("batch")

    def _on_button_clicked(self, button_id: int) -> None:
        value = self._STRATEGIES[button_id][0]
        self.strategy_changed.emit(value)

    def set_strategy(self, value: MultiVideoStrategy | str) -> None:
        """程序化设置当前选中策略（用于外部恢复 / retranslate）。"""
        for idx, (v, _icon, _t, _d) in enumerate(self._STRATEGIES):
            if v == value:
                btn = self._button_group.button(idx)
                if btn is not None and not btn.isChecked():
                    btn.setChecked(True)
                break

    def strategy(self) -> str:
        """当前选中的策略。"""
        btn = self._button_group.checkedButton()
        if btn is None:
            return "batch"  # type: ignore[unreachable]
        idx = self._button_group.id(btn)
        return self._STRATEGIES[idx][0]

    def retranslate(self) -> None:
        for card in self._cards.values():
            card.retranslate()


class _StrategyCard(QPushButton):
    """单张策略卡片（带选中态）。"""

    _SELECTED_QSS = """
        background: {primary_subtle};
        border: 2px solid {primary};
    """

    _UNSELECTED_QSS = """
        background: {bg_surface};
        border: 1px solid {border};
    """

    def __init__(
        self,
        value: str,
        icon: str,
        title_key: str,
        desc_key: str,
    ) -> None:
        super().__init__()
        self.setCheckable(True)
        self.setFixedHeight(72)
        self._value = value
        self._title_key = title_key
        self._desc_key = desc_key

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            Spacing.md, Spacing.sm, Spacing.md, Spacing.sm
        )
        layout.setSpacing(Spacing.md)

        # icon
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(ui_font(22))
        icon_lbl.setFixedWidth(28)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        # text col
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)
        self._title_lbl = QLabel()
        self._title_lbl.setFont(
            ui_font(FontSizes.sm, FontWeights.SemiBold)
        )
        text_col.addWidget(self._title_lbl)
        self._desc_lbl = QLabel()
        self._desc_lbl.setFont(ui_font(FontSizes.xs))
        self._desc_lbl.setWordWrap(True)
        self._desc_lbl.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        text_col.addWidget(self._desc_lbl)
        layout.addLayout(text_col, 1)

        self.retranslate()
        self._refresh_style()
        self.toggled.connect(self._refresh_style)

    def retranslate(self) -> None:
        self._title_lbl.setText(t(self._title_key))
        self._desc_lbl.setText(t(self._desc_key))

    def _refresh_style(self) -> None:
        if self.isChecked():
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background: {_C.PRIMARY_LIGHTEST};
                    border: 2px solid {_C.PRIMARY};
                    border-radius: {Radii.md};
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {_C.PRIMARY_LIGHTER};
                }}
                """
            )
            self._title_lbl.setStyleSheet(f"color: {_C.PRIMARY_DARK};")
        else:
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background: {_C.BG_SURFACE};
                    border: 1px solid {_C.BORDER_SUBTLE};
                    border-radius: {Radii.md};
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {_C.BG_ELEVATED};
                    border-color: {_C.BORDER_DEFAULT};
                }}
                """
            )
            self._title_lbl.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")


# ═══════════════════════════════════════════════════════════════════
# SeriesContextPreview
# ═══════════════════════════════════════════════════════════════════


class SeriesContextPreview(QFrame):
    """series 策略选中后的 SeriesContext 摘要预览卡。

    - 显示剧名 / 总集数 / 共享人物（前 3 个 + 更多计数）
    - 右侧「编辑」按钮触发外部弹窗
    - 空 SeriesContext 时显示提示 + 编辑按钮

    Signals:
        edit_clicked: 用户点击「编辑」时发射
    """

    edit_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("series_context_preview")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            Spacing.md, Spacing.sm, Spacing.md, Spacing.sm
        )
        layout.setSpacing(Spacing.md)

        # left: icon + text col
        icon = QLabel("📺")
        icon.setFont(ui_font(20))
        icon.setFixedWidth(28)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)
        self._title_lbl = QLabel()
        self._title_lbl.setFont(
            ui_font(FontSizes.sm, FontWeights.SemiBold)
        )
        text_col.addWidget(self._title_lbl)
        self._meta_lbl = QLabel()
        self._meta_lbl.setFont(ui_font(FontSizes.xs))
        self._meta_lbl.setWordWrap(True)
        self._meta_lbl.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        text_col.addWidget(self._meta_lbl)
        layout.addLayout(text_col, 1)

        # right: edit button
        self._edit_btn = QPushButton(t("production.strategy.series_edit"))
        self._edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_btn.setFixedHeight(30)
        self._edit_btn.clicked.connect(self.edit_clicked)
        self._edit_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {_C.PRIMARY};
                color: #ffffff;
                border: none;
                border-radius: {Radii.sm};
                padding: 0 14px;
                font-size: {FontSizes.xs}px;
                font-weight: {FontWeights.Medium};
            }}
            QPushButton:hover {{
                background: {_C.PRIMARY_DARK};
            }}
            """
        )
        layout.addWidget(self._edit_btn)

        self.setStyleSheet(
            f"""
            QFrame#series_context_preview {{
                background: {_C.PRIMARY_LIGHTEST};
                border: 1px solid {_C.PRIMARY_LIGHT};
                border-radius: {Radii.sm};
            }}
            """
        )

        self.set_context(None)

    def set_context(self, ctx: SeriesContext | None) -> None:
        """根据当前 SeriesContext 刷新预览。"""
        if ctx is None or not ctx.series_title:
            self._title_lbl.setText(t("production.media.series_empty_title"))
            self._title_lbl.setStyleSheet(
                f"color: {_C.TEXT_SECONDARY}; font-style: italic;"
            )
            self._meta_lbl.setText(
                t("production.media.series_empty_hint")
            )
            return
        self._title_lbl.setText(ctx.series_title)
        self._title_lbl.setStyleSheet(f"color: {_C.PRIMARY_DARK};")
        meta_parts: list[str] = []
        if ctx.total_episodes > 0:
            meta_parts.append(
                t("production.media.series_meta_eps").format(
                    n=ctx.total_episodes
                )
            )
        if ctx.genre:
            meta_parts.append(ctx.genre)
        if ctx.shared_characters:
            chars = ctx.shared_characters[:3]
            more = (
                len(ctx.shared_characters) - 3
                if len(ctx.shared_characters) > 3
                else 0
            )
            chars_text = "、".join(chars)
            if more > 0:
                chars_text += (
                    " " + t("production.media.series_meta_more").format(n=more)
                )
            meta_parts.append(chars_text)
        self._meta_lbl.setText(" · ".join(meta_parts) or ctx.series_title)

    def retranslate(self) -> None:
        self._edit_btn.setText(t("production.strategy.series_edit"))


# ═══════════════════════════════════════════════════════════════════
# File stats helper
# ═══════════════════════════════════════════════════════════════════


def compute_file_stats(
    paths: list[str],
) -> tuple[int, float, int]:
    """从路径列表汇总 (数量, 总秒数, 总字节)。

    注：FFmpeg 调用开销大，此函数仅依赖 ``os.path.getsize``，时长按 0
    估算（避免在主线程跑 ffprobe）。需要准确时长请在调用方预先
    触发 :class:`VideoDropzoneFrame` 的 ``files_changed`` 信号内异步分析。
    """
    total_size = 0
    for p in paths:
        try:
            total_size += Path(p).stat().st_size
        except OSError:
            pass
    return (len(paths), 0.0, total_size)


__all__ = [
    "MediaSummaryBar",
    "StrategyChoiceCards",
    "SeriesContextPreview",
    "compute_file_stats",
]
