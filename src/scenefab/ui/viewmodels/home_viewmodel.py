#!/usr/bin/env python3
"""Home page ViewModel.

Binds to ``scenefab.project_manager.ProjectManager`` and exposes a
flattened snapshot of the current project's status to the view:

- media_count   : number of media files in the active project
- scene_count   : number of video tracks on the active project timeline
- script_status : human-readable state of the script generation stage
- export_config : tuple (resolution, fps, bitrate) for the active project

The view (``HomePage``) reads these on construction and updates its 4
status cards accordingly. The ViewModel re-emits on every project
event from the service layer, so the cards stay in sync as the user
imports media, edits timeline, or saves the project.

The ViewModel is intentionally tolerant: when no project is open (the
most common state on a fresh install), all counts read 0 and statuses
fall back to the same Chinese defaults the static page used to show.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal

from scenefab.ui.viewmodels import ViewModelBase

if TYPE_CHECKING:
    from scenefab.application import Application


class HomePageViewModel(ViewModelBase):
    """Read-only home dashboard ViewModel.

    Properties
    ----------
    media_count : int
    scene_count : int
    script_status : str
    export_config : str
    """

    media_count_changed = Signal()
    scene_count_changed = Signal()
    script_status_changed = Signal()
    export_config_changed = Signal()
    recent_projects_changed = Signal()

    def __init__(self, application: Application | None = None, parent=None) -> None:
        super().__init__(application, parent)
        self._media_count = 0
        self._scene_count = 0
        self._script_status = "待生成"
        self._export_config = "1080x1920"
        self._recent_projects: list[str] = []
        self._bound = False

    # ──────────────────────────────────────────────────────────
    # 公开属性 (Qt Property 风格 — 视图可直接访问 .xxx)
    # ──────────────────────────────────────────────────────────

    @property
    def media_count(self) -> int:
        return self._media_count

    @property
    def scene_count(self) -> int:
        return self._scene_count

    @property
    def script_status(self) -> str:
        return self._script_status

    @property
    def export_config(self) -> str:
        return self._export_config

    @property
    def recent_projects(self) -> list[str]:
        return list(self._recent_projects)

    # ──────────────────────────────────────────────────────────
    # 绑定 / 解绑
    # ──────────────────────────────────────────────────────────

    def bind(self) -> None:
        if self._bound:
            return
        self._connect_and_seed(
            {
                "project_opened": self._on_project_opened,
                "project_closed": self._on_project_closed,
                "project_saved": lambda _: self._refresh_from_project(),
                "project_deleted": lambda _: self._set_media(0),
                "recent_projects_updated": self._on_recent_updated,
            },
            initial_project_opened="",
            initial_recent=self._recent_projects,
        )

    def unbind(self) -> None:
        if not self._bound:
            return
        self._unbind_pm_signals(
            {
                "project_opened": self._on_project_opened,
                "project_closed": self._on_project_closed,
            }
        )
        self._bound = False

    # ──────────────────────────────────────────────────────────
    # 信号处理
    # ──────────────────────────────────────────────────────────

    def _on_project_opened(self, _project_id: str) -> None:
        self._refresh_from_project()

    def _on_project_closed(self, _project_id: str) -> None:
        self._set_media(0)
        self._set_scenes(0)
        self._set_script_status("待生成")
        self._set_export_config("1080x1920")

    def _on_recent_updated(self, recents: list) -> None:
        self._recent_projects = list(recents) if recents else []
        self.recent_projects_changed.emit()

    # ──────────────────────────────────────────────────────────
    # 内部辅助
    # ──────────────────────────────────────────────────────────

    # _project_manager / _current_project 继承自 ViewModelBase

    def _refresh_from_project(self) -> None:
        project = self._current_project()
        if project is None:
            self._on_project_closed("")
            return

        # media: 媒体文件数
        self._set_media(len(project.media_files))

        # scene: 用 timeline.tracks 数量作为"已拆场景"代理
        timeline = project.timeline
        scene_count = len(timeline.tracks) if timeline is not None else 0
        self._set_scenes(scene_count)

        # script: 有 timeline tracks > 0 → "已生成" 否则 "待生成"
        if scene_count > 0:
            self._set_script_status("已生成")
        else:
            self._set_script_status("待生成")

        # export: 从 settings 拿 resolution / fps / bitrate
        settings = project.settings
        resolution = getattr(settings, "resolution", None) or "1080x1920"
        fps = getattr(settings, "fps", None) or 30
        bitrate = getattr(settings, "bitrate", None) or "8000k"
        self._set_export_config(f"{resolution} · {fps}fps · {bitrate}")

    def _set_media(self, n: int) -> None:
        if n != self._media_count:
            self._media_count = n
            self.media_count_changed.emit()

    def _set_scenes(self, n: int) -> None:
        if n != self._scene_count:
            self._scene_count = n
            self.scene_count_changed.emit()

    def _set_script_status(self, s: str) -> None:
        if s != self._script_status:
            self._script_status = s
            self.script_status_changed.emit()

    def _set_export_config(self, s: str) -> None:
        if s != self._export_config:
            self._export_config = s
            self.export_config_changed.emit()


__all__ = ["HomePageViewModel"]
