"""pytest configuration - skip PySide6 GUI tests when display is not available."""
from pathlib import Path

_PYSIDE6_GUI_TESTS = [
    "tests/test_project_manager.py",
    "tests/test_application.py",
    "tests/test_ui_components.py",
    "tests/test_page_loader.py",
    "tests/test_project_settings_manager.py",
    "tests/test_project_version_manager.py",
    "tests/test_icon_manager.py",
    "tests/test_project_template_manager.py",
]

# Skip PySide6 GUI tests when PySide6 is not available
try:
    from PySide6 import QtCore  # noqa: F401
except ImportError:
    collect_ignore = _PYSIDE6_GUI_TESTS
