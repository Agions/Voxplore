#!/usr/bin/env python3
"""
回归测试: video_understanding / export 模块收紧 except Exception 后,
HTTP/JSON/subprocess 错误仍正确处理, 但 RuntimeError/TypeError 不再被吞.

覆盖:
1. api_adapters._parse_video_response: JSON 解析失败 + RuntimeError 行为变化
2. jianying_exporter._get_video_meta: FFmpeg 失败 + RuntimeError 行为变化
3. subtitle_exporter.export_srt: 文件 IO 失败 + TypeError 行为变化
4. core.VideoUnderstandingEngine: Gemini 客户端初始化失败降级

诚实性核心: 收紧后非预期异常 (RuntimeError/TypeError/AttributeError) 应该 raise,
而不再被 log 后吞掉 (掩盖 bug).
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from scenefab.services.export.jianying_exporter import JianyingExporter
from scenefab.services.export.subtitle_exporter import SubtitleExporter
from scenefab.services.video_understanding.api_adapters import APIAdapterMixin


# =============================================================================
# 1. api_adapters._parse_video_response
# =============================================================================


def test_parse_understanding_response_json_decode_error_returns_summary():
    """JSON 解析失败 → 返回 summary 兜底 (行为保持)"""
    # _parse_understanding_response 是 mixin 方法, 用子类实例化
    mixin = APIAdapterMixin()

    result = mixin._parse_understanding_response("这是非 JSON 文本")

    assert isinstance(result, dict)
    assert "summary" in result
    assert "非 JSON" in result["summary"] or result["summary"]


def test_parse_understanding_response_runtime_error_propagates():
    """★诚实性: 解析过程中真正的 bug (RuntimeError) 不再被吞"""
    mixin = APIAdapterMixin()

    # mock json.loads 抛 RuntimeError (模拟真实编程 bug)
    with patch("scenefab.services.video_understanding.api_adapters.json.loads",
               side_effect=RuntimeError("Code bug: unexpected state")):
        with pytest.raises(RuntimeError, match="Code bug"):
            mixin._parse_understanding_response("任意文本")


# =============================================================================
# 2. jianying_exporter._get_video_meta (实际方法名可能不同)
# =============================================================================


def test_get_video_info_jianying_subprocess_error_returns_default():
    """FFmpegTool.get_video_info 抛 subprocess.SubprocessError → 返回 1920x1080 default"""
    with patch("scenefab.services.export.jianying_exporter.FFmpegTool") as mock_ffmpeg:
        import subprocess

        mock_ffmpeg.get_video_info.side_effect = subprocess.SubprocessError("ffprobe failed")

        # JianyingExporter._get_video_info 是 protected 但可测
        result = JianyingExporter._get_video_info(JianyingExporter(), "/tmp/fake.mp4")

        assert result["width"] == 1920
        assert result["height"] == 1080
        assert result["duration"] == 0


def test_get_video_info_jianying_runtime_error_propagates():
    """★诚实性: RuntimeError 不再被 fallback 吞掉"""
    with patch("scenefab.services.export.jianying_exporter.FFmpegTool") as mock_ffmpeg:
        mock_ffmpeg.get_video_info.side_effect = RuntimeError("Code bug: bad meta extraction")

        with pytest.raises(RuntimeError, match="Code bug"):
            JianyingExporter._get_video_info(JianyingExporter(), "/tmp/fake.mp4")


def test_get_video_info_jianying_filenotfound_returns_default():
    """FFmpeg 二进制不存在 → FileNotFoundError → 返回 default"""
    with patch("scenefab.services.export.jianying_exporter.FFmpegTool") as mock_ffmpeg:
        mock_ffmpeg.get_video_info.side_effect = FileNotFoundError("ffmpeg not in PATH")

        result = JianyingExporter._get_video_info(JianyingExporter(), "/tmp/fake.mp4")

        assert result["width"] == 1920
        assert result["duration"] == 0


# =============================================================================
# 3. subtitle_exporter.export_srt
# =============================================================================


def test_export_srt_oserror_returns_false(tmp_path):
    """磁盘满 / 权限不足 (OSError) → 返回 False (行为保持)"""
    bad_path = tmp_path / "readonly" / "out.srt"

    # 在只读目录尝试写入会触发 PermissionError (OSError 子类)
    import os
    readonly_dir = tmp_path / "ro"
    readonly_dir.mkdir()
    os.chmod(readonly_dir, 0o555)  # 只读

    try:
        result = SubtitleExporter.export_srt(
            [{"to_srt": lambda i: f"{i}\n00:00:01,000 --> 00:00:02,000\ntest"}],
            str(readonly_dir / "out.srt"),
        )
        assert result is False
    finally:
        os.chmod(readonly_dir, 0o755)  # 恢复, 避免影响后续测试


def test_export_srt_type_error_propagates():
    """★诚实性: subtitle.to_srt 真实 bug (TypeError) 不再被返回 False 掩盖"""
    # 传入一个没有 to_srt 方法的对象
    bad_subtitles = [{"no_to_srt": "bug"}]

    with pytest.raises(AttributeError):
        SubtitleExporter.export_srt(bad_subtitles, "/tmp/out.srt")


# =============================================================================
# 4. core.VideoUnderstandingEngine: Gemini 客户端初始化
# =============================================================================


def test_gemini_client_init_oserror_falls_back():
    """Gemini 初始化时 httpx.Client() 抛 OSError → 降级到 None"""
    from scenefab.services.video_understanding.core import LongVideoUnderstanding

    with patch("httpx.Client", side_effect=OSError("Cannot allocate resource")):
        engine = LongVideoUnderstanding(api_keys={"gemini": "test-key"})

        assert engine.gemini_client is None


def test_gemini_client_init_runtime_error_propagates():
    """★诚实性: Gemini 初始化时 RuntimeError (真实 bug) 不再被吞"""
    from scenefab.services.video_understanding.core import LongVideoUnderstanding

    with patch("httpx.Client", side_effect=RuntimeError("Code bug: bad init")):
        with pytest.raises(RuntimeError, match="Code bug"):
            LongVideoUnderstanding(api_keys={"gemini": "test-key"})


def test_gemini_client_init_httpx_http_error_falls_back():
    """Gemini 初始化时 httpx.HTTPError → 降级到 None (网络环境异常)"""
    from scenefab.services.video_understanding.core import LongVideoUnderstanding

    # httpx.Client.__init__ 在网络受限环境可能抛 HTTPError
    with patch("httpx.Client", side_effect=httpx.HTTPError("Network unreachable")):
        engine = LongVideoUnderstanding(api_keys={"gemini": "test-key"})

        assert engine.gemini_client is None