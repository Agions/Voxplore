"""Project I/O controller for the main window.

Owns the file dialogs and persistence calls for ``.scenefab`` projects:
- ``open_project(path)`` — prompt for a file (or use the supplied path),
  load via ``ProjectManager`` and hand it off to the production page.
- ``save_project()`` — save the most recent in-memory project to disk.

Extracted from ``SceneFabMainWindow`` as part of the Phase B
single-responsibility refactor. The controller takes its dependencies
through callbacks so it does not import the main window or any concrete
service directly — easier to test, easier to swap implementations.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

if TYPE_CHECKING:
    from app.services.video.monologue_maker import MonologueProject


# Callback alias: ``MonologueProject`` may be ``None`` when nothing is loaded
# yet, so the getter returns that explicitly instead of raising.
GetProjectCallable = Callable[[], "MonologueProject | None"]
SetProjectCallable = Callable[["MonologueProject"], None]


class ProjectIOController:
    """Drive the .scenefab open / save dialogs.

    The class is a plain Python object — *not* a QObject — because Qt owns
    the dialogs through the main window itself; this controller just shows
    them and forwards the result via callbacks.
    """

    PROJECT_FILE_FILTER = "SceneFab 项目 (*.scenefab)"

    def __init__(
        self,
        window: QMainWindow,
        *,
        get_project_manager: Callable[[], object | None],
        get_last_project: GetProjectCallable,
        set_last_project: SetProjectCallable,
        get_production_page: Callable[[], object | None],
        navigate_to_create: Callable[[], None],
        show_status: Callable[[str], None],
        show_message: Callable[[str, str], None],
    ) -> None:
        self._window = window
        self._get_project_manager = get_project_manager
        self._get_last_project = get_last_project
        self._set_last_project = set_last_project
        self._get_production_page = get_production_page
        self._navigate_to_create = navigate_to_create
        self._show_status = show_status
        self._show_message = show_message

    # ──────────────────────────────────────────────────────────
    # 打开项目
    # ──────────────────────────────────────────────────────────

    def open_project(self, project_path: str = "") -> None:
        """Open a .scenefab project file, or prompt for one when ``project_path`` is empty."""
        if not project_path:
            project_path, _ = QFileDialog.getOpenFileName(
                self._window,
                "打开 SceneFab 项目",
                "",
                self.PROJECT_FILE_FILTER,
            )
        if not project_path:
            return

        pm = self._get_project_manager()
        if pm is None:
            self._show_message("项目管理器未就绪", "error")
            return

        project = pm.load_project(project_path)
        if project is None:
            self._show_message(f"加载项目失败:\n{project_path}", "error")
            return

        self._set_last_project(project)
        self._show_status(f"已加载项目: {project.name}")

        page = self._get_production_page()
        if page is not None and hasattr(page, "load_project_data"):
            page.load_project_data(project)

        self._navigate_to_create()

    # ──────────────────────────────────────────────────────────
    # 保存项目
    # ──────────────────────────────────────────────────────────

    def save_project(self) -> None:
        """Save the most recent project to a .scenefab file."""
        last_project = self._get_last_project()
        if last_project is None:
            QMessageBox.warning(self._window, "无法保存", "请先完成生产流程")
            return

        default_name = f"{last_project.name}.scenefab"
        file_path, _ = QFileDialog.getSaveFileName(
            self._window,
            "保存项目",
            default_name,
            self.PROJECT_FILE_FILTER,
        )
        if not file_path:
            return

        try:
            saved = last_project.save(file_path)
        except Exception as e:
            QMessageBox.critical(self._window, "保存失败", f"保存项目出错:\n{e}")
            return

        self._show_status(f"项目已保存: {saved}")
        QMessageBox.information(self._window, "保存成功", f"项目已保存到:\n{saved}")


__all__ = ["ProjectIOController"]
