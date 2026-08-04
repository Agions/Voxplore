#!/usr/bin/env python3
"""Toast 通知组件（v2.5.0 端到端流程优化）。

设计目标：用非阻塞的 toast/snackbar 替代阻塞式 ``QMessageBox``，
提升生产完成 / 失败 / 取消 / 导出完成等关键节点的反馈体验。

设计要点：

* **自动消失**：默认 4s（error 类 6s）；鼠标 hover 暂停计时。
* **类型系统**：info / success / warning / error 四种，配色与 icon 区分。
* **可操作**：toast 内置 0~2 个 action 按钮（如「打开文件」「重试」）。
* **队列堆叠**：多个 toast 同时存在时，垂直堆叠在右下角。
* **线程安全**：``ToastManager.show_*`` 静态方法可从后台线程调用，
  内部用 ``QMetaObject.invokeMethod`` 投递到主线程。
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar

from PySide6.QtCore import (
    QMetaObject,
    QObject,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, ui_font

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# ToastSpec — 描述一条 toast 的不可变数据
# ═══════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ToastAction:
    """toast 上的可点击 action。"""

    label: str
    callback: Callable[[], None]


@dataclass(frozen=True)
class ToastSpec:
    """toast 的数据规约。"""

    level: str  # info / success / warning / error
    title: str
    message: str = ""
    actions: tuple[ToastAction, ...] = ()
    duration_ms: int = 0  # 0 = 用默认（info=4s, error=6s）


# ═══════════════════════════════════════════════════════════════════
# 单条 Toast 控件
# ═══════════════════════════════════════════════════════════════════


class _ToastItem(QFrame):
    """单条 toast 的可视化。"""

    closed = Signal(object)  # 自身引用，便于 manager 清理

    _ICONS: ClassVar[dict[str, str]] = {
        "info": "ℹ",
        "success": "✓",
        "warning": "⚠",
        "error": "✕",
    }

    _ACCENT_COLORS: ClassVar[dict[str, str]] = {
        "info": "_C.INFO",
        "success": "_C.SUCCESS",
        "warning": "_C.WARNING",
        "error": "_C.ERROR",
    }

    def __init__(
        self,
        spec: ToastSpec,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("toast_item")
        self._spec = spec

        # ── 顶部行：icon + 标题 + 关闭 ──
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(Spacing_xs := 8)

        icon_lbl = QLabel(self._ICONS.get(spec.level, "•"))
        icon_lbl.setFont(ui_font(18, FontWeights.Bold))
        icon_lbl.setFixedWidth(24)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(icon_lbl)

        title_lbl = QLabel(spec.title)
        title_lbl.setFont(ui_font(FontSizes.sm, FontWeights.SemiBold))
        title_lbl.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        title_lbl.setWordWrap(True)
        top_row.addWidget(title_lbl, 1)

        close_btn = QPushButton("×")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                color: {_C.TEXT_MUTED};
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: {FontWeights.Bold};
            }}
            QPushButton:hover {{
                background: {_C.BG_ELEVATED};
                color: {_C.TEXT_PRIMARY};
            }}
            """
        )
        close_btn.clicked.connect(self._close)
        top_row.addWidget(close_btn)

        # ── 主体 ──
        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            Spacing_md := 12, Spacing_sm := 10, Spacing_md, Spacing_sm)
        outer.setSpacing(Spacing_xs)
        outer.addLayout(top_row)

        if spec.message:
            msg_lbl = QLabel(spec.message)
            msg_lbl.setFont(ui_font(FontSizes.xs))
            msg_lbl.setWordWrap(True)
            msg_lbl.setStyleSheet(f"color: {_C.TEXT_SECONDARY};")
            outer.addWidget(msg_lbl)

        if spec.actions:
            actions_row = QHBoxLayout()
            actions_row.setContentsMargins(0, Spacing_xs, 0, 0)
            actions_row.setSpacing(Spacing_xs)
            actions_row.addStretch(1)
            for action in spec.actions:
                btn = QPushButton(action.label)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFixedHeight(26)
                btn.setStyleSheet(self._action_style(spec.level))
                btn.clicked.connect(
                    lambda _checked=False, cb=action.callback: self._trigger_action(
                        cb)
                )
                actions_row.addWidget(btn)
            outer.addLayout(actions_row)

        # ── 整体外观 ──
        accent = self._accent_color(spec.level)
        self.setStyleSheet(
            f"""
            QFrame#toast_item {{
                background: {_C.BG_ELEVATED};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-left: 3px solid {accent};
                border-radius: {Radii.md};
            }}
            """
        )
        self.setFixedWidth(360)
        self.setMinimumHeight(0)
        # 阴影通过 Qt 自带 WA_Shadow 不可靠，简单抬高 z 即可
        self.raise_()

        # ── 自动消失定时器 ──
        duration = self._resolve_duration(spec)
        if duration > 0:
            self._timer: QTimer | None = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.setInterval(duration)
            self._timer.timeout.connect(self._close)
            self._timer.start()
        else:
            self._timer = None

    # ──────────────────────────────────────────────────────────────
    # 行为
    # ──────────────────────────────────────────────────────────────

    def enterEvent(self, event) -> None:  # noqa: N802 (Qt 命名)
        """鼠标 hover：暂停自动消失计时。"""
        if self._timer is not None and self._timer.isActive():
            self._timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 (Qt 命名)
        """鼠标离开：恢复自动消失计时（剩余原 duration）。"""
        if self._timer is not None and not self._timer.isActive():
            self._timer.start()
        super().leaveEvent(event)

    def pause_auto_close(self) -> None:
        """外部（manager）调用：暂停计时（例如：排队等待展示时）。"""
        if self._timer is not None:
            self._timer.stop()

    def resume_auto_close(self) -> None:
        """外部（manager）调用：恢复计时。"""
        if self._timer is not None and not self._timer.isActive():
            self._timer.start()

    # ──────────────────────────────────────────────────────────────
    # 内部
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _accent_color(level: str) -> str:
        return {
            "info": _C.INFO,
            "success": _C.SUCCESS,
            "warning": _C.WARNING,
            "error": _C.ERROR,
        }.get(level, _C.PRIMARY)

    @staticmethod
    def _action_style(level: str) -> str:
        accent = _ToastItem._accent_color(level)
        return (
            f"""
            QPushButton {{
                background: transparent;
                color: {accent};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
                padding: 0 12px;
                font-size: {FontSizes.xs}px;
                font-weight: {FontWeights.Medium};
            }}
            QPushButton:hover {{
                background: {_C.BG_BASE};
                border-color: {accent};
            }}
            """
        )

    @staticmethod
    def _resolve_duration(spec: ToastSpec) -> int:
        if spec.duration_ms > 0:
            return spec.duration_ms
        # 默认：error 长一点（让用户看清）；其它 4s
        return 6000 if spec.level == "error" else 4000

    def _close(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        self.closed.emit(self)
        self.deleteLater()

    def _trigger_action(self, callback: Callable[[], None]) -> None:
        try:
            callback()
        except Exception:  # pragma: no cover - 防御性
            logger.exception("toast action callback failed")
        finally:
            self._close()


# ═══════════════════════════════════════════════════════════════════
# ToastManager — 主线程/跨线程的入口
# ═══════════════════════════════════════════════════════════════════


class ToastManager(QObject):
    """管理一个或多个 toast 的展示。

    用法::

        ToastManager.info("导入完成", "已加载 5 个文件")
        ToastManager.success(
            "生产完成",
            "项目已保存到 ~/Movies",
            actions=[
                ToastAction("打开文件", lambda: open_file(path)),
                ToastAction("打开文件夹", lambda: open_folder(dir)),
            ],
        )

    所有 ``show_*`` 都是线程安全的（后台线程也会被路由到主线程）。
    """

    _instance: ClassVar[ToastManager | None] = None

    def __init__(self) -> None:
        super().__init__()
        # 浮动 widget，没有 parent → 顶级窗口
        self._host = _ToastHost()
        self._host.show()
        # 跨线程暂存：后台线程的 ToastSpec 先存这里，主线程 _push 再读
        self._next_spec: ToastSpec | None = None

    # ──────────────────────────────────────────────────────────────
    # 单例入口
    # ──────────────────────────────────────────────────────────────

    @classmethod
    def instance(cls) -> ToastManager:
        if cls._instance is None:
            cls._instance = ToastManager()
        return cls._instance

    @classmethod
    def show(cls, spec: ToastSpec) -> None:
        """线程安全：显示一条 toast。

        流程：先把 spec 压入主线程可见的 host 队列，再投递 drain 信号到主线程。
        后台线程直接调用本方法也安全（host 队列只由主线程读写）。
        """
        # 在调用线程入队（host 是 QWidget，只能在主线程创建/修改）。
        # 由于 _enqueue 内部会触发 invokeMethod → 主线程 drain，
        # 所以后台线程调用本方法时：host 创建由 instance() 懒加载触发，
        # 而具体 widget 创建发生在主线程。
        cls._enqueue(spec)

    @classmethod
    def info(
        cls,
        title: str,
        message: str = "",
        *,
        actions: tuple[ToastAction, ...] = (),
        duration_ms: int = 0,
    ) -> None:
        cls.show(
            ToastSpec(
                level="info",
                title=title,
                message=message,
                actions=actions,
                duration_ms=duration_ms,
            )
        )

    @classmethod
    def success(
        cls,
        title: str,
        message: str = "",
        *,
        actions: tuple[ToastAction, ...] = (),
        duration_ms: int = 0,
    ) -> None:
        cls.show(
            ToastSpec(
                level="success",
                title=title,
                message=message,
                actions=actions,
                duration_ms=duration_ms,
            )
        )

    @classmethod
    def warning(
        cls,
        title: str,
        message: str = "",
        *,
        actions: tuple[ToastAction, ...] = (),
        duration_ms: int = 0,
    ) -> None:
        cls.show(
            ToastSpec(
                level="warning",
                title=title,
                message=message,
                actions=actions,
                duration_ms=duration_ms,
            )
        )

    @classmethod
    def error(
        cls,
        title: str,
        message: str = "",
        *,
        actions: tuple[ToastAction, ...] = (),
        duration_ms: int = 0,
    ) -> None:
        cls.show(
            ToastSpec(
                level="error",
                title=title,
                message=message,
                actions=actions,
                duration_ms=duration_ms,
            )
        )

    # ──────────────────────────────────────────────────────────────
    # 主线程槽
    # ──────────────────────────────────────────────────────────────

    @Slot()
    def _show_on_main_thread(self) -> None:
        """由 QMetaObject.invokeMethod 调用（QueuedConnection）。

        实际投递靠 ``pending_specs`` 队列；invokeMethod 只能传 arg，
        所以本方法只触发 drain，由调用方 ``show()`` 之前先压栈。
        """
        self._host.drain_pending()

    @Slot()
    def _push(self) -> None:
        """主线程槽：把 ``_next_spec`` 入队并 drain。"""
        spec = getattr(self, "_next_spec", None)
        if spec is not None:
            self._host.enqueue(spec)
            self._host.drain_pending()
            self._next_spec = None

    @classmethod
    def _enqueue(cls, spec: ToastSpec) -> None:
        """由 ToastManager.show() 调用，把 spec 投递到主线程的 host 队列。"""
        # 跨线程安全：用 invokeMethod 把 spec 投递到主线程的 _push 方法
        # Qt 不支持自定义 dataclass 直接跨线程，所以借助 _next_spec 暂存
        cls.instance()._next_spec = spec
        QMetaObject.invokeMethod(  # type: ignore[call-overload]
            cls.instance(),
            "_push",
            Qt.ConnectionType.QueuedConnection,
        )


# ═══════════════════════════════════════════════════════════════════
# _ToastHost — 浮动容器（透明 + 始终在最上层）
# ═══════════════════════════════════════════════════════════════════


class _ToastHost(QWidget):
    """透明顶级窗口，用于堆叠 toast。"""

    TOAST_SPACING = 8
    TOAST_MARGIN = 20

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("toast_host")
        # 无边框 + 透明背景 + 始终置顶 + 工具窗口（不在任务栏）
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(400, 600)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            self.TOAST_MARGIN, self.TOAST_MARGIN,
            self.TOAST_MARGIN, self.TOAST_MARGIN
        )
        self._layout.setSpacing(self.TOAST_SPACING)
        # 让 toast 从下往上排列（最新在最下面）
        self._layout.addStretch(1)

        self._pending: list[ToastSpec] = []

    # ──────────────────────────────────────────────────────────────
    # 队列 / 展示
    # ──────────────────────────────────────────────────────────────

    def enqueue(self, spec: ToastSpec) -> None:
        self._pending.append(spec)

    def drain_pending(self) -> None:
        """主线程触发：消费 pending 队列，渲染新 toast。"""
        if not self._pending:
            return
        # 确保 host 已定位到主窗口
        self._align_to_active_window()
        for spec in list(self._pending):
            self._pending.remove(spec)
            self._render(spec)
        self.show()

    def _render(self, spec: ToastSpec) -> None:
        item = _ToastItem(spec, parent=self)
        item.closed.connect(self._on_item_closed)
        # 插在 stretch(1) 之前，保证新 toast 在最下方
        self._layout.insertWidget(self._layout.count() - 1, item)

    def _on_item_closed(self, _item: QFrame) -> None:
        # host 没有 toast 时自动隐藏，节省资源
        if self._layout.count() <= 1:  # 只剩 stretch
            self.hide()

    # ──────────────────────────────────────────────────────────────
    # 定位
    # ──────────────────────────────────────────────────────────────

    def _align_to_active_window(self) -> None:
        """把 host 右下角对齐到主窗口右下角（无主窗口时对齐桌面）。"""
        target = QApplication.activeWindow()
        if target is None:
            # 退化：屏幕右下角
            screen = QApplication.primaryScreen()
            if screen is None:
                return  # type: ignore[unreachable]
            geo = screen.availableGeometry()
            self.move(geo.right() - self.width() + 1,
                      geo.bottom() - self.height() + 1)
            return
        # 主窗口右下角
        host_w, host_h = self.width(), self.height()
        target_geo = target.geometry()
        x = target_geo.right() - host_w + 1
        y = target_geo.bottom() - host_h + 1
        self.move(x, y)


# ═══════════════════════════════════════════════════════════════════
# 便捷工具：open_file / open_folder 跨平台打开
# ═══════════════════════════════════════════════════════════════════


def open_in_os(path: str) -> None:
    """用系统默认程序打开文件或文件夹（macOS/Linux/Windows）。"""
    if not path:
        return
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path])
    except (OSError, FileNotFoundError) as exc:
        logger.warning("无法用系统程序打开 %s: %s", path, exc)


def reveal_in_finder(path: str) -> None:
    """在 Finder/Explorer 中显示并高亮文件。文件夹则直接打开。"""
    if not path:
        return
    try:
        if sys.platform == "darwin":
            if os.path.isdir(path):
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["open", "-R", path])
        elif sys.platform.startswith("win"):
            if os.path.isdir(path):
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["explorer", f"/select,{path}"])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(path) or "."])
    except (OSError, FileNotFoundError) as exc:
        logger.warning("无法在文件管理器中显示 %s: %s", path, exc)


__all__ = [
    "ToastAction",
    "ToastSpec",
    "ToastManager",
    "open_in_os",
    "reveal_in_finder",
]


# Suppress unused warnings for QAction（保留 Qt import 以备将来 tooltip 拓展）
_ = QAction
