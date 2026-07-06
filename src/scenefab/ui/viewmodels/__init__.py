#!/usr/bin/env python3
"""ViewModel base class.

ViewModels bridge services (non-Qt) and views (QWidget) by:

1. Holding the application-facing state the view binds to.
2. Exposing that state as Qt Properties + Signals so views can react
   declaratively via ``propertyChanged`` connections or direct
   ``setProperty`` rebinds.
3. Subscribing to service-layer signals and re-emitting as ViewModel
   changes.

Convention for derived ViewModels:
- One Python attribute per bound value, named in ``snake_case``.
- A corresponding ``<name>_changed = Signal()`` for each attribute.
- A Qt ``Property`` wrapper of the same name returning the attribute
  and emitting the change signal on ``setter`` calls.

This file deliberately avoids importing ``scenefab.application`` to keep
the base reusable in tests without a live Application.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

from scenefab.project_manager import Project, ProjectManager

if TYPE_CHECKING:
    from scenefab.application import Application


class ViewModelBase(QObject):
    """Thin Qt-aware wrapper that owns state + change signals.

    Subclasses should ``super().__init__(parent)`` and then call
    :py:meth:`bind` to subscribe to service signals.
    """

    def __init__(self, application: Application | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._application = application
        self._pm_connections: dict[str, object] | None = None

    @property
    def application(self) -> Application | None:
        return self._application

    def bind(self) -> None:
        """Subscribe to service signals. Idempotent: safe to call once
        per VM lifetime. Override in subclasses."""

    def unbind(self) -> None:
        """Unsubscribe from service signals. Called when the VM is
        destroyed or the page is popped. Default impl is a no-op."""

    # ── 内部辅助（ProjectManager/CurrentProject 共享给 assets/home viewmodel）──
    def _project_manager(self) -> ProjectManager | None:
        """获取全局 ProjectManager service（无 app/服务时返回 None）"""
        app = self._application
        if app is None:
            return None
        return app.get_service(ProjectManager)

    def _current_project(self) -> Project | None:
        """获取当前打开的项目（无 pm 或未打开项目时返回 None）"""
        pm = self._project_manager()
        if pm is None:
            return None
        return pm.get_current_project()

    def _unbind_pm_signals(
        self,
        handlers: dict[str, object],
    ) -> bool:
        """Disconnect ``handlers`` (mapping of signal-name → bound callable) from the
        current :class:`ProjectManager`, tolerating signals that were never connected.

        Used by subclasses' :py:meth:`unbind` overrides to keep the
        disconnect boilerplate in one place. Returns ``True`` if a project
        manager was available, ``False`` otherwise.
        """
        pm = self._project_manager()
        if pm is None:
            return False
        for signal_name, handler in handlers.items():
            signal = getattr(pm, signal_name, None)
            if signal is None:
                continue
            try:
                signal.disconnect(handler)  # type: ignore[arg-type]
            except (RuntimeError, TypeError):
                # Signal was never connected (no project_manager at bind time)
                pass
        return True

    def _bind_pm_signals(self, connections: dict[str, object]) -> bool:
        """Connect ``connections`` (signal-name → handler) to the current
        :class:`ProjectManager`, returning ``True`` on success."""
        pm = self._project_manager()
        if pm is None:
            return False
        self._pm_connections = dict(connections)
        for signal_name, handler in connections.items():
            signal = getattr(pm, signal_name, None)
            if signal is None:
                continue
            try:
                signal.connect(handler)  # type: ignore[arg-type]
            except (RuntimeError, TypeError):
                pass
        return True

    def _connect_and_seed(
        self,
        connections: dict[str, object],
        *,
        initial_project_opened: str = "",
        initial_recent: list | None = None,
    ) -> bool:
        """Bind project-manager signals and optionally seed initial state.

        ``initial_project_opened`` is emitted once to refresh page state;
        ``initial_recent`` is passed to the ``recent_projects_updated``
        handler if provided.
        """
        if not self._bind_pm_signals(connections):
            return False
        if initial_project_opened:
            opened_handler = connections.get("project_opened")
            if callable(opened_handler):
                opened_handler(initial_project_opened)
        if initial_recent is not None:
            recent_handler = connections.get("recent_projects_updated")
            if callable(recent_handler):
                recent_handler(initial_recent)
        self._bound = True
        return True


__all__ = ["ViewModelBase"]
