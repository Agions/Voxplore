#!/usr/bin/env python3
"""Test Video Exporter"""


from app.services.export.video_exporter import (
    ExportFormat,
    VideoCodec,
    AudioCodec,
    ExportConfig,
    VideoExporter,
)


class TestExportFormat:
    """Test export format enum"""

    def test_all_formats(self):
        """Test all formats"""
        formats = [
            ExportFormat.MP4,
            ExportFormat.MOV,
            ExportFormat.WEBM,
            ExportFormat.GIF,
        ]
        
        assert len(formats) == 4
        assert ExportFormat.MP4.value == "mp4"


class TestVideoCodec:
    """Test video codec enum"""

    def test_all_codecs(self):
        """Test all codecs"""
        codecs = [
            VideoCodec.H264,
            VideoCodec.H265,
            VideoCodec.VP9,
            VideoCodec.PRORES,
        ]
        
        assert len(codecs) == 4
        assert VideoCodec.H264.value == "libx264"


class TestAudioCodec:
    """Test audio codec enum"""

    def test_all_codecs(self):
        """Test all codecs"""
        codecs = [
            AudioCodec.AAC,
            AudioCodec.MP3,
            AudioCodec.OPUS,
        ]
        
        assert len(codecs) == 3
        assert AudioCodec.AAC.value == "aac"


class TestExportConfig:
    """Test export config"""

    def test_default_config(self):
        """Test default config"""
        config = ExportConfig()
        
        assert config.format == ExportFormat.MP4
        assert config.video_codec == VideoCodec.H264
        assert config.width == 1080
        assert config.height == 1920

    def test_custom_config(self):
        """Test custom config"""
        config = ExportConfig(
            format=ExportFormat.WEBM,
            width=1920,
            height=1080,
        )
        
        assert config.format == ExportFormat.WEBM
        assert config.width == 1920
        assert config.height == 1080


class TestVideoExporter:
    """Test video exporter"""

    def test_init(self):
        """Test initialization"""
        exporter = VideoExporter()
        
        assert exporter.config is not None
        assert isinstance(exporter.config, ExportConfig)

    def test_init_custom_config(self):
        """Test custom config initialization"""
        config = ExportConfig(format=ExportFormat.MOV)
        exporter = VideoExporter(config)
        
        assert exporter.config.format == ExportFormat.MOV
