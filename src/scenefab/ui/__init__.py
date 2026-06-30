"""
SceneFab UI 模块

提供 PySide6 图形界面组件

Note (Phase 4 P1 refactor): SceneFabMainWindow is **not** re-exported
from this package's ``__init__``. Importing the package used to drag
in ``scenefab.ui.main.main_window`` which transitively imports
PySide6.QtWidgets — that chain blew up headless CI environments
without libEGL. Consumers should use the explicit submodule path:

    from scenefab.ui.main.main_window import SceneFabMainWindow
"""
