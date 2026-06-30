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

    @property
    def application(self) -> Application | None:
        return self._application

    def bind(self) -> None:
        """Subscribe to service signals. Idempotent: safe to call once
        per VM lifetime. Override in subclasses."""

    def unbind(self) -> None:
        """Unsubscribe from service signals. Called when the VM is
        destroyed or the page is popped. Default impl is a no-op."""


__all__ = ["ViewModelBase"]
