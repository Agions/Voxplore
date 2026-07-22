#!/usr/bin/env python3
"""Test Direct Video Exporter"""

from scenefab.services.export.video_exporter import (
    AudioCodec,
    DirectVideoExporter,
    HWAccel,
    Resolution,
    VideoCodec,
    VideoExportConfig,
    VideoFormat,
    build_burn_subtitles_command,
    build_concat_command,
    build_extract_segment_command,
    build_merge_audio_command,
    build_scale_pad_filter,
    resolve_video_codec,
    with_hw_accel_params,
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


class TestFfmpegCommandHelpers:
    """Test pure FFmpeg command helpers"""

    def test_build_scale_pad_filter(self):
        assert build_scale_pad_filter(Resolution.VERTICAL_1080P) == (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
        )

    def test_with_hw_accel_params_does_not_mutate_input(self):
        config = VideoExportConfig(hw_accel=HWAccel.APPLE)
        cmd = ["ffmpeg", "-y", "-i", "input.mp4"]

        result = with_hw_accel_params(cmd, config)

        assert result == [
            "ffmpeg",
            "-hwaccel",
            "videotoolbox",
            "-y",
            "-i",
            "input.mp4",
        ]
        assert cmd == ["ffmpeg", "-y", "-i", "input.mp4"]

    def test_resolve_video_codec_uses_hw_encoder(self):
        config = VideoExportConfig(hw_accel=HWAccel.APPLE, video_codec=VideoCodec.H265)

        assert resolve_video_codec(config) == "hevc_videotoolbox"

    def test_build_extract_segment_command(self):
        config = VideoExportConfig(resolution=Resolution.HD_720P, hw_accel=HWAccel.NONE)

        cmd = build_extract_segment_command(
            "input.mp4",
            1.5,
            3.0,
            "out.mp4",
            config,
        )

        assert cmd[:8] == ["ffmpeg", "-y", "-ss", "1.5", "-t", "3.0", "-i", "input.mp4"]
        assert build_scale_pad_filter(Resolution.HD_720P) in cmd
        assert cmd[cmd.index("-c:v") + 1] == "libx264"
        assert cmd[-1] == "out.mp4"

    def test_build_merge_audio_command(self):
        config = VideoExportConfig(audio_codec=AudioCodec.AAC)

        cmd = build_merge_audio_command("video.mp4", "voice.wav", "out.mp4", config)

        assert cmd == [
            "ffmpeg",
            "-y",
            "-i",
            "video.mp4",
            "-i",
            "voice.wav",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "out.mp4",
        ]

    def test_build_concat_command(self, tmp_path):
        list_file = tmp_path / "concat.txt"

        cmd = build_concat_command(list_file, "merged.mp4")

        assert cmd == [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            "merged.mp4",
        ]

    def test_build_burn_subtitles_command(self):
        config = VideoExportConfig(crf=20, preset="slow")

        cmd = build_burn_subtitles_command(
            "video.mp4",
            "subtitles.srt",
            "out.mp4",
            config,
        )

        assert (
            cmd[cmd.index("-vf") + 1]
            == "subtitles=subtitles.srt:force_style=FontSize=24"
        )
        assert cmd[cmd.index("-preset") + 1] == "slow"
        assert cmd[cmd.index("-crf") + 1] == "20"


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

    def test_progress_callback_is_optional(self):
        """Progress reporting should be a no-op until a callback is set."""
        exporter = DirectVideoExporter()

        exporter._report_progress("准备导出", 0.1)
