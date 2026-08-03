#!/usr/bin/env python3
"""Production workflow page."""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ....models.project import (
    MultiVideoSource,
    MultiVideoStrategy,
    SeriesContext,
    VideoSource,
)  # v2.5.0
from ...i18n import t
from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, ui_font
from ..controls import ComboBox
from ..dialogs.series_context_dialog import SeriesContextDialog
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


_VIDEO_EXTENSIONS: tuple[str, ...] = (
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".flv",
    ".wmv",
)


# v2.5.0: 多视频策略选项 (策略值, i18n key, 显示图标)
_STRATEGY_OPTIONS: tuple[tuple[str, str, str], ...] = (
    ("single", "production.strategy.single", "▶"),
    ("concat", "production.strategy.concat", "▶▶"),
    ("batch", "production.strategy.batch", "❑❑"),
    ("series", "production.strategy.series", "📺"),
)


class _VideoSourceRow(QFrame):
    """单条视频行：序号 + 文件名 + 操作按钮。

    通过 ``remove_clicked`` 信号向外抛索引，避免 row 与 dropzone 状态耦合。
    """

    remove_clicked = Signal(int)  # 原始 index（由 caller 解析）

    def __init__(
        self,
        index: int,
        source: VideoSource,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._index = index
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        order_lbl = QLabel(f"{index + 1:02d}")
        order_lbl.setFont(ui_font(FontSizes.xs, FontWeights.Bold))
        order_lbl.setFixedWidth(28)
        order_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(order_lbl)

        info_col = QVBoxLayout()
        info_col.setSpacing(0)
        name_lbl = QLabel(source.label or os.path.basename(source.path))
        name_lbl.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        info_col.addWidget(name_lbl)
        path_lbl = QLabel(source.path)
        path_lbl.setFont(ui_font(FontSizes.xs))
        path_lbl.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        info_col.addWidget(path_lbl)
        layout.addLayout(info_col, 1)

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setToolTip(t("production.multi.remove"))
        remove_btn.setStyleSheet(
            f"QPushButton {{ background: {_C.BG_SURFACE}; "
            f"color: {_C.TEXT_SECONDARY}; border: 1px solid {_C.BORDER_SUBTLE}; "
            f"border-radius: {Radii.sm}; }}"
            f"QPushButton:hover {{ color: {_C.DANGER if hasattr(_C, 'DANGER') else '#ef4444'}; }}"
        )
        remove_btn.clicked.connect(
            lambda _checked=False, i=index: self.remove_clicked.emit(i)
        )
        layout.addWidget(remove_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    @property
    def index(self) -> int:
        return self._index


class VideoDropzoneFrame(PaletteAwareMixin, QFrame):
    """交互式拖拽容器（v2.5.0 支持多文件）。

    向后兼容：
    - ``selected_path`` : 取首个路径（与 v2.4 一致）
    - ``file_selected(str)`` : 当首个文件被添加/移除时仍触发
    - 单文件拖入时与老行为完全一致

    新增 API：
    - ``sources`` : ``MultiVideoSource`` 实例（顺序/重命名/删除）
    - ``files_changed(list[VideoSource])`` : 列表变更时发射
    - ``add_paths(paths)`` / ``remove(index)`` / ``move(src, dst)`` / ``clear()``
    """

    file_selected = Signal(str)  # 向后兼容：首文件路径
    files_changed = Signal(list)  # 新增：完整 VideoSource 列表

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_palette_registry()
        self.setAcceptDrops(True)
        self.selected_path: str = ""
        self._sources = MultiVideoSource()
        self._file_present = False
        self._row_widgets: list[_VideoSourceRow] = []
        self._setup_ui()

    # ──────────────────────────────────────────────────────────────
    # 公共 API
    # ──────────────────────────────────────────────────────────────

    @property
    def sources(self) -> MultiVideoSource:
        return self._sources

    @property
    def paths(self) -> list[str]:
        return self._sources.paths

    def add_paths(self, paths: Iterable[str]) -> int:
        """批量追加路径（去重），返回实际新增数量。"""
        added = self._sources.add_many(p for p in paths if self._is_video(p))
        if added:
            self._refresh_ui()
            self._emit_change()
        return added

    def remove(self, index: int) -> bool:
        if self._sources.remove(index) is None:
            return False
        self._refresh_ui()
        self._emit_change()
        return True

    def move(self, src: int, dst: int) -> bool:  # type: ignore[override]
        """v2.5.0：调整两个视频源顺序。"""
        if not self._sources.move(src, dst):
            return False
        self._refresh_ui()
        self._emit_change()
        return True

    # ``move_source`` 是 ``move`` 的语义别名；保留 ``move`` 与 Qt 基类签名
    # 不同的原因：内部把它当作业务动词，而不是 Qt 的窗口位置移动。
    move_source = move

    def clear(self) -> None:
        if self._sources.is_empty:
            return
        self._sources.clear()
        self._refresh_ui()
        self._emit_change()

    # ──────────────────────────────────────────────────────────────
    # UI 搭建与刷新
    # ──────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self._set_palette_style(
            self,
            lambda: (
                f"""
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
        """
            ),
        )
        self._root = QVBoxLayout(self)
        self._root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._root.setSpacing(10)

        # 拖拽提示（empty 状态用，filled 状态隐藏）
        self._empty_box = QWidget()
        empty_layout = QVBoxLayout(self._empty_box)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(10)

        self._icon_lbl = QLabel("🎬")
        self._icon_lbl.setFont(ui_font(32))
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._icon_lbl)

        self._title_lbl = QLabel(t("production.drop_hint"))
        self._title_lbl.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        self._set_palette_style(self._title_lbl, lambda: f"color: {_C.TEXT_PRIMARY};")
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._title_lbl)

        self._path_lbl = QLabel(t("production.format_supported"))
        self._path_lbl.setFont(ui_font(FontSizes.xs))
        self._set_palette_style(self._path_lbl, lambda: f"color: {_C.TEXT_MUTED};")
        self._path_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._path_lbl)

        self._root.addWidget(self._empty_box)

        # 向后兼容：保留 ``_browse_btn``（旧测试 / 旧绑定 code 访问），
        # 委派到多选对话框 ``getOpenFileNames``。
        self._browse_btn = action_button(t("production.browse_button"))
        self._browse_btn.clicked.connect(self._on_browse)
        self._root.addWidget(self._browse_btn, 0, Qt.AlignmentFlag.AlignCenter)

        # filled 状态：文件列表 + 「添加更多」按钮 + 「清空」按钮
        self._list_box = QWidget()
        list_outer = QVBoxLayout(self._list_box)
        list_outer.setContentsMargins(0, 0, 0, 0)
        list_outer.setSpacing(8)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setMaximumHeight(180)
        self._scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: {_C.BG_SURFACE}; "
            f"border: 1px solid {_C.BORDER_SUBTLE}; border-radius: {Radii.sm}; }}"
        )
        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(4, 4, 4, 4)
        self._rows_layout.setSpacing(4)
        self._rows_layout.addStretch()
        self._scroll.setWidget(self._rows_container)
        list_outer.addWidget(self._scroll)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        self._add_more_btn = action_button(t("production.multi.add_more"))
        self._add_more_btn.clicked.connect(self._on_browse)
        actions_row.addWidget(self._add_more_btn)
        self._clear_btn = QPushButton(t("production.multi.clear"))
        self._clear_btn.clicked.connect(self.clear)
        self._clear_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_C.TEXT_MUTED}; "
            f"border: 1px solid {_C.BORDER_SUBTLE}; border-radius: {Radii.sm}; "
            f"padding: 6px 12px; }}"
            f"QPushButton:hover {{ color: {_C.TEXT_PRIMARY}; }}"
        )
        actions_row.addWidget(self._clear_btn)
        actions_row.addStretch()
        list_outer.addLayout(actions_row)

        self._list_box.setVisible(False)
        self._root.addWidget(self._list_box)

        # 首次绘制：保证 empty 显示
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        """根据当前 ``_sources`` 重建 row 列表并切换 empty/list 显隐。"""
        # 清理旧 row
        for row in self._row_widgets:
            row.setParent(None)
            row.deleteLater()
        self._row_widgets.clear()

        # 移除 stretch 之外的所有 item
        while self._rows_layout.count() > 1:
            item = self._rows_layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.deleteLater()

        # 添加新 row
        is_multi = self._sources.count > 0
        for idx, src in enumerate(sorted(self._sources.videos, key=lambda v: v.order)):
            row = _VideoSourceRow(idx, src)
            row.remove_clicked.connect(self._on_row_remove)
            self._row_widgets.append(row)
            # 在 stretch 之前插入
            self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)

        # 切换显隐 + 同步标题（向后兼容：选中状态显示文件信息）
        if is_multi:
            self._empty_box.setVisible(False)
            self._list_box.setVisible(True)
            self._file_present = True
            # 同步 _title_lbl / _path_lbl 为「已选择视频」状态
            first = self._sources.videos[0]
            count = self._sources.count
            if count == 1:
                self._title_lbl.setText(
                    t("production.video_selected").format(name=first.basename)
                )
                self._path_lbl.setText(first.path)
                # v2.4.3 向后兼容：选中状态下 browse 按钮显示「更换视频」
                self._browse_btn.setText(t("production.replace_video"))
            else:
                self._title_lbl.setText(t("production.multi.count").format(count=count))
                self._path_lbl.setText(first.path)
                self._browse_btn.setText(t("production.browse_button"))
        else:
            self._empty_box.setVisible(True)
            self._list_box.setVisible(False)
            self._file_present = False
            self.selected_path = ""
            self._browse_btn.setText(t("production.browse_button"))

    def _on_row_remove(self, index: int) -> None:
        self.remove(index)

    def _emit_change(self) -> None:
        """同步 ``selected_path`` + 发射信号。"""
        first_path = self._sources.paths[0] if self._sources.paths else ""
        # 兼容旧 API：selected_path 始终等于首个
        if first_path != self.selected_path:
            self.selected_path = first_path
            if first_path:
                self.file_selected.emit(first_path)
        self.files_changed.emit(list(self._sources.videos))

    def _on_browse(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            t("production.browse_dialog_title"),
            "",
            t("production.video_filter"),
        )
        if paths:
            self.add_paths(paths)

    # ──────────────────────────────────────────────────────────────
    # 向后兼容：单文件 set_file（保留 旧 call site 的可用性）
    # ──────────────────────────────────────────────────────────────

    def set_file(self, path: str) -> None:
        """单文件设置 API（向后兼容）：替换现有列表为 [path]。"""
        self._sources.clear()
        self._sources.add(path)
        self._refresh_ui()
        self._emit_change()

    # ──────────────────────────────────────────────────────────────
    # 国际化刷新
    # ──────────────────────────────────────────────────────────────

    def retranslate(self) -> None:
        # 保留 _file_present 状态，按选中/未选中分别刷新标题
        if self._file_present and self._sources.count == 1:
            first = self._sources.videos[0]
            self._title_lbl.setText(
                t("production.video_selected").format(name=first.basename)
            )
            self._path_lbl.setText(first.path)
            self._browse_btn.setText(t("production.replace_video"))
        elif self._file_present and self._sources.count > 1:
            self._title_lbl.setText(
                t("production.multi.count").format(count=self._sources.count)
            )
            self._path_lbl.setText(self._sources.videos[0].path)
            self._browse_btn.setText(t("production.browse_button"))
        else:
            self._title_lbl.setText(t("production.drop_hint"))
            self._path_lbl.setText(t("production.format_supported"))
            self._browse_btn.setText(t("production.browse_button"))
        # 状态无关的按钮：仅在 multi 列表状态下显示
        if hasattr(self, "_add_more_btn"):
            self._add_more_btn.setText(t("production.multi.add_more"))
        if hasattr(self, "_clear_btn"):
            self._clear_btn.setText(t("production.multi.clear"))

    # ──────────────────────────────────────────────────────────────
    # 拖拽事件（v2.5.0：收集所有匹配 URL，去重加入）
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _is_video(path: str) -> bool:
        return path.lower().endswith(_VIDEO_EXTENSIONS)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if self._is_video(url.toLocalFile()):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        paths: list[str] = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if self._is_video(path) and path not in paths:
                paths.append(path)
        if paths:
            self.add_paths(paths)
            event.acceptProposedAction()


class ProductionPage(PaletteAwareMixin, QFrame):
    """Structured workflow for first-person narration production.

    Phase 2B: 5-step pipeline + per-step status are read from
    :class:`ProductionPageViewModel`. The view renders them declaratively
    and forwards ``start_requested`` clicks to ``vm.start_pipeline()``.
    """

    start_requested = Signal()
    cancel_requested = Signal()

    # v2.5.0: 控件缓存，便于 retranslate 与类型推断
    _strategy_combo: ComboBox
    _strategy_label: QLabel
    _strategy_frame: QFrame
    _strategy_help: QLabel
    _series_edit_btn: QPushButton
    _series_context: SeriesContext | None
    _files_changed: object  # slot reference, unused at runtime

    def __init__(self, viewmodel: ProductionPageViewModel | None = None, parent=None):
        super().__init__(parent)
        self._init_palette_registry()
        self.setAcceptDrops(True)
        self._vm = viewmodel
        self.setObjectName("production_page")
        self._step_statuses: dict[str, QLabel] = {}
        self._step_status_keys: dict[str, str] = {}
        self._series_context = None
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
        assert layout is not None and isinstance(
            layout, QVBoxLayout
        )  # for type checker

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
        # v2.5.0: 优先取多文件列表，保持向后兼容（fallback 到 selected_path）
        paths = self.dropzone.paths or (
            [self.dropzone.selected_path] if self.dropzone.selected_path else []
        )
        context = self._context_input.text().strip() or t("production.theme_default")
        emotion = self._emotion_combo.currentText().split()[0]

        self.start_requested.emit()
        window = self.window()
        if window is None or not hasattr(window, "_start_production_with_video"):
            return

        if not paths:
            # 退化：打开文件选择对话框（多选）
            from PySide6.QtWidgets import QFileDialog

            selected, _ = QFileDialog.getOpenFileNames(
                self,
                t("production.browse_dialog_title"),
                "",
                t("production.video_filter"),
            )
            if not selected:
                return
            self.dropzone.add_paths(selected)
            paths = self.dropzone.paths

        # 单文件：调用老 API；多文件：尝试新 API。
        if len(paths) == 1:
            window._start_production_with_video(paths[0], context, emotion)
        else:
            starter = getattr(window, "_start_production_with_videos", None)
            if callable(starter):
                strategy = self._current_strategy()
                # series 策略未填 SeriesContext 时给一个空默认值，让 LLM 也能走
                series_ctx = self._series_context if strategy == "series" else None
                starter(paths, context, emotion, strategy, series_ctx)
            else:
                # Fallback：只取首个，保持不让进程崩
                window._start_production_with_video(paths[0], context, emotion)

    # ──────────────────────────────────────────────────────────────
    # v2.5.0: 多视频策略选择 + SeriesContext 编辑（控件响应）
    # ──────────────────────────────────────────────────────────────

    def _on_files_changed(self, _paths: list) -> None:
        """拖拽区文件数变化：2+ 视频时显示策略选择器。"""
        count = self.dropzone._sources.count
        multi = count >= 2
        self._strategy_frame.setVisible(multi)
        self._strategy_help.setVisible(multi)
        # 控件隐藏后 series_edit_btn 总是隐藏（仅 series 时显示）
        if not multi:
            self._series_edit_btn.hide()

    def _on_strategy_changed(self, _index: int) -> None:
        """策略变化：series 时显示“编辑整季系列设定”按钮。"""
        strategy = self._current_strategy()
        self._series_edit_btn.setVisible(strategy == "series")
        # 切到非 series：保留已填的 SeriesContext 以防用户往返

    def _on_edit_series_context(self) -> None:
        """弹出 :class:`SeriesContextDialog` 让用户填写整季系列设定。

        v2.5.0 Phase R:优先用本次会话内已存在的 ``_series_context``;
        若为 None 则从 :func:`load_series_context` 读上次保存的值;
        若仍无,则空白。让用户每次打开对话框都看到上一次的内容。
        """
        from ....services.series_context_store import load_series_context

        initial = self._series_context
        if initial is None:
            initial = load_series_context()
        dlg = SeriesContextDialog(self, initial=initial)
        if dlg.exec() == 1:  # QDialog.Accepted == 1
            ctx = dlg.result_ctx()
            self._series_context = ctx
            # v2.5.0 Phase R:落盘到 SettingsStore,跨项目复用
            from ....services.series_context_store import save_series_context

            save_series_context(ctx)

    def _current_strategy(self) -> MultiVideoStrategy:
        """读取当前策略选择器的值，未知值回退 ``batch``。"""
        from typing import cast

        value = self._strategy_combo.currentData()
        if value in ("single", "concat", "batch", "series"):
            return cast(MultiVideoStrategy, value)
        return "batch"

    def _build_pipeline(self) -> QFrame:
        frame = panel("production_pipeline")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        self._pipeline_section = section_title(t("production.section.media_import"))
        layout.addWidget(self._pipeline_section)

        # 视频拖拽区域
        self.dropzone = VideoDropzoneFrame(self)
        layout.addWidget(self.dropzone)
        # v2.5.0: 拖拽区文件数变化同步触发策略选择器显示逻辑
        self.dropzone.files_changed.connect(self._on_files_changed)

        # v2.5.0: 多视频策略选择器（多文件时显示）
        self._strategy_frame = QFrame()
        self._set_palette_style(
            self._strategy_frame,
            lambda: (
                f"""
            QFrame {{
                background: {_C.BG_BASE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.base};
                padding: 10px 12px;
            }}
        """
            ),
        )
        strategy_box = QHBoxLayout(self._strategy_frame)
        strategy_box.setContentsMargins(0, 0, 0, 0)
        strategy_box.setSpacing(10)

        self._strategy_label = QLabel(t("production.strategy.label"))
        self._strategy_label.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        self._set_palette_style(
            self._strategy_label, lambda: f"color: {_C.TEXT_PRIMARY};"
        )
        self._strategy_combo = ComboBox()
        self._strategy_combo.setMinimumWidth(220)
        for value, key, icon in _STRATEGY_OPTIONS:
            self._strategy_combo.addItem(f"{icon}  {t(key)}", userData=value)
        self._strategy_combo.setCurrentIndex(2)  # 默认 batch
        self._strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)
        self._set_palette_style(
            self._strategy_combo,
            lambda: (
                f"""
            QComboBox {{
                background: {_C.BG_SURFACE};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
                padding: 4px 10px;
            }}
            QComboBox:hover {{
                border-color: {_C.PRIMARY};
            }}
        """
            ),
        )
        strategy_box.addWidget(self._strategy_label)
        strategy_box.addWidget(self._strategy_combo, 1)

        # 编辑整季系列设定按钮（仅 series 策略可见）
        self._series_edit_btn = QPushButton(t("production.strategy.series_edit"))
        self._series_edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._series_edit_btn.clicked.connect(self._on_edit_series_context)
        self._set_palette_style(
            self._series_edit_btn,
            lambda: (
                f"""
            QPushButton {{
                background: {_C.PRIMARY};
                color: #ffffff;
                border: none;
                border-radius: {Radii.sm};
                padding: 4px 14px;
                font-size: {FontSizes.xs}px;
            }}
            QPushButton:hover {{
                background: {_C.PRIMARY_DARK};
            }}
        """
            ),
        )
        strategy_box.addWidget(self._series_edit_btn)

        # 策略帮助说明（单行 hint）
        self._strategy_help = QLabel(t("production.strategy.help"))
        self._strategy_help.setFont(ui_font(FontSizes.xs))
        self._set_palette_style(self._strategy_help, lambda: f"color: {_C.TEXT_MUTED};")
        self._strategy_help.setWordWrap(True)

        strategy_outer = QVBoxLayout()
        strategy_outer.setContentsMargins(0, 0, 0, 0)
        strategy_outer.setSpacing(6)
        strategy_outer.addWidget(self._strategy_frame)
        strategy_outer.addWidget(self._strategy_help)
        layout.addLayout(strategy_outer)

        # SeriesContext (v2.5.0)：仅在 series 策略下由对话框填入
        # （已在 __init__ 中初始化为 None）

        # 默认隐藏（1 个视频 / 无视频时不需要选策略）
        self._strategy_frame.hide()
        self._strategy_help.hide()
        self._series_edit_btn.hide()

        # 行内参数配置面板
        config_frame = QFrame()
        self._set_palette_style(
            config_frame,
            lambda: (
                f"""
            QFrame {{
                background: {_C.BG_BASE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.base};
                padding: 12px;
            }}
        """
            ),
        )
        config_layout = QVBoxLayout(config_frame)
        config_layout.setSpacing(10)

        # 解说主题输入
        context_box = QHBoxLayout()
        self._ctx_label = QLabel(t("production.theme_label"))
        self._ctx_label.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        self._set_palette_style(self._ctx_label, lambda: f"color: {_C.TEXT_PRIMARY};")
        self._context_input = QLineEdit(t("production.theme_default"))
        self._context_input.setPlaceholderText(t("production.theme_placeholder"))
        self._set_palette_style(
            self._context_input,
            lambda: (
                f"""
            QLineEdit {{
                background: {_C.BG_SURFACE};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
                padding: 6px 10px;
            }}
        """
            ),
        )
        context_box.addWidget(self._ctx_label)
        context_box.addWidget(self._context_input, 1)
        config_layout.addLayout(context_box)

        # 情感风格下拉选择
        emotion_box = QHBoxLayout()
        self._emo_label = QLabel(t("production.tone_label"))
        self._emo_label.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        self._set_palette_style(self._emo_label, lambda: f"color: {_C.TEXT_PRIMARY};")
        self._emotion_combo = ComboBox()
        self._emotion_combo.addItems([t(key) for key in _EMOTION_KEYS])
        self._set_palette_style(
            self._emotion_combo,
            lambda: (
                f"""
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
        """
            ),
        )
        emotion_box.addWidget(self._emo_label)
        emotion_box.addWidget(self._emotion_combo, 1)
        config_layout.addLayout(emotion_box)

        layout.addWidget(config_frame)

        self._steps_section = section_title(t("production.section.workflow_steps"))
        layout.addWidget(self._steps_section)

        # Phase 2B: read 5 steps from VM (falls back to canon if no VM)
        steps = self._step_definitions()
        self._step_rows: list[
            tuple[QFrame, QLabel | None, QLabel | None, QLabel | None, str, str]
        ] = []
        for number, name, desc in steps:
            row = self._step_row(number, name, desc)
            layout.addWidget(row)
            badge = row.findChild(QLabel, "step_badge")
            title = row.findChild(QLabel, "step_title")
            status_lbl = row.findChild(QLabel, "step_status")
            self._step_rows.append((row, badge, title, status_lbl, number, name))
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
        self._quality_section = section_title(t("production.section.quality_gate"))
        layout.addWidget(self._quality_section)

        for item in EXPORT_QUALITY_CHECKS:
            layout.addWidget(self._check_item(item))
        layout.addStretch()
        return frame

    def _step_row(self, number: str, name: str, desc: str) -> QFrame:
        row = QFrame()
        row.setObjectName("production_step_row")
        self._set_palette_style(
            row,
            lambda: (
                f"""
            QFrame#production_step_row {{
                background: {_C.BG_BASE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.base};
            }}
        """
            ),
        )
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
        self._set_palette_style(
            label,
            lambda: (
                f"""
            QLabel {{
                color: {_C.TEXT_SECONDARY};
                background: {_C.BG_BASE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
                padding: 8px 10px;
            }}
        """
            ),
        )
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
            self._pipeline_section.setText(t("production.section.media_import"))
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
        self._context_input.setPlaceholderText(t("production.theme_placeholder"))
        # Emotion combo: rebuild every visible item from the canonical
        # ``_EMOTION_KEYS`` so language switches update both label and
        # placeholder/selectable text. ``setItemText`` keeps the existing
        # data slot intact so user selections survive the retranslate.
        for index, key in enumerate(_EMOTION_KEYS):
            if index < self._emotion_combo.count():
                self._emotion_combo.setItemText(index, t(key))
        # v2.5.0: 策略选择器与 SeriesContext 按钮文案刷新
        if hasattr(self, "_strategy_label"):
            self._strategy_label.setText(t("production.strategy.label"))
        if hasattr(self, "_strategy_help"):
            self._strategy_help.setText(t("production.strategy.help"))
        if hasattr(self, "_series_edit_btn"):
            self._series_edit_btn.setText(t("production.strategy.series_edit"))
        if hasattr(self, "_strategy_combo"):
            for index, entry in enumerate(_STRATEGY_OPTIONS):
                key = entry[1]
                icon = entry[2]
                if index < self._strategy_combo.count():
                    self._strategy_combo.setItemText(index, f"{icon}  {t(key)}")
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
                name: t("production.status.pending") for name in self._step_statuses
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
        for index, (_row, _badge, _title, status_lbl, _num, _name) in enumerate(
            self._step_rows
        ):
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
