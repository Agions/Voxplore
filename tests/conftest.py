"""Shared pytest fixtures and configuration"""
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_ffmpeg_check():
    """Auto-mock FFmpeg availability check in all tests.
    
    CI environments lack FFmpeg, but tests only verify initialization
    and configuration — they don't need real FFmpeg binary.
    """
    with patch("app.services.video_tools.ffmpeg_tool.FFmpegTool.check_ffmpeg"):
        yield
