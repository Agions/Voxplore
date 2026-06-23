"""pytest configuration - skip PySide6 GUI tests when display is not available."""

_PYSIDE6_GUI_TESTS = [
    "tests/test_project_manager.py",
    "tests/test_project_settings_manager.py",
    "tests/test_project_version_manager.py",
    "tests/test_project_template_manager.py",
]

# Skip PySide6 GUI tests when PySide6 is not available
try:
    from PySide6 import QtCore  # noqa: F401
except ImportError:
    collect_ignore = _PYSIDE6_GUI_TESTS
