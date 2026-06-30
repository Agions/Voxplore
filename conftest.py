"""pytest configuration - skip PySide6 GUI tests when display is not available."""

import ctypes.util

_PYSIDE6_GUI_TESTS = [
    "tests/test_project_manager.py",
    "tests/test_project_settings_manager.py",
    "tests/test_project_template_manager.py",
    # Tests below import PySide6.QtWidgets which loads libEGL. On GitHub
    # Actions ubuntu-latest runners without X11/EGL system libs the import
    # fails with `libEGL.so.1: cannot open shared object file`. The tests
    # are still valuable locally (offscreen platform works fine on PySide6
    # 6.11+), so we skip in headless CI.
    "tests/test_ui_module_smoke.py",
    "tests/test_home_viewmodel.py",
]


def _has_egl_lib() -> bool:
    """Return True if libEGL.so.1 (or platform equivalent) is loadable.

    PySide6.QtWidgets' offscreen platform on Linux links against libEGL at
    import time. If libEGL isn't installed (typical GitHub Actions runner),
    the import raises ImportError / OSError.
    """
    for name in ("libEGL.so.1", "libEGL.so"):
        if ctypes.util.find_library(name.replace(".so", "").replace("lib", "")):
            return True
        try:
            ctypes.CDLL(name)
            return True
        except OSError:
            continue
    return False


# Skip PySide6 GUI tests when PySide6 is not available, OR when libEGL is
# missing (headless CI runners without X11/EGL system libs).
pyside6_available = True
try:
    from PySide6 import QtCore  # noqa: F401
except ImportError:
    pyside6_available = False

if not pyside6_available or not _has_egl_lib():
    collect_ignore = _PYSIDE6_GUI_TESTS
