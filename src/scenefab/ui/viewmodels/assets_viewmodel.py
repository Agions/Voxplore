#!/usr/bin/env python3
"""Assets page ViewModel (Phase 2C).

Drives the "project assets" workspace — current project media/scripts/
audio/exports + a recent projects list sourced from
:py:meth:`ProjectManager.get_recent_projects`.

Public surface
--------------

Properties (read by the view)
- :attr:`current_assets`     : :class:`AssetSummary` for the active project
- :attr:`recent_projects`    : ``list[RecentProjectInfo]`` (cached)

Signals
- :attr:`current_assets_changed`     — emitted when the summary updates
- :attr:`recent_projects_changed`    — emitted when the list refreshes

Inputs (called by the view / router)
- :meth:`refresh`              — re-pull from service layer
- :meth:`open_recent(path)`    — open a project from the recent list
- :meth:`import_media(files)`  — forward media import to ProjectManager

Design notes
------------

`ProjectManager.get_recent_projects()` returns ``list[str]`` (paths).
For the UI we wrap each path in :class:`RecentProjectInfo` carrying
display metadata (name, mtime, size, exists). The wrapping is local to
the ViewModel — we don't change the service surface.

`Path.stat()` is reasonably cheap (single syscall) and we never iterate
huge lists, so we do it eagerly on each :meth:`refresh`. If a recent
list ever grows past ~50 entries, switch to a worker-thread build.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Signal

from scenefab.project_manager import Project, ProjectManager
from scenefab.ui.viewmodels import ViewModelBase

if TYPE_CHECKING:
    from scenefab.application import Application


# ── 数据类 ──────────────────────────────────────────────────────────
@dataclass(frozen=True)
class RecentProjectInfo:
    """Display metadata for a single entry in the recent projects list.

    Fields
    ------
    path : str
        Absolute project file path.
    name : str
        Human-readable name (``Path(path).stem``).
    last_opened : datetime
        File mtime (best-effort — fall back to ``datetime.fromtimestamp(0)``
        if stat fails).
    size_mb : float
        File size in MB. ``0.0`` if unavailable.
    exists : bool
        Whether the path still resolves to a real file. ``False`` entries
        are still rendered (so the user can see and remove stale links)
        but visually muted.
    """

    path: str
    name: str
    last_opened: datetime = field(default_factory=lambda: datetime.fromtimestamp(0))
    size_mb: float = 0.0
    exists: bool = False


@dataclass(frozen=True)
class AssetSummary:
    """Aggregate counts for the active project.

    Fields default to 0 (no project) so the view can render
    deterministically even before the first ``project_opened`` fires.
    """

    media_count: int = 0
    script_count: int = 0
    audio_count: int = 0
    export_count: int = 0

    @property
    def total(self) -> int:
        return self.media_count + self.script_count + self.audio_count + self.export_count

    @property
    def is_empty(self) -> bool:
        return self.total == 0


def _build_recent_info(path_str: str) -> RecentProjectInfo:
    """Wrap a project path string into a RecentProjectInfo.

    Pure helper — never raises (falls back to safe defaults)."""
    p = Path(path_str)
    name = p.stem or path_str
    exists = p.is_file()
    if not exists:
        return RecentProjectInfo(path=path_str, name=name, exists=False)
    try:
        st = p.stat()
        last = datetime.fromtimestamp(st.st_mtime)
        size_mb = round(st.st_size / (1024 * 1024), 2)
        return RecentProjectInfo(
            path=path_str,
            name=name,
            last_opened=last,
            size_mb=size_mb,
            exists=True,
        )
    except OSError:
        return RecentProjectInfo(path=path_str, name=name, exists=False)


# ── 主 ViewModel ──────────────────────────────────────────────────────
class AssetsPageViewModel(ViewModelBase):
    """Project assets + recent projects ViewModel."""

    current_assets_changed = Signal()
    recent_projects_changed = Signal()

    def __init__(self, application: Application | None = None, parent=None) -> None:
        super().__init__(application, parent)
        self._current_assets: AssetSummary = AssetSummary()
        self._recent_projects: list[RecentProjectInfo] = []
        self._bound = False

    # ── 公开属性 ────────────────────────────────────────────────────
    @property
    def current_assets(self) -> AssetSummary:
        return self._current_assets

    @property
    def recent_projects(self) -> list[RecentProjectInfo]:
        return list(self._recent_projects)

    # ── 绑定 / 解绑 ─────────────────────────────────────────────────
    def bind(self) -> None:
        if self._bound:
            return
        pm = self._project_manager()
        if pm is None:
            return
        pm.project_opened.connect(self._on_project_opened)
        pm.project_closed.connect(self._on_project_closed)
        pm.project_saved.connect(lambda _: self._refresh_current_assets())
        pm.project_deleted.connect(lambda _: self._refresh_current_assets())
        pm.recent_projects_updated.connect(self._on_recent_updated)
        # Pull initial state
        self._on_project_opened("")
        self._on_recent_updated(pm.recent_projects or [])
        self._bound = True

    def unbind(self) -> None:
        if not self._bound:
            return
        pm = self._project_manager()
        if pm is not None:
            try:
                pm.project_opened.disconnect(self._on_project_opened)
                pm.project_closed.disconnect(self._on_project_closed)
            except (RuntimeError, TypeError):
                # Signal was never connected (no project_manager)
                pass
        self._bound = False

    # ── 信号处理 ───────────────────────────────────────────────────
    def _on_project_opened(self, _project_id: str) -> None:
        self._refresh_current_assets()

    def _on_project_closed(self, _project_id: str) -> None:
        self._set_current_assets(AssetSummary())

    def _on_recent_updated(self, recents: list) -> None:
        self._recent_projects = [_build_recent_info(p) for p in (recents or [])]
        self.recent_projects_changed.emit()

    # ── 业务入口 (供 view 调用) ─────────────────────────────────────
    def refresh(self) -> None:
        """Re-pull both current assets and recent projects."""
        self._refresh_current_assets()
        pm = self._project_manager()
        if pm is not None:
            self._on_recent_updated(pm.recent_projects or [])

    def open_recent(self, path: str) -> bool:
        """Open a project from the recent list.

        Returns True if the project was opened, False otherwise (no
        project_manager, project not found, or open raised)."""
        pm = self._project_manager()
        if pm is None:
            return False
        if not Path(path).is_file():
            return False
        try:
            pm.open_project(path)
            return True
        except Exception:  # noqa: BLE001 - PM may raise on corrupt file
            return False

    def import_media(self, files: list[str]) -> int:
        """Forward a list of media paths to ProjectManager.

        Returns the number of media files added (best-effort — exceptions
        on individual files are caught so the call still surfaces a count
        for the rest)."""
        pm = self._project_manager()
        if pm is None or not files:
            return 0
        added = 0
        for f in files:
            try:
                pm.add_media_file(f)
                added += 1
            except Exception:  # noqa: BLE001
                continue
        return added

    # ── 内部辅助 ────────────────────────────────────────────────────
    def _project_manager(self) -> ProjectManager | None:
        app = self._application
        if app is None:
            return None
        return app.get_service(ProjectManager)

    def _current_project(self) -> Project | None:
        pm = self._project_manager()
        if pm is None:
            return None
        return pm.get_current_project()

    def _refresh_current_assets(self) -> None:
        project = self._current_project()
        if project is None:
            self._set_current_assets(AssetSummary())
            return
        # media: media_files list
        media_count = len(project.media_files) if hasattr(project, "media_files") else 0
        # script / audio / export: 没有这些原生 list,
        # 退化为 media + 0 / 0 / 0 (后续 Phase 接入 assets registry 时扩展)
        self._set_current_assets(
            AssetSummary(
                media_count=media_count,
                script_count=0,
                audio_count=0,
                export_count=0,
            )
        )

    def _set_current_assets(self, summary: AssetSummary) -> None:
        if summary != self._current_assets:
            self._current_assets = summary
            self.current_assets_changed.emit()


__all__ = [
    "AssetsPageViewModel",
    "AssetSummary",
    "RecentProjectInfo",
    "_build_recent_info",
]
