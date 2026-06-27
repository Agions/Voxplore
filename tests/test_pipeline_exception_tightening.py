#!/usr/bin/env python3
"""
回归测试: pipeline/assembly_steps + pipeline/understanding_steps 收紧 except Exception 后,
FFmpeg / wave / 文件 IO / scene Bridge 构造错误仍正确处理,
但 RuntimeError/TypeError (除合理情况) 不再被吞.

诚实性核心: 收紧后非预期异常 (RuntimeError 等真实编程 bug) 应该 raise,
而不再被 log/continue 后吞掉 (掩盖 bug).
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# 1. assembly_steps.py:71 — probe_audio_duration FFmpeg fallback
# =============================================================================


def test_probe_audio_duration_ffmpeg_subprocess_error_falls_through(tmp_path):
    """FFmpegTool.get_duration subprocess 失败 → 继续到下一阶段 (16kbps 估算)"""
    from scenefab.pipeline.assembly_steps import probe_audio_duration

    # 创建一个 fake 音频文件 (不是 WAV)
    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"x" * 2048)  # 2KB

    # Mock FFmpegTool.get_duration 抛 SubprocessError
    with patch("scenefab.services.video_tools.ffmpeg_tool.FFmpegTool.get_duration",
               side_effect=subprocess.SubprocessError("ffprobe failed")):
        result = probe_audio_duration(audio_path)
        # 走 fallback (文件大小估算): size_bytes / 2048.0
        assert result == pytest.approx(1.0, abs=0.01)


def test_probe_audio_duration_filenotfound_falls_through(tmp_path):
    """FFmpegTool.get_duration 抛 FileNotFoundError (FFmpeg 未装) → fallback"""
    from scenefab.pipeline.assembly_steps import probe_audio_duration

    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"x" * 4096)  # 4KB

    with patch("scenefab.services.video_tools.ffmpeg_tool.FFmpegTool.get_duration",
               side_effect=FileNotFoundError("ffmpeg not in PATH")):
        result = probe_audio_duration(audio_path)
        assert result == pytest.approx(2.0, abs=0.01)


def test_probe_audio_duration_runtime_error_propagates(tmp_path):
    """★诚实性: FFmpegTool.get_duration 中 RuntimeError 不再被吞"""
    from scenefab.pipeline.assembly_steps import probe_audio_duration

    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"x" * 100)

    with patch("scenefab.services.video_tools.ffmpeg_tool.FFmpegTool.get_duration",
               side_effect=RuntimeError("Code bug: bad ffprobe logic")):
        with pytest.raises(RuntimeError, match="Code bug"):
            probe_audio_duration(audio_path)


# =============================================================================
# 2. assembly_steps.py:299 — _tts_stub wave.open 写文件
# =============================================================================


def test_tts_stub_wave_oserror_returns_failure():
    """_tts_stub 写 WAV 失败 (OSError) → return failure StepResult"""
    from scenefab.pipeline.assembly_steps import _tts_stub
    from scenefab.pipeline.narration_context import NarrationContext
    from scenefab.pipeline.narration_state_machine import NarrationState

    ctx = MagicMock(spec=NarrationContext)
    ctx.trace_id = "trace-abc-12345"
    ctx.current_draft = "测试文本"

    with patch("wave.open", side_effect=OSError("Permission denied")):
        result = _tts_stub(ctx, Path("/tmp/test.wav"), start=0.0)

    assert result.success is False
    assert result.state == NarrationState.TTS
    assert result.error is not None
    assert "stub TTS 写文件失败" in result.error
    assert "Permission denied" in result.error


def test_tts_stub_wave_type_error_propagates():
    """★诚实性: wave.open 中 TypeError (e.g. 参数错) 不再被返回 failure 掩盖"""
    from scenefab.pipeline.assembly_steps import _tts_stub
    from scenefab.pipeline.narration_context import NarrationContext

    ctx = MagicMock(spec=NarrationContext)
    ctx.trace_id = "trace-abc-12345"
    ctx.current_draft = "测试文本"

    with patch("wave.open", side_effect=TypeError("Code bug: bad wave params")):
        with pytest.raises(TypeError, match="Code bug"):
            _tts_stub(ctx, Path("/tmp/test.wav"), start=0.0)


# =============================================================================
# 3. assembly_steps.py:380 — _write_jianying_metadata 文件 IO
# =============================================================================


def test_jianying_metadata_runtime_error_propagates(tmp_path):
    """★诚实性: _write_jianying_metadata 中 RuntimeError 不再被吞"""
    from scenefab.pipeline.assembly_steps import _write_jianying_metadata
    from scenefab.pipeline.narration_context import NarrationContext

    ctx = MagicMock(spec=NarrationContext)
    ctx.trace_id = "trace-jy"

    # 让 json.dumps 抛 RuntimeError (模拟真实编程 bug, 如循环引用)
    with patch("json.dumps", side_effect=RuntimeError("Code bug: circular reference")):
        with pytest.raises(RuntimeError, match="Code bug"):
            _write_jianying_metadata(ctx, tmp_path / "test.json")


def test_jianying_metadata_oserror_logs_warning(tmp_path):
    """_write_jianying_metadata 抛 OSError → 上层 catch (行为保持)"""
    from scenefab.pipeline.assembly_steps import _write_jianying_metadata

    # 让 json.dumps 抛 OSError (绕过 ctx 字段 mock 难题)
    with patch("json.dumps", side_effect=OSError("Disk full")):
        with pytest.raises(OSError):
            # ctx 可以是 None 或 MagicMock, json.dumps 先抛 OSError
            _write_jianying_metadata(MagicMock(), tmp_path / "test.json")


# =============================================================================
# 4. assembly_steps.py:387 — _write_placeholder_video 文件 IO
# =============================================================================


def test_placeholder_video_runtime_error_propagates(tmp_path):
    """★诚实性: _write_placeholder_video 中 RuntimeError 不再被吞"""
    from scenefab.pipeline.assembly_steps import _write_placeholder_video
    from scenefab.pipeline.narration_context import NarrationContext

    ctx = MagicMock(spec=NarrationContext)
    ctx.trace_id = "trace-placeholder"

    # 让 json.dumps 抛 RuntimeError
    with patch("json.dumps", side_effect=RuntimeError("Code bug: bad serialization")):
        with pytest.raises(RuntimeError, match="Code bug"):
            _write_placeholder_video(tmp_path / "video.mp4", ctx)


# =============================================================================
# 5. understanding_steps.py:519 — _detect_bridges 循环
# =============================================================================


def test_detect_bridges_scene_attribute_error_continues():
    """_detect_bridges 单 scene AttributeError → continue, 不影响其他 scene"""
    from scenefab.core.short_drama import TropeType
    from scenefab.pipeline.understanding_steps import _detect_bridges

    narrator = MagicMock()

    # 构造 3 个 scene, 第 2 个有问题
    good_scene1 = MagicMock(description="主角霸气登场", index=0)
    bad_scene = MagicMock()
    bad_scene.description = MagicMock(side_effect=AttributeError("Code bug"))
    bad_scene.index = 1
    good_scene2 = MagicMock(description="第3集结尾", index=2)

    narrator.detect_trope.side_effect = lambda desc: (
        TropeType.IDENTITY_REVEAL if "霸气" in desc else TropeType.GENERAL
    )

    bridges = _detect_bridges(narrator, [good_scene1, bad_scene, good_scene2])

    # 第 1 个和第 3 个应该成功, 第 2 个被 skip
    # good_scene1 命中 IDENTITY_REVEAL, good_scene2 返回 GENERAL (value == "general" 不命中)
    assert len(bridges) == 1
    assert bridges[0].scene_index == 0


def test_detect_bridges_runtime_error_propagates():
    """★诚实性: _detect_bridges 中 RuntimeError 不再被吞 (e.g. narrator 真 bug)"""
    from scenefab.pipeline.understanding_steps import _detect_bridges

    narrator = MagicMock()
    narrator.detect_trope.side_effect = RuntimeError("Code bug: LLM adapter crashed")

    scene = MagicMock(description="test", index=0)

    with pytest.raises(RuntimeError, match="Code bug"):
        _detect_bridges(narrator, [scene])


def test_detect_bridges_empty_description_skipped():
    """scene.description 为空 → skip (行为保持)"""
    from scenefab.core.short_drama import TropeType
    from scenefab.pipeline.understanding_steps import _detect_bridges

    narrator = MagicMock()
    narrator.detect_trope.return_value = TropeType.IDENTITY_REVEAL

    scene_empty = MagicMock(description="", index=0)
    scene_valid = MagicMock(description="测试", index=1)

    bridges = _detect_bridges(narrator, [scene_empty, scene_valid])

    # 空描述被 skip, 有效描述命中
    assert len(bridges) == 1
    assert bridges[0].scene_index == 1
    # detect_trope 不应被空描述调用
    assert narrator.detect_trope.call_count == 1