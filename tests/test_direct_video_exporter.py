#!/usr/bin/env python3
"""Test Direct Video Exporter"""

import pytest
from dataclasses import asdict

from app.services.export.direct_video_exporter import (
    Resolution,
    VideoCodec,
    VideoFormat,
    HWAccel,
    VideoExportConfig,
    DirectVideoExporter,
)


class TestResolution:
    """Test resolution enum"""

    def test_landscape_resolutions(self):
        """Test landscape resolutions"""
        assert Resolution.FHD_1080P.width == 1920
        assert Resolution.FHD_1080P.height == 1080
        assert Resolution.UHD_4K.width == 3840
        assert Resolution.UHD_4K.height == 2160

    def test_vertical_resolutions(self):
        """Test vertical resolutions"""
        assert Resolution.VERTICAL_1080P.width == 1080
        assert Resolution.VERTICAL_1080P.height == 1920

    def test_square_resolutions(self):
        """Test square resolutions"""
        assert Resolution.SQUARE_1080.width == 1080
        assert Resolution.SQUARE_1080.height == 1080


class TestVideoCodec:
    """Test video codec enum"""

    def test_codecs(self):
        """Test video codecs"""
        assert VideoCodec.H264.value == "libx264"
        assert VideoCodec.H265.value == "libx265"


class TestVideoFormat:
    """Test video format enum"""

    def test_formats(self):
        """Test video formats"""
        assert VideoFormat.MP4.value == "mp4"
        assert VideoFormat.WEBM.value == "webm"


class TestHWAccel:
    """Test hardware acceleration enum"""

    def test_hw_accels(self):
        """Test hardware accelerations"""
        assert HWAccel.NONE.value == "none"
        assert HWAccel.APPLE.value == "videotoolbox"
        assert HWAccel.NVIDIA.value == "nvenc"


class TestVideoExportConfig:
    """Test video export config"""

    def test_default_config(self):
        """Test default config"""
        config = VideoExportConfig()
        
        assert config.resolution == Resolution.FHD_1080P
        assert config.format == VideoFormat.MP4
        assert config.fps == 30.0

    def test_custom_config(self):
        """Test custom config"""
        config = VideoExportConfig(
            resolution=Resolution.VERTICAL_1080P,
            fps=60.0,
        )
        
        assert config.resolution == Resolution.VERTICAL_1080P
        assert config.fps == 60.0


class TestDirectVideoExporter:
    """Test direct video exporter"""

    def test_init(self):
        """Test initialization"""
        exporter = DirectVideoExporter()
        
        assert exporter.config is not None
        assert isinstance(exporter.config, VideoExportConfig)

    def test_init_custom_config(self):
        """Test custom config initialization"""
        config = VideoExportConfig(resolution=Resolution.UHD_4K)
        exporter = DirectVideoExporter(config)
        
        assert exporter.config.resolution == Resolution.UHD_4K
