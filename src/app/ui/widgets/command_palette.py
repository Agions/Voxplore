#!/usr/bin/env python3
"""CommandPalette · Cmd+K 命令面板（Phase 2 快速导航）。

交互特性
--------

* **全局快捷键** ：通过 :py:class:`QShortcut` 绑定 ``Ctrl+K``
  （在 macOS 上 Qt 会自动把 ``Ctrl`` 翻译成 ``⌘ Cmd``）。
* **模糊搜索** ：标题 / 关键词 不区分大小写子串匹配；空 query
  显示全部命令。
* **键盘导航** ：上下方向键移动选中；Enter 触发当前项；Esc 关闭。
* **主题感知** ：通过 :py:class:`PaletteAwareMixin` 重新刷新 QSS。
* **动画进入** ：从 12px 偏移 + 透明进入（借用
  :py:mod:`app.ui.theme.animations`）。
"""

from __future__ import annotations

import logging
from typing import Sequence

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QKeyEvent, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.commands.registry import Command, CommandRegistry
from app.ui.main.pages.page_widgets import PaletteAwareMixin
from app.ui.theme.ds_tokens import FontWeights, Radii, _C, ui_font

logger = logging.getLogger(__name__)

__all__ = ["CommandPalette"]


class CommandPalette(PaletteAwareMixin, QWidget):
    """命令面板。

    Parameters
    ----------
    registry : CommandRegistry
        命令来源。面板本身**不**注册命令，只读。
    parent : QWidget, optional
        一般传 ``QMainWindow``，面板会用 ``window()`` 计算居中位置。
    shortcut : str, default ``"Ctrl+K"``
        触发显示 / 隐藏 的快捷键序列。
    """

    commandExecuted = Signal(str)  # command id

    DEFAULT_SHORTCUT: str = "Ctrl+K"
    DEFAULT_MAX_HEIGHT: int = 480
    DEFAULT_WIDTH: int = 600

    def __init__(
        self,
        registry: CommandRegistry,
        parent: QWidget | None = None,
        *,
        shortcut: str = DEFAULT_SHORTCUT,
    ) -> None:
        super().__init__(parent)
        self._init_palette_registry()

        self._registry = registry

        # 浮层属性
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("command_palette")

        self._build_ui()
        self._refresh_palette_brushes()
        self._apply_style()
        self._refresh_list("")

        # 全局快捷键
        self._shortcut = QShortcut(self)
        self._shortcut.setKey(shortcut)
        self._shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._shortcut.activated.connect(self.toggle)

        # 动画
        self._opacity_anim: QPropertyAnimation | None = None
        self.setWindowOpacity(0.0)

    # ───────────────────────────────────────────────
    #  UI 构建
    # ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        # 标题条
        title_row = QHBoxLayout()
        title_row.setContentsMargins(2, 0, 2, 0)
        title = QLabel("Command Palette")
        title.setObjectName("command_palette_title")
        font = ui_font(13, FontWeights.SemiBold)
        title.setFont(font)
        title_row.addWidget(title)
        title_row.addStretch(1)
        badge = QLabel("Esc")
        badge.setObjectName("command_palette_badge")
        badge.setFont(ui_font(11, FontWeights.Medium))
        title_row.addWidget(badge)
        outer.addLayout(title_row)

        # 搜索框
        self._search = QLineEdit()
        self._search.setObjectName("command_palette_search")
        self._search.setPlaceholderText("输入命令或搜索…")
        self._search.setFont(ui_font(13))
        self._search.textChanged.connect(self._on_query_changed)
        self._search.returnPressed.connect(self._activate_current)
        outer.addWidget(self._search)

        # 结果列表
        self._list = QListWidget()
        self._list.setObjectName("command_palette_list")
        self._list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setUniformItemSizes(True)
        self._list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._list.itemActivated.connect(
            lambda _item: self._activate_current())
        outer.addWidget(self._list, 1)

        # 底部 hint
        hint = QLabel("↑↓ 选择    Enter 确认    Esc 关闭")
        hint.setObjectName("command_palette_hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        hint.setFont(ui_font(11))
        outer.addWidget(hint)

        # 卡片尺寸约束
        self.setFixedWidth(self.DEFAULT_WIDTH)
        self.setMinimumHeight(220)
        self.setMaximumHeight(self.DEFAULT_MAX_HEIGHT)

    # ───────────────────────────────────────────────
    #  主题 + 数据刷新
    # ───────────────────────────────────────────────

    def _refresh_palette_brushes(self) -> None:
        # 这里不存 QColor；只用 QSS 在 _apply_style 里渲染
        pass

    def _apply_style(self) -> None:
        # 通过懒求值让主题切换更新
        def _factory() -> str:
            return f"""
                #command_palette {{
                    background: {_C.BG_GLASS};
                    border: 1px solid {_C.NEON_CYAN};
                    border-radius: {Radii.glass};
                }}
                #command_palette_title {{
                    color: {_C.TEXT_PRIMARY};
                }}
                #command_palette_badge {{
                    color: {_C.TEXT_MUTED};
                    background: {_C.BG_OVERLAY};
                    border-radius: 6px;
                    padding: 1px 8px;
                }}
                #command_palette_search {{
                    background: {_C.BG_INPUT};
                    color: {_C.TEXT_PRIMARY};
                    border: 1px solid {_C.BORDER_SUBTLE};
                    border-radius: 8px;
                    padding: 8px 10px;
                }}
                #command_palette_search:focus {{
                    border-color: {_C.NEON_CYAN};
                }}
                #command_palette_list {{
                    background: transparent;
                    border: none;
                    outline: none;
                    color: {_C.TEXT_PRIMARY};
                }}
                #command_palette_list::item {{
                    padding: 8px 10px;
                    border-radius: 6px;
                }}
                #command_palette_list::item:selected {{
                    background: {_C.PRIMARY_10};
                    color: {_C.NEON_CYAN};
                }}
                #command_palette_hint {{
                    color: {_C.TEXT_MUTED};
                    padding: 2px;
                }}
            """

        self._set_palette_style(self, _factory)
        # 子控件（QLineEdit/QListView）也会被 QSS 影响，但不强制包成可随主题切换
        # —— 上面 #xxx 选择器在主题切换后会自动随 _C 值刷新

    def apply_palette(self) -> None:  # type: ignore[override]
        super().apply_palette()
        self._refresh_palette_brushes()
        self._refresh_list(self._search.text())

    # ───────────────────────────────────────────────
    #  命令刷新
    # ───────────────────────────────────────────────

    def _on_query_changed(self, text: str) -> None:
        self._refresh_list(text)

    def _refresh_list(self, query: str) -> None:
        self._list.clear()
        commands = self._registry.search(query, limit=50)
        for cmd in commands:
            item = QListWidgetItem(self._format_item_text(cmd))
            item.setData(Qt.ItemDataRole.UserRole, cmd)
            self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    @staticmethod
    def _format_item_text(cmd: Command) -> str:
        shortcut = f"   {cmd.shortcut_hint}" if cmd.shortcut_hint else ""
        return f"{cmd.title}{shortcut}"

    # ───────────────────────────────────────────────
    #  显示 / 关闭
    # ───────────────────────────────────────────────

    def toggle(self) -> None:
        if self.isVisible():
            self.close()
        else:
            self.show_palette()

    def show_palette(self) -> None:
        # 居中到父窗口
        target = self.parent() if isinstance(self.parent(), QWidget) else self.window()
        anchor = target if isinstance(target, QWidget) else None
        if anchor is not None:
            aw = max(anchor.width(), 800)
            ah = max(anchor.height(), 600)
            x = anchor.x() + (aw - self.width()) // 2
            y = anchor.y() + max(80, ah // 5)
            self.move(QPoint(x, y))
        else:
            screen = self.screen()
            if screen is not None:
                geo = screen.availableGeometry()
                self.move(
                    geo.x() + (geo.width() - self.width()) // 2,
                    geo.y() + geo.height() // 5,
                )

        self._refresh_list("")
        self._search.clear()
        self.show()
        self.raise_()
        self.activateWindow()
        self._search.setFocus()

        # 渐入动画
        if self._opacity_anim is not None:
            self._opacity_anim.stop()
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(140)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._opacity_anim = anim
        anim.start()

    def close_palette(self) -> None:
        self.close()

    # ───────────────────────────────────────────────
    #  交互
    # ───────────────────────────────────────────────

    def _activate_current(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        cmd: Command = item.data(Qt.ItemDataRole.UserRole)
        self.commandExecuted.emit(cmd.id)
        self._run_command(cmd)
        self.close()

    def _run_command(self, cmd: Command) -> None:
        try:
            cmd.callback()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Command '%s' failed: %s", cmd.id, exc)

    # 键盘事件：Esc 关闭 / 上下方向键移动选择
    # type: ignore[override]
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._search.setFocus()
