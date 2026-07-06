"""Helpers for PEP 562-style ``__getattr__`` lazy imports.

Several package ``__init__`` modules expose a single ``__getattr__(name)``
that looks ``name`` up in a dict and lazily imports it from a sub-module
on first access. That body is identical across packages — only the
mapping differs.

:func:`make_lazy_getattr` builds a closure suitable for binding as a
module's ``__getattr__``. Each successful lookup caches the resolved
attribute on the calling module's ``globals()`` to avoid re-import.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Any


def make_lazy_getattr(
    exports: dict[str, str],
    package_name: str,
) -> Callable[[str], Any]:
    """Return a module-level ``__getattr__`` built from an export map.

    Args:
        exports: mapping of attribute name to its sub-module. Relative
            module paths (those starting with ``"."``) are resolved against
            ``package_name``. Absolute paths are imported as-is.
        package_name: the dotted name of the package that owns this lazy
            loader. Used both for resolving relative paths and for
            ``AttributeError`` messages.

    The returned function caches each successful lookup on the calling
    module's globals (PEP 562). It is meant to be assigned to a package's
    module-level ``__getattr__`` name.

    Example::

        # scenefab/services/ai/__init__.py
        _EXPORTS = {"LLMRequest": ".base_llm_provider"}
        __getattr__ = make_lazy_getattr(_EXPORTS, package_name=__name__)
    """

    def _lazy_getattr(name: str) -> Any:
        module_path = exports.get(name)
        if module_path is None:
            raise AttributeError(
                f"module {package_name!r} has no attribute {name!r}"
            )
        if module_path.startswith("."):
            module_path = f"{package_name}{module_path}"
        module = import_module(module_path)
        value = getattr(module, name)
        # Cache on the calling module's globals so subsequent attribute
        # accesses skip the import machinery.
        import sys

        caller_globals = sys.modules[package_name].__dict__
        caller_globals[name] = value
        return value

    return _lazy_getattr


__all__ = ["make_lazy_getattr"]
