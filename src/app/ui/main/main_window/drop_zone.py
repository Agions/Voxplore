"""Drop-zone controller for the main window.

Owns the ``dragEnterEvent`` / ``dropEvent`` hooks on the main window
and routes accepted drops to a single ``on_drop`` callback that the
main window wires up. Video-only MIME filter lives here so the rest
of the window doesn't need to know which extensions are accepted.
"""

from __future__ import annotations

from typing import Callable, Iterable

from PySide6.QtCore import QEvent
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QMainWindow

DropCallback = Callable[[str], None]


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
        ".mp4", ".mov", ".avi", ".mkv",
    )

    def __init__(
        self,
        window: QMainWindow,
        on_drop: DropCallback,
        *,
        video_extensions: Iterable[str] | None = None,
    ) -> None:
        self._window = window
        self._on_drop = on_drop
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
        event.acceptProposedAction()

    def handle_drop(self, event: QDropEvent | QEvent) -> None:
        mime = event.mimeData()
        if mime is None or not mime.hasUrls():
            event.ignore()
            return
        for url in mime.urls():
            path = url.toLocalFile()
            if self._is_video(path):
                self._on_drop(path)
                event.acceptProposedAction()
                # We intentionally only start production with the
                # *first* matching video, matching the original
                # window-level behavior.
                return
        event.ignore()

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


__all__ = ["MainWindowDropZone"]
