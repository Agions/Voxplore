"""pytest configuration - skip PySide6 GUI tests when display is not available."""

_PYSIDE6_GUI_TESTS = [
    "tests/test_project_manager.py",
    "tests/test_project_settings_manager.py",
    "tests/test_project_template_manager.py",
    # test_ui_module_smoke.py imports PySide6.QtWidgets which loads libEGL.
    # On GitHub Actions ubuntu-latest runners without X11/EGL system libs,
    # the import fails with `libEGL.so.1: cannot open shared object file`.
    # The test is still valuable locally (offscreen platform works fine on
    # PySide6 6.11+), so we just skip in headless CI.
    "tests/test_ui_module_smoke.py",
]

# Skip PySide6 GUI tests when PySide6 is not available
try:
    from PySide6 import QtCore  # noqa: F401
except ImportError:
    collect_ignore = _PYSIDE6_GUI_TESTS
