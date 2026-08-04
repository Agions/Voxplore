#!/usr/bin/env python3
"""生产完成 Summary 卡片（v2.5.0 端到端流程优化 Phase 2）。

5 步流水线跑完之后,在 production_page 上插入一张「本次成果」持久卡片,
作为 Toast 的视觉补强 — 用户即使错过 4 秒 toast,也能在流水线下方直接
看到产物路径、耗时、文件大小,以及一键打开/保存。

设计要点:
- **持久展示**: 默认 hidden,生产完成后显示,直到用户主动关闭(下次生产再显示)
- **左 4px SUCCESS 色描边**: 视觉语义对齐「成功状态」
- **3 列指标**: 耗时 / 大小 / 步骤数,与 MediaSummaryBar 视觉系统一致
- **3 个 action**: 打开文件 / 打开文件夹 / 保存项目,对应 toast 的 actions
- **可关闭**: 提供 dismissed 信号,父控件可重新生产时重置

设计原则（取自 ui-designer skill）:
- 视觉层级清晰: 标题 xxl/SemiBold, 副标题 sm/Muted
- 间距系统化: 全部 8/12/16/24px (Spacing.xs/sm/md/lg)
- 配色克制: 仅 Primary / Neutral + SUCCESS 强调色
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...i18n import t
from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, Spacing, ui_font


def _humanize_size(size_bytes: int) -> str:
    """把字节数格式化为人类可读的 KB/MB。

    v2.5.0: Summary 卡片用;无第三方依赖。
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _humanize_duration(seconds: float) -> str:
    """把秒数格式化为 ``mm:ss`` 或 ``X.Xs`` 友好形式。"""
    if seconds < 0:
        seconds = 0.0
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    return f"{minutes}m{secs:04.1f}s"


class ProductionSummaryCard(QFrame):
    """生产完成后展示的「本次成果」持久卡片。

    与 Toast 通知互为补强:Toast 4s 自动消失给即时反馈,
    Summary 卡持续展示直到用户主动关闭,确保用户在 5 步流水线下方
    始终能看到产物信息和入口。

    Signals:
        open_file_clicked(str): 点击「打开文件」时发射,携带产物路径
        open_folder_clicked(str): 点击「打开文件夹」时发射,携带产物路径
        save_project_clicked(): 点击「保存项目」时发射
        dismissed(): 用户点关闭按钮

    Public API:
        show_result(path, elapsed_seconds, file_size_bytes, steps_completed, steps_total)
        clear()
        retranslate()
        set_project_path(path)   # 单独更新路径（耗时/大小为 0 占位）
        is_visible_state() -> bool
    """

    open_file_clicked = Signal(str)
    open_folder_clicked = Signal(str)
    save_project_clicked = Signal()
    dismissed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("production_summary_card")

        self._project_path: str = ""
        self._elapsed: float = 0.0
        self._size_bytes: int = 0
        self._steps_completed: int = 0
        self._steps_total: int = 0

        # 显式属性（便于 mypy 推导，避免 dict['value_lbl'] 模糊类型）
        self._header_lbl: QLabel
        self._desc_lbl: QLabel
        self._close_btn: QPushButton
        self._path_lbl: QLabel
        self._open_file_btn: QPushButton
        self._open_folder_btn: QPushButton
        self._save_btn: QPushButton
        self._elapsed_value_lbl: QLabel
        self._elapsed_label_lbl: QLabel
        self._size_value_lbl: QLabel
        self._size_label_lbl: QLabel
        self._steps_value_lbl: QLabel
        self._steps_label_lbl: QLabel

        self._build_ui()
        # 默认禁用 open_file / open_folder（无路径）；save_btn 始终可用
        self._open_file_btn.setEnabled(False)
        self._open_folder_btn.setEnabled(False)
        self._save_btn.setEnabled(True)
        self.setVisible(False)

    # ──────────────────────────────────────────────────────────────
    # UI 搭建
    # ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self._apply_container_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            Spacing.lg, Spacing.base, Spacing.lg, Spacing.base)
        layout.setSpacing(Spacing.md)

        # ── 头部: 标题 + 关闭按钮 ──
        header = QHBoxLayout()
        header.setSpacing(Spacing.xs)
        self._header_lbl = self._make_label(
            f"✅  {t('production.summary.title')}",
            FontSizes.md,
            FontWeights.SemiBold,
            _C.SUCCESS,
        )
        header.addWidget(self._header_lbl)
        header.addStretch(1)

        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("summary_close_btn")
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setToolTip(t("production.summary.close_tooltip"))
        self._close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; "
            f"color: {_C.TEXT_MUTED}; border: none; "
            f"border-radius: {Radii.sm}; }}"
            f"QPushButton:hover {{ background: {_C.BG_OVERLAY}; "
            f"color: {_C.TEXT_PRIMARY}; }}"
        )
        self._close_btn.clicked.connect(self._on_close_clicked)
        header.addWidget(self._close_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header)

        # ── 描述行: 项目已生成 ──
        self._desc_lbl = self._make_label(
            t("production.summary.desc"),
            FontSizes.sm,
            FontWeights.Medium,
            _C.TEXT_PRIMARY,
        )
        self._desc_lbl.setWordWrap(True)
        layout.addWidget(self._desc_lbl)

        # ── 路径行: 文件路径（可点击） ──
        path_row = QHBoxLayout()
        path_row.setSpacing(Spacing.xs)
        path_row.setContentsMargins(0, 0, 0, 0)
        self._path_lbl = QLabel("")
        self._path_lbl.setObjectName("summary_path")
        self._path_lbl.setFont(ui_font(FontSizes.sm))
        self._path_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._path_lbl.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._path_lbl.setStyleSheet(
            f"color: {_C.PRIMARY}; "
            f"background: {_C.BG_SURFACE}; "
            f"border: 1px solid {_C.BORDER_SUBTLE}; "
            f"border-radius: {Radii.sm}; "
            f"padding: 8px 12px;"
        )
        path_row.addWidget(self._path_lbl, 1)
        layout.addLayout(path_row)

        # ── 指标行: 3 列等宽（耗时 / 大小 / 步骤数） ──
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(Spacing.md)
        metrics_row.setContentsMargins(0, 0, 0, 0)
        self._elapsed_value_lbl = QLabel("—")
        self._elapsed_label_lbl = QLabel("")
        self._size_value_lbl = QLabel("—")
        self._size_label_lbl = QLabel("")
        self._steps_value_lbl = QLabel("—")
        self._steps_label_lbl = QLabel("")
        self._add_metric(
            metrics_row,
            "⏱",
            t("production.summary.metric.elapsed"),
            self._elapsed_label_lbl,
            self._elapsed_value_lbl,
        )
        self._add_metric(
            metrics_row,
            "📦",
            t("production.summary.metric.size"),
            self._size_label_lbl,
            self._size_value_lbl,
        )
        self._add_metric(
            metrics_row,
            "📋",
            t("production.summary.metric.steps"),
            self._steps_label_lbl,
            self._steps_value_lbl,
        )
        layout.addLayout(metrics_row)

        # ── 按钮行: 3 个 action ──
        actions_row = QHBoxLayout()
        actions_row.setSpacing(Spacing.xs)
        actions_row.setContentsMargins(0, 0, 0, 0)

        self._open_file_btn = QPushButton(
            f"📂  {t('toast.action.open_file')}")
        self._open_file_btn.setObjectName("summary_open_file_btn")
        self._open_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_file_btn.clicked.connect(self._on_open_file_clicked)
        actions_row.addWidget(self._open_file_btn)

        self._open_folder_btn = QPushButton(
            f"📁  {t('toast.action.open_folder')}")
        self._open_folder_btn.setObjectName("summary_open_folder_btn")
        self._open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_folder_btn.clicked.connect(self._on_open_folder_clicked)
        actions_row.addWidget(self._open_folder_btn)

        self._save_btn = QPushButton(
            f"💾  {t('toast.action.save_project')}")
        self._save_btn.setObjectName("summary_save_btn")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self.save_project_clicked.emit)
        actions_row.addWidget(self._save_btn)

        actions_row.addStretch(1)
        layout.addLayout(actions_row)

    def _apply_container_style(self) -> None:
        """卡片容器样式: SUCCESS 边框 + SUCCESS_LIGHT 背景 + 圆角。"""
        self.setStyleSheet(
            f"QFrame#production_summary_card {{ "
            f"background: {_C.SUCCESS_LIGHT}; "
            f"border: 1px solid {_C.SUCCESS}; "
            f"border-left: 4px solid {_C.SUCCESS}; "
            f"border-radius: {Radii.base}; "
            f"}}"
        )

    @staticmethod
    def _make_label(
        text: str,
        size: int,
        weight: int,
        color: str,
    ) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(ui_font(size, weight))
        lbl.setStyleSheet(f"color: {color};")
        return lbl

    def _add_metric(
        self,
        parent_layout: QHBoxLayout,
        icon: str,
        label: str,
        value_label_lbl: QLabel,
        value_value_lbl: QLabel,
    ) -> QFrame:
        """构造一个 metric 单元 (icon + label + value),并直接挂到父布局。

        Args:
            parent_layout: 接收 QFrame 的 QHBoxLayout
            icon: emoji icon（如 ⏱）
            label: 副标题（如 "总耗时"）
            value_label_lbl: 由调用方提供的 label QLabel 实例
            value_value_lbl: 由调用方提供的 value QLabel 实例
        """
        frame = QFrame()
        frame.setObjectName("summary_metric")
        frame.setStyleSheet(
            f"QFrame#summary_metric {{ "
            f"background: {_C.BG_SURFACE}; "
            f"border: 1px solid {_C.BORDER_SUBTLE}; "
            f"border-radius: {Radii.sm}; "
            f"}}"
        )
        v = QVBoxLayout(frame)
        v.setContentsMargins(Spacing.md, Spacing.sm, Spacing.md, Spacing.sm)
        v.setSpacing(Spacing.xxs)

        top = QHBoxLayout()
        top.setSpacing(Spacing.xxs)
        top.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("summary_metric_icon")
        icon_lbl.setFont(ui_font(FontSizes.sm))
        top.addWidget(icon_lbl)
        value_label_lbl.setObjectName("summary_metric_label")
        value_label_lbl.setFont(ui_font(FontSizes.xs))
        value_label_lbl.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        value_label_lbl.setText(label)
        top.addWidget(value_label_lbl)
        top.addStretch(1)
        v.addLayout(top)

        value_value_lbl.setObjectName("summary_metric_value")
        value_value_lbl.setFont(ui_font(FontSizes.md, FontWeights.SemiBold))
        value_value_lbl.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        v.addWidget(value_value_lbl)

        parent_layout.addWidget(frame, 1)
        return frame

    # ──────────────────────────────────────────────────────────────
    # 公共 API
    # ──────────────────────────────────────────────────────────────

    def show_result(
        self,
        project_path: str,
        elapsed_seconds: float,
        file_size_bytes: int,
        steps_completed: int,
        steps_total: int,
    ) -> None:
        """展示本次生产成果。

        Args:
            project_path: 产物文件路径（用于显示 + 打开/在文件夹中显示）
            elapsed_seconds: 总耗时（秒）
            file_size_bytes: 文件大小（字节）
            steps_completed: 已完成步骤数
            steps_total: 总步骤数（通常 5）
        """
        self._project_path = project_path or ""
        self._elapsed = max(0.0, float(elapsed_seconds))
        self._size_bytes = max(0, int(file_size_bytes))
        self._steps_completed = max(0, int(steps_completed))
        self._steps_total = max(0, int(steps_total))

        # 路径
        if self._project_path:
            self._path_lbl.setText(self._project_path)
            self._path_lbl.setVisible(True)
        else:
            self._path_lbl.setVisible(False)

        # 耗时
        if self._elapsed > 0:
            self._elapsed_value_lbl.setText(
                _humanize_duration(self._elapsed)
            )
        else:
            self._elapsed_value_lbl.setText("—")

        # 大小
        if self._size_bytes > 0:
            self._size_value_lbl.setText(_humanize_size(self._size_bytes))
        else:
            self._size_value_lbl.setText("—")

        # 步骤
        if self._steps_total > 0:
            self._steps_value_lbl.setText(
                t("production.summary.metric.steps_value").format(
                    completed=self._steps_completed,
                    total=self._steps_total,
                )
            )
        else:
            self._steps_value_lbl.setText("—")

        # 按钮启用状态: 没有路径时打开/保存按钮禁用
        has_path = bool(self._project_path) and os.path.exists(
            self._project_path
        )
        self._open_file_btn.setEnabled(has_path)
        self._open_folder_btn.setEnabled(has_path)
        self._save_btn.setEnabled(True)

        self.setVisible(True)

    def clear(self) -> None:
        """重置卡片（下次生产开始时调用）。"""
        self._project_path = ""
        self._elapsed = 0.0
        self._size_bytes = 0
        self._steps_completed = 0
        self._steps_total = 0
        self._path_lbl.clear()
        self._elapsed_value_lbl.setText("—")
        self._size_value_lbl.setText("—")
        self._steps_value_lbl.setText("—")
        self._open_file_btn.setEnabled(False)
        self._open_folder_btn.setEnabled(False)
        self._save_btn.setEnabled(True)
        self.setVisible(False)

    def set_project_path(self, path: str) -> None:
        """仅更新路径（其他指标保留）。"""
        self._project_path = path or ""
        if self._project_path:
            self._path_lbl.setText(self._project_path)
        else:
            self._path_lbl.clear()
        has_path = bool(self._project_path) and os.path.exists(
            self._project_path
        )
        self._open_file_btn.setEnabled(has_path)
        self._open_folder_btn.setEnabled(has_path)

    def is_visible_state(self) -> bool:
        """是否处于「已展示成果」状态（用于父控件判断）。"""
        return self.isVisible()

    def retranslate(self) -> None:
        """i18n 切换时刷新所有可见文本。"""
        self._header_lbl.setText(
            f"✅  {t('production.summary.title')}"
        )
        self._desc_lbl.setText(t("production.summary.desc"))
        self._close_btn.setToolTip(t("production.summary.close_tooltip"))
        self._open_file_btn.setText(
            f"📂  {t('toast.action.open_file')}"
        )
        self._open_folder_btn.setText(
            f"📁  {t('toast.action.open_folder')}"
        )
        self._save_btn.setText(
            f"💾  {t('toast.action.save_project')}"
        )
        self._elapsed_label_lbl.setText(
            t("production.summary.metric.elapsed")
        )
        self._size_label_lbl.setText(
            t("production.summary.metric.size")
        )
        self._steps_label_lbl.setText(
            t("production.summary.metric.steps")
        )

    @staticmethod
    def _refresh_metric_label(
        metric_frame: QFrame, icon: str, label: str
    ) -> None:
        """重置 metric 顶部的 icon + label 文本（兼容旧调用,保留以防外部扩展）。"""
        icon_lbl = metric_frame.findChild(QLabel, "summary_metric_icon")
        label_lbl = metric_frame.findChild(QLabel, "summary_metric_label")
        if icon_lbl is not None:
            icon_lbl.setText(icon)
        if label_lbl is not None:
            label_lbl.setText(label)

    # ──────────────────────────────────────────────────────────────
    # 事件处理
    # ──────────────────────────────────────────────────────────────

    def _on_close_clicked(self) -> None:
        self.setVisible(False)
        self.dismissed.emit()

    def _on_open_file_clicked(self) -> None:
        if self._project_path:
            self.open_file_clicked.emit(self._project_path)

    def _on_open_folder_clicked(self) -> None:
        if self._project_path:
            self.open_folder_clicked.emit(self._project_path)
