#!/usr/bin/env python3
"""测试 FFmpeg 工具"""

import os
import tempfile
from unittest.mock import Mock, patch

from scenefab.services.video_tools.ffmpeg_tool import FFmpegTool
from scenefab.utils.security import SecurityError


class TestFFmpegToolBasic:
    """测试 FFmpeg 基础方法"""

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_get_duration_success(self, mock_run):
        """测试获取视频时长成功"""
        mock_run.return_value = Mock(
            stdout='{"format": {"duration": "120.5"}}', returncode=0
        )

        duration = FFmpegTool.get_duration("/test/video.mp4")

        assert duration == 120.5

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_get_duration_error(self, mock_run):
        """测试获取视频时长失败"""
        mock_run.side_effect = SecurityError(
            "Command 'ffprobe' returned non-zero exit status 1."
        )

        duration = FFmpegTool.get_duration("/test/video.mp4")

        assert duration == 0.0

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_get_resolution_success(self, mock_run):
        """测试获取分辨率成功"""
        mock_run.return_value = Mock(
            stdout='{"streams": [{"codec_type": "video", "width": 1920, "height": 1080}]}',
            returncode=0,
        )

        width, height = FFmpegTool.get_resolution("/test/video.mp4")

        assert width == 1920
        assert height == 1080

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_get_resolution_no_video_stream(self, mock_run):
        """测试无视频流时返回默认值"""
        mock_run.return_value = Mock(
            stdout='{"streams": [{"codec_type": "audio"}]}', returncode=0
        )

        width, height = FFmpegTool.get_resolution("/test/video.mp4")

        assert width == 1920
        assert height == 1080

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_get_framerate_success(self, mock_run):
        """测试获取帧率成功"""
        mock_run.return_value = Mock(
            stdout='{"streams": [{"r_frame_rate": "30000/1001"}]}', returncode=0
        )

        fps = FFmpegTool.get_framerate("/test/video.mp4")

        assert abs(fps - 29.97) < 0.1

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_get_framerate_integer(self, mock_run):
        """测试获取整数帧率"""
        mock_run.return_value = Mock(
            stdout='{"streams": [{"r_frame_rate": "60/1"}]}', returncode=0
        )

        fps = FFmpegTool.get_framerate("/test/video.mp4")

        assert fps == 60.0

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_get_bitrate_success(self, mock_run):
        """测试获取码率成功"""
        mock_run.return_value = Mock(
            stdout='{"format": {"bit_rate": "5000000"}}', returncode=0
        )

        bitrate = FFmpegTool.get_bitrate("/test/video.mp4")

        assert bitrate == 5000000

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_get_video_info_success(self, mock_run):
        """测试获取完整视频信息"""
        mock_run.return_value = Mock(
            stdout='{"format": {"duration": "120"}, "streams": []}', returncode=0
        )

        info = FFmpegTool.get_video_info("/test/video.mp4")

        assert "format" in info
        assert info["format"]["duration"] == "120"


class TestFFmpegToolVideoProcessing:
    """测试视频处理方法"""

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_trim_video_success(self, mock_run):
        """测试裁剪视频成功"""
        mock_run.return_value = Mock(returncode=0)

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            output = f.name

        try:
            result = FFmpegTool.trim_video("/input.mp4", output, start=5.0, end=10.0)
            assert result is True
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "-ss" in args
            assert "5.0" in args
            assert "-to" in args
            assert "10.0" in args
        finally:
            if os.path.exists(output):
                os.unlink(output)

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_trim_video_failure(self, mock_run):
        """测试裁剪视频失败"""
        mock_run.side_effect = SecurityError("ffmpeg error")

        result = FFmpegTool.trim_video("/input.mp4", "/output.mp4", start=0, end=10)

        assert result is False

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_concat_videos_success(self, mock_run):
        """测试拼接视频成功"""
        mock_run.return_value = Mock(returncode=0)

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            output = f.name

        try:
            result = FFmpegTool.concat_videos(["/input1.mp4", "/input2.mp4"], output)
            assert result is True
        finally:
            if os.path.exists(output):
                os.unlink(output)

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_change_speed_success(self, mock_run):
        """测试改变视频速度成功"""
        mock_run.return_value = Mock(returncode=0)

        result = FFmpegTool.change_speed("/input.mp4", "/output.mp4", speed=2.0)

        assert result is True
        args = mock_run.call_args[0][0]
        assert "setpts=0.5*PTS" in " ".join(args)

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_reverse_video_success(self, mock_run):
        """测试倒放视频成功"""
        mock_run.return_value = Mock(returncode=0)

        result = FFmpegTool.reverse_video("/input.mp4", "/output.mp4")

        assert result is True
        args = mock_run.call_args[0][0]
        assert "reverse" in " ".join(args)


class TestFFmpegToolAudioProcessing:
    """测试音频处理方法"""

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_extract_audio_success(self, mock_run):
        """测试提取音频成功"""
        mock_run.return_value = Mock(returncode=0)

        result = FFmpegTool.extract_audio("/input.mp4", "/output.mp3")

        assert result is True
        args = mock_run.call_args[0][0]
        assert "-vn" in args

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_add_audio_success(self, mock_run):
        """测试添加音频成功"""
        mock_run.return_value = Mock(returncode=0)

        result = FFmpegTool.add_audio(
            "/video.mp4", "/audio.mp3", "/output.mp4", mix=True
        )

        assert result is True

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_adjust_volume_success(self, mock_run):
        """测试调整音量成功"""
        mock_run.return_value = Mock(returncode=0)

        result = FFmpegTool.adjust_volume("/input.mp4", "/output.mp4", volume=0.5)

        assert result is True
        args = mock_run.call_args[0][0]
        assert "volume=0.5" in " ".join(args)


class TestFFmpegToolThumbnail:
    """测试缩略图方法"""

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_generate_thumbnail_success(self, mock_run):
        """测试生成缩略图成功"""
        mock_run.return_value = Mock(returncode=0)

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            output = f.name

        try:
            result = FFmpegTool.generate_thumbnail(
                "/input.mp4", output, timestamp=5.0, width=320, height=180
            )
            assert result is True
            args = mock_run.call_args[0][0]
            assert "-ss" in args
            assert "5.0" in args
            assert "-vframes" in args
        finally:
            if os.path.exists(output):
                os.unlink(output)

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_generate_waveform_success(self, mock_run):
        """测试生成波形图成功"""
        mock_run.return_value = Mock(returncode=0)

        result = FFmpegTool.generate_waveform("/audio.mp3", "/output.png")

        assert result is True


class TestFFmpegToolConversion:
    """测试格式转换方法"""

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_convert_format_success(self, mock_run):
        """测试格式转换成功"""
        mock_run.return_value = Mock(returncode=0)

        result = FFmpegTool.convert_format(
            "/input.avi",
            "/output.mp4",
            video_codec="libx264",
            audio_codec="aac",
            use_hw_accel=False,  # 禁用硬件加速以确保使用指定的编码器
        )

        assert result is True
        args = mock_run.call_args[0][0]
        assert "-c:v" in args
        assert "libx264" in args

    @patch("scenefab.utils.security.SecureExecutor.run")
    def test_convert_format_failure(self, mock_run):
        """测试格式转换失败"""
        mock_run.side_effect = SecurityError("ffmpeg error")

        result = FFmpegTool.convert_format("/input.avi", "/output.mp4")

        assert result is False


class TestFFmpegToolIntegration:
    """FFmpegTool 集成测试"""

    def test_all_methods_exist(self):
        """验证所有方法都存在"""
        required_methods = [
            "check_ffmpeg",
            "get_duration",
            "get_resolution",
            "get_framerate",
            "get_bitrate",
            "get_video_info",
            "trim_video",
            "concat_videos",
            "change_speed",
            "reverse_video",
            "extract_audio",
            "add_audio",
            "adjust_volume",
            "generate_thumbnail",
            "generate_waveform",
            "convert_format",
        ]

        for method in required_methods:
            assert hasattr(FFmpegTool, method), f"FFmpegTool.{method} 不存在"
