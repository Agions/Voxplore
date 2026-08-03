"""Drop-zone controller for the main window.

Owns the ``dragEnterEvent`` / ``dropEvent`` hooks on the main window
and routes accepted drops to a single ``on_drop`` callback that the
main window wires up. Video-only MIME filter lives here so the rest
of the window doesn't need to know which extensions are accepted.

v2.5.0 (Phase 2 · 多文件上传)
    - 单参数回调 ``on_drop(path)`` 仍受支持（向后兼容）
    - 可选 ``multi_on_drop(paths)`` ：按拖入顺序一次性传入所有匹配视频路径
    - 拖入多文件时，优先调用 ``multi_on_drop``，避免「只取第一个」丢失上下文
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import cast

from PySide6.QtCore import QEvent
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QMainWindow

DropCallback = Callable[[str], None]
MultiDropCallback = Callable[[list[str]], None]


class MainWindowDropZone:
    """Drag-and-drop controller.

    Instantiated *with* a reference to the main window so it can
    intercept the Qt events on the window itself. The main window
    delegates ``dragEnterEvent`` and ``dropEvent`` to this object
    instead of implementing them inline.

    Only files with extensions in ``video_extensions`` are accepted;
    everything else is ignored so the OS doesn't show the copy/move
    cursor over an unhandled region.
    """

    DEFAULT_VIDEO_EXTENSIONS: tuple[str, ...] = (
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
    )

    def __init__(
        self,
        window: QMainWindow,
        on_drop: DropCallback | None = None,
        *,
        multi_on_drop: MultiDropCallback | None = None,
        video_extensions: Iterable[str] | None = None,
    ) -> None:
        self._window = window
        self._on_drop = on_drop
        self._multi_on_drop = multi_on_drop
        self._video_exts = tuple(
            e.lower() for e in (video_extensions or self.DEFAULT_VIDEO_EXTENSIONS)
        )
        # Make sure the window actually accepts drops. Tests may create
        # the drop zone on a host that hasn't called setAcceptDrops yet.
        self._window.setAcceptDrops(True)

    # ──────────────────────────────────────────────────────────
    # Qt event entry points (call from the main window's overrides)
    # ──────────────────────────────────────────────────────────

    def handle_drag_enter(self, event: QDragEnterEvent | QEvent) -> None:
        if not self._has_video_url(event):
            event.ignore()
            return
        # 运行时实际 event 一定是 QDragEnterEvent，但 stub/测试可能传入 duck-type。
        # 用 cast 显式表达意图，避开 QEvent 无 ``acceptProposedAction`` 的类型问题。
        cast(QDragEnterEvent, event).acceptProposedAction()

    def handle_drop(self, event: QDropEvent | QEvent) -> None:
        paths = self.collect_paths(event)
        if not paths:
            event.ignore()
            return
        cast(QDropEvent, event).acceptProposedAction()
        # v2.5.0: 优先多文件 callback（保留全量上下文），
        # 退化到单文件 callback（只传第一个，保持旧行为）。
        if self._multi_on_drop is not None:
            self._multi_on_drop(list(paths))
        elif self._on_drop is not None:
            self._on_drop(paths[0])

    # ──────────────────────────────────────────────────────────
    # 公开辅助：提取事件中所有匹配的视频路径（v2.5.0）
    # ──────────────────────────────────────────────────────────

    def collect_paths(self, event) -> list[str]:
        """从拖拽事件中提取所有匹配扩展名的本地文件路径。

        按 ``event.mimeData().urls()`` 的原始顺序返回，**去重**保持首次出现。
        返回空列表表示无可接受的视频（caller 自行决定 ignore）。
        """
        mime = getattr(event, "mimeData", None)
        if mime is None:
            return []
        md = mime() if callable(mime) else mime
        if md is None or not md.hasUrls():
            return []

        seen: set[str] = set()
        paths: list[str] = []
        for url in md.urls():
            path = url.toLocalFile()
            if not self._is_video(path):
                continue
            if path in seen:
                continue
            seen.add(path)
            paths.append(path)
        return paths

    # ──────────────────────────────────────────────────────────
    # 内部辅助
    # ──────────────────────────────────────────────────────────

    def _has_video_url(self, event) -> bool:
        mime = getattr(event, "mimeData", None)
        if mime is None:
            return False
        md = mime() if callable(mime) else mime
        if md is None or not md.hasUrls():
            return False
        return any(self._is_video(u.toLocalFile()) for u in md.urls())

    def _is_video(self, path: str) -> bool:
        return path.lower().endswith(self._video_exts)


__all__ = ["MainWindowDropZone", "DropCallback", "MultiDropCallback"]
