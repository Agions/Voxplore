"""Assets import controller for the main window.

Owns the file-picker dialog for importing media assets. After the user
picks files the controller:

- forwards the list to the ``AssetsPage`` so the table reflects them,
- copies each file into the current project's ``media/`` directory (if a
  project is open), and
- registers the resulting ``ProjectMedia`` entries with the project via
  ``ProjectManager``.

Extracted from ``SceneFabMainWindow`` as part of the Phase B
single-responsibility refactor. All dependencies are injected via
callbacks so this controller does not import the main window or any
concrete service directly.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QFileDialog, QMainWindow


# File extensions accepted by the importer. Includes video, audio and
# image types since ``ProjectMedia`` covers all media kinds.
ASSETS_FILE_FILTER = (
    "媒体文件 ("
    "*.mp4 *.mov *.avi *.mkv "
    "*.mp3 *.wav "
    "*.jpg *.png"
    ");;所有文件 (*)"
)


class AssetsIOController:
    """Drive the import-assets dialog and propagate the result.

    Plain Python object, not a QObject. The QFileDialog is parented to
    the main window and the asset list is forwarded via callbacks.
    """

    def __init__(
        self,
        window: QMainWindow,
        *,
        get_project_manager: Callable[[], object | None],
        get_assets_page: Callable[[], object | None],
        show_status: Callable[[str], None],
    ) -> None:
        self._window = window
        self._get_project_manager = get_project_manager
        self._get_assets_page = get_assets_page
        self._show_status = show_status

    # ──────────────────────────────────────────────────────────
    # 公共 API
    # ──────────────────────────────────────────────────────────

    def import_assets(self) -> None:
        """Show the import dialog and forward the selected files."""
        files, _ = QFileDialog.getOpenFileNames(
            self._window,
            "导入素材",
            "",
            ASSETS_FILE_FILTER,
        )
        if not files:
            return

        self._show_status(f"已选择 {len(files)} 个素材文件")

        # Show imported files in the AssetsPage list, if it exists.
        assets_page = self._get_assets_page()
        if assets_page is not None and hasattr(assets_page, "add_imported_files"):
            assets_page.add_imported_files(files)

        # Register media files with the current project, if one is open.
        pm = self._get_project_manager()
        if pm is None:
            return

        current = pm.get_current_project()
        if current is None:
            return

        self._register_media_files(pm, current, files)

    # ──────────────────────────────────────────────────────────
    # 内部辅助
    # ──────────────────────────────────────────────────────────

    def _register_media_files(
        self,
        pm,
        current,
        files: list[str],
    ) -> None:
        """Copy each file into ``<project>/media/`` and add a ``ProjectMedia`` entry."""
        from app.models.project_models import ProjectMedia

        media_dir = Path(current.path) / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        for fp in files:
            src = Path(fp)
            dst = media_dir / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
            media = ProjectMedia(
                id=f"{src.stem}_{src.suffix.lstrip('.')}",
                name=src.name,
                type=src.suffix.lstrip(".").lower(),
                path=str(dst),
            )
            current.add_media_file(media)
        pm.save_project(current.id)


__all__ = ["AssetsIOController", "ASSETS_FILE_FILTER"]
