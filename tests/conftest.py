"""Shared pytest fixtures and configuration."""

from unittest.mock import patch
import pytest

# ── PySide6 GUI 测试跳过 ──────────────────────────────────────
_PYSIDE6_GUI_TESTS = [
    "tests/test_project_manager.py",
    "tests/test_settings_mgr.py",
    "tests/test_template_mgr.py",
]

try:
    from PySide6 import QtCore  # noqa: F401
except ImportError:
    collect_ignore = _PYSIDE6_GUI_TESTS

# ── FFmpeg mock ───────────────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_ffmpeg_check():
    with patch("scenefab.services.video.ffmpeg_tool.FFmpegTool.check_ffmpeg"):
        yield


@pytest.fixture
def anyio_backend():
    return "asyncio"
