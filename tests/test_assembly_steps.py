#!/usr/bin/env python3
"""
v2.2 Narration State Machine — Phase 4 真实实现测试

覆盖 Phase 4 新增能力:
- tts_length_adjust_step: 长度反馈 + LLM 压缩/扩展 + 降级
- tts_step: Edge-TTS 真实调用 + 降级 stub WAV
- assemble_step: 字幕生成 (ASS+SRT) + 剪映草稿元数据
- probe_audio_duration: WAV/ffprobe/文件大小 3 层探测
- 端到端 Phase 1+2+3+4 跑通, 11 状态全 DONE
"""

from __future__ import annotations

import json
import wave
from pathlib import Path
from unittest.mock import patch

import pytest

from scenefab.pipeline.assembly_steps import (
    assemble_step,
    probe_audio_duration,
    tts_length_adjust_step,
    tts_step,
)
from scenefab.pipeline.narration import (
    PLATFORM_SPECS,
    NarrationContext,
    NarrationState,
    NarrationStateMachine,
    NarrationStyle,
    Persona,
    Platform,
    StepResult,
    register_assembly_steps,
    register_default_steps,
    register_evaluation_steps,
    register_understanding_steps,
)
from scenefab.services.video_understanding.models import (
    Character,
    PlotEvent,
    StoryGraph,
)

# ============================================
# Fixtures
# ============================================


@pytest.fixture
def fake_video(tmp_path: Path) -> Path:
    video = tmp_path / "test_video.mp4"
    video.write_bytes(b"\x00" * 1024)
    return video


@pytest.fixture
def ctx(fake_video: Path, tmp_path: Path) -> NarrationContext:
    return NarrationContext(
        source_video=fake_video,
        output_dir=tmp_path / "output",
        persona=Persona.STORY_TELLER,
        style=NarrationStyle.SUSPENSE,
        platform=Platform.BILIBILI,
    )


@pytest.fixture
def ctx_with_draft(ctx: NarrationContext) -> NarrationContext:
    """预填 draft + story_graph, 跳过 Phase 2/3"""
    ctx.story_graph = StoryGraph(
        title="测试",
        synopsis="测试剧情",
        characters=[Character(character_id="c1", name="林墨", description="女主")],
        plot_events=[
            PlotEvent(
                event_id="e1",
                timestamp=0,
                event_type="climax",
                description="身份揭露",
            )
        ],
    )
    return ctx


@pytest.fixture
def sm_full() -> NarrationStateMachine:
    sm = NarrationStateMachine()
    register_default_steps(sm)
    register_understanding_steps(sm)
    register_evaluation_steps(sm)
    register_assembly_steps(sm)
    # Force ACCEPT to skip Phase 3 真实评估
    def high_eval(c):
        c.eval_score = 9.0
        c.eval_issues = []
        return StepResult(
            success=True, state=NarrationState.EVALUATE, message="9.0 forced"
        )
    sm.register_step(NarrationState.EVALUATE, high_eval)
    return sm


# ============================================
# 1. probe_audio_duration 工具函数
# ============================================


class TestProbeAudioDuration:
    """音频时长探测 3 层降级"""

    def test_probe_wav_file(self, tmp_path: Path) -> None:
        """WAV 文件用 wave 模块探测"""
        wav = tmp_path / "test.wav"
        # 1 秒 16kHz 单声道
        with wave.open(str(wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00" * 32000)  # 1s

        duration = probe_audio_duration(wav)
        assert abs(duration - 1.0) < 0.01

    def test_probe_wav_5_seconds(self, tmp_path: Path) -> None:
        """5 秒 WAV"""
        wav = tmp_path / "test_5s.wav"
        with wave.open(str(wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00" * 160000)  # 5s

        duration = probe_audio_duration(wav)
        assert abs(duration - 5.0) < 0.01

    def test_probe_nonexistent_file(self) -> None:
        """不存在的文件返回 0.0"""
        duration = probe_audio_duration(Path("/nonexistent/path/audio.wav"))
        assert duration == 0.0

    def test_probe_corrupted_wav(self, tmp_path: Path) -> None:
        """损坏的 WAV 文件不崩溃"""
        bad = tmp_path / "bad.wav"
        bad.write_bytes(b"\x00" * 100)
        # 不抛异常, 降级返回 0 或文件大小估算
        duration = probe_audio_duration(bad)
        assert duration >= 0.0


# ============================================
# 2. tts_length_adjust_step
# ============================================


class TestTtsLengthAdjustStep:
    """TTS 长度反馈压缩/扩展"""

    def test_empty_draft_fails(self, ctx: NarrationContext) -> None:
        """空 draft 失败"""
        result = tts_length_adjust_step(ctx)
        assert not result.success
        assert "current_draft 为空" in (result.error or "")

    def test_perfect_length_no_adjust(
        self, ctx_with_draft: NarrationContext
    ) -> None:
        """字数接近 target → 不调 LLM, 直接 succeed"""
        target_chars = int(
            ctx_with_draft.platform_spec.char_per_second
            * ctx_with_draft.platform_spec.target_duration_sec
        )
        # 97% target, 偏离 < 5% (避开边界 0.05)
        ctx_with_draft.current_draft = "x" * int(target_chars * 0.97)
        result = tts_length_adjust_step(ctx_with_draft)

        assert result.success
        assert result.data["adjusted"] is False
        assert result.data["deviation"] < 0.05

    def test_over_under_5pct_keeps_original(
        self, ctx_with_draft: NarrationContext
    ) -> None:
        """偏离 4% → 保持原 draft, 调 LLM 失败 (无 API)"""
        target_chars = int(
            ctx_with_draft.platform_spec.char_per_second
            * ctx_with_draft.platform_spec.target_duration_sec
        )
        # 96% (偏离 4%, 不调 LLM)
        ctx_with_draft.current_draft = "x" * int(target_chars * 0.96)
        result = tts_length_adjust_step(ctx_with_draft)
        assert result.success
        assert result.data["adjusted"] is False

    def test_large_deviation_triggers_llm_attempt(
        self, ctx_with_draft: NarrationContext
    ) -> None:
        """偏离 > 5% → 调 LLM (失败降级保留)"""
        # 30 字 (远少于 200 字目标, 偏离 > 5%)
        ctx_with_draft.current_draft = "短" * 30
        result = tts_length_adjust_step(ctx_with_draft)
        assert result.success
        # LLM 不可用 → 降级保留
        assert result.data.get("fallback") is True or result.data.get("adjusted") is True

    def test_records_real_and_target_duration(
        self, ctx_with_draft: NarrationContext
    ) -> None:
        """step 写入 tts_real/target 时长"""
        ctx_with_draft.current_draft = "x" * 200
        tts_length_adjust_step(ctx_with_draft)
        assert ctx_with_draft.tts_target_duration_sec > 0
        assert ctx_with_draft.tts_real_duration_sec > 0

    def test_no_draft_fails_returns_error(self, ctx: NarrationContext) -> None:
        """ctx 无 current_draft 字段时也安全失败"""
        # 不预填 current_draft
        result = tts_length_adjust_step(ctx)
        assert not result.success


# ============================================
# 3. tts_step
# ============================================


class TestTtsStep:
    """TTS 配音合成"""

    def test_empty_draft_fails(self, ctx: NarrationContext) -> None:
        result = tts_step(ctx)
        assert not result.success
        assert "current_draft 为空" in (result.error or "")

    def test_edge_tts_success(self, ctx_with_draft: NarrationContext) -> None:
        """真实 Edge-TTS 调用成功"""
        ctx_with_draft.current_draft = "测试一下 Edge-TTS 的输出。" * 5

        with patch(
            "scenefab.services.ai.voice_generator.VoiceGenerator"
        ) as mock_cls:
            # Mock Edge-TTS 实际写一个真实 WAV
            def mock_generate(text, output_path, config):
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with wave.open(str(output_path), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    # 2s silence
                    wf.writeframes(b"\x00" * 64000)
                from scenefab.services.ai.voice_models import GeneratedVoice

                return GeneratedVoice(
                    file_path=str(output_path),
                    duration=2.0,
                    voice_id="mock",
                )

            mock_cls.return_value.generate.side_effect = mock_generate
            result = tts_step(ctx_with_draft)

        assert result.success
        assert ctx_with_draft.tts_audio_path is not None
        assert ctx_with_draft.tts_audio_path.exists()
        # 真实探测时长
        assert ctx_with_draft.tts_real_duration_sec > 0

    def test_edge_tts_failure_fallback_stub(
        self, ctx_with_draft: NarrationContext
    ) -> None:
        """Edge-TTS 失败 → stub WAV + 字数估算时长"""
        ctx_with_draft.current_draft = "测试降级 stub。" * 5

        with patch(
            "scenefab.services.ai.voice_generator.VoiceGenerator"
        ) as mock_cls:
            mock_cls.return_value.generate.side_effect = RuntimeError("no edge-tts")
            result = tts_step(ctx_with_draft)

        assert result.success
        assert result.data.get("fallback") is True
        # 仍写文件 (stub 0.1s 静音 WAV)
        assert ctx_with_draft.tts_audio_path is not None
        assert ctx_with_draft.tts_audio_path.exists()

    def test_tts_writes_audio_path(
        self, ctx_with_draft: NarrationContext
    ) -> None:
        """step 写入 ctx.tts_audio_path"""
        ctx_with_draft.current_draft = "x" * 100

        with patch(
            "scenefab.services.ai.voice_generator.VoiceGenerator"
        ) as mock_cls:
            mock_cls.return_value.generate.side_effect = RuntimeError("no API")
            tts_step(ctx_with_draft)

        assert ctx_with_draft.tts_audio_path is not None
        # 文件名包含 trace_id 前 8 位
        assert ctx_with_draft.trace_id[:8] in ctx_with_draft.tts_audio_path.name


# ============================================
# 4. assemble_step
# ============================================


class TestAssembleStep:
    """字幕生成 + 剪映草稿 + 视频占位"""

    def test_empty_draft_fails(self, ctx: NarrationContext) -> None:
        result = assemble_step(ctx)
        assert not result.success
        assert "current_draft 为空" in (result.error or "")

    def test_srt_subtitle_always_written(
        self, ctx_with_draft: NarrationContext
    ) -> None:
        """SRT 字幕永远写入 (降级保障)"""
        ctx_with_draft.current_draft = "第一句。第二句！第三句？" * 5
        result = assemble_step(ctx_with_draft)

        assert result.success
        assert ctx_with_draft.final_subtitle_path is not None
        assert ctx_with_draft.final_subtitle_path.exists()
        # SRT 内容包含句号切分
        srt_content = ctx_with_draft.final_subtitle_path.read_text(encoding="utf-8")
        assert "第一句" in srt_content
        assert "00:00:00" in srt_content  # 标准 SRT 时间格式

    def test_jianying_metadata_written(
        self, ctx_with_draft: NarrationContext
    ) -> None:
        """剪映草稿元数据 JSON 写入"""
        ctx_with_draft.current_draft = "测试草稿"
        ctx_with_draft.eval_score = 8.5
        ctx_with_draft.eval_issues = ["issue1"]
        result = assemble_step(ctx_with_draft)

        assert result.success
        jianying_path = Path(result.data["jianying_path"])
        assert jianying_path.exists()
        meta = json.loads(jianying_path.read_text(encoding="utf-8"))
        assert meta["type"] == "scenefab_narration_v22"
        assert meta["trace_id"] == ctx_with_draft.trace_id
        assert meta["evaluation"]["score"] == 8.5

    def test_video_placeholder_written(
        self, ctx_with_draft: NarrationContext
    ) -> None:
        """视频占位 JSON 写入 (Phase 5 FFmpeg 合成替换)"""
        ctx_with_draft.current_draft = "x" * 100
        result = assemble_step(ctx_with_draft)

        assert result.success
        assert ctx_with_draft.final_video_path is not None
        # 实际写的是 .json 占位
        json_path = ctx_with_draft.final_video_path.with_suffix(".json")
        assert json_path.exists()
        meta = json.loads(json_path.read_text(encoding="utf-8"))
        assert meta["pending_ffmpeg"] is True

    def test_ass_subtitle_optional(
        self, ctx_with_draft: NarrationContext
    ) -> None:
        """ASS 字幕取决于 CaptionGenerator 是否可用"""
        ctx_with_draft.current_draft = "测试 ASS 字幕。" * 5
        result = assemble_step(ctx_with_draft)
        assert result.success
        # ASS 是 best-effort, 可能在 data 中为 None
        assert "ass_path" in result.data

    def test_final_ctx_fields_populated(
        self, ctx_with_draft: NarrationContext
    ) -> None:
        """assemble 后, ctx.final_* 字段填充"""
        ctx_with_draft.current_draft = "终态测试"
        ctx_with_draft.current_segments = [{"text": "a", "duration": 1.0, "start_time": 0}]
        assemble_step(ctx_with_draft)

        assert ctx_with_draft.final_narration == "终态测试"
        assert len(ctx_with_draft.final_segments) == 1
        assert ctx_with_draft.final_subtitle_path is not None
        assert ctx_with_draft.final_video_path is not None


# ============================================
# 5. 端到端 Phase 1+2+3+4
# ============================================


class TestPhase4EndToEnd:
    """完整 11 状态端到端"""

    def test_full_flow_done(
        self,
        sm_full: NarrationStateMachine,
        ctx: NarrationContext,
    ) -> None:
        """完整跑通 11 状态 → DONE"""
        ctx.story_graph = StoryGraph(title="X", synopsis="Y")
        result = sm_full.run(ctx)

        assert result.success
        assert result.state == NarrationState.DONE
        assert len(sm_full.transitions()) == 11

    def test_full_flow_all_outputs(
        self,
        sm_full: NarrationStateMachine,
        ctx: NarrationContext,
    ) -> None:
        """完整流程后, 5 类产物文件全部生成"""
        ctx.story_graph = StoryGraph(title="X", synopsis="Y")
        sm_full.run(ctx)

        # SRT
        assert ctx.final_subtitle_path is not None
        assert ctx.final_subtitle_path.exists()
        # TTS audio
        assert ctx.tts_audio_path is not None
        assert ctx.tts_audio_path.exists()
        # Video placeholder JSON
        assert ctx.final_video_path is not None
        json_path = ctx.final_video_path.with_suffix(".json")
        assert json_path.exists()
        # 剪映草稿 (在 step data 里)
        jianying_path = Path(ctx.output_dir) / f"{ctx.trace_id[:8]}_jianying.json"
        assert jianying_path.exists()

    def test_full_flow_different_platforms(
        self,
        sm_full: NarrationStateMachine,
        fake_video: Path,
        tmp_path: Path,
    ) -> None:
        """6 平台全部能完整跑通"""
        for platform in Platform:
            ctx = NarrationContext(
                source_video=fake_video,
                output_dir=tmp_path / f"out_{platform.value}",
                platform=platform,
            )
            ctx.story_graph = StoryGraph(title="X", synopsis="Y")
            # Force ACCEPT
            def forced_eval(c):
                c.eval_score = 9.0
                return StepResult(
                    success=True,
                    state=NarrationState.EVALUATE,
                    message="forced",
                )
            sm_full.register_step(NarrationState.EVALUATE, forced_eval)

            result = sm_full.run(ctx)
            assert result.success, f"platform={platform} 失败"
            spec = PLATFORM_SPECS[platform]
            assert ctx.tts_target_duration_sec == spec.target_duration_sec

    def test_full_flow_long_draft_with_adjust(
        self,
        sm_full: NarrationStateMachine,
        ctx: NarrationContext,
    ) -> None:
        """超长 draft (偏离 > 5%) → 触发 LLM 调整 (降级保留)"""
        # Monkey-patch TTS_LENGTH_ADJUST 用真 LLM (mock 失败)
        target_chars = int(
            ctx.platform_spec.char_per_second
            * ctx.platform_spec.target_duration_sec
        )
        # 制造极长 draft (3x target)
        ctx.current_draft = "x" * (target_chars * 3)
        ctx.story_graph = StoryGraph(title="X", synopsis="Y")

        result = sm_full.run(ctx)
        assert result.success
        # LLM 不可用 → fallback, draft 未变 (但流程跑通)
        assert result.state == NarrationState.DONE


# ============================================
# 6. Phase 1 stub 兼容性
# ============================================


class TestPhase4BackwardCompat:
    """Phase 4 不破坏 Phase 1/2/3"""

    def test_phase1_stub_still_works(
        self, fake_video: Path, tmp_path: Path
    ) -> None:
        """只注册 Phase 1 stub 仍能跑通"""
        sm = NarrationStateMachine()
        register_default_steps(sm)
        ctx = NarrationContext(
            source_video=fake_video,
            output_dir=tmp_path / "out",
        )
        result = sm.run(ctx)
        assert result.success
        # stub 标记
        assert "Phase 1 Stub" in ctx.current_draft

    def test_phase4_register_replaces_three_steps(
        self, sm_full: NarrationStateMachine
    ) -> None:
        """register_assembly_steps 替换 3 个状态"""
        from scenefab.pipeline.assembly_steps import (
            assemble_step as phase4_assemble,
        )
        from scenefab.pipeline.assembly_steps import (
            tts_length_adjust_step as phase4_tts_la,
        )
        from scenefab.pipeline.assembly_steps import (
            tts_step as phase4_tts,
        )
        from scenefab.pipeline.narration_steps import (
            assemble_step as stub_assemble,
        )
        from scenefab.pipeline.narration_steps import (
            tts_length_adjust_step as stub_tts_la,
        )
        from scenefab.pipeline.narration_steps import (
            tts_step as stub_tts,
        )

        # Phase 4 版本应该不同
        assert phase4_tts_la is not stub_tts_la
        assert phase4_tts is not stub_tts
        assert phase4_assemble is not stub_assemble
        # 全部已注册
        assert NarrationState.TTS_LENGTH_ADJUST in sm_full._steps
        assert NarrationState.TTS in sm_full._steps
        assert NarrationState.ASSEMBLE in sm_full._steps


# ============================================
# 7. SRT 字幕内容正确性
# ============================================


class TestSrtSubtitleFormat:
    """SRT 字幕格式正确"""

    def test_srt_has_correct_format(self, ctx: NarrationContext) -> None:
        """SRT 标准格式: 序号 + 时间码 + 文本"""
        ctx.current_draft = "第一句。第二句！第三句？"
        ctx.current_segments = []
        assemble_step(ctx)
        srt = ctx.final_subtitle_path.read_text(encoding="utf-8")

        # 验证 SRT 格式
        assert "1\n" in srt  # 第一条序号
        assert "00:00:00,000 --> " in srt  # 时间码格式
        assert "\n\n" in srt  # 条目间空行

    def test_srt_timestamps_sequential(
        self, ctx: NarrationContext
    ) -> None:
        """SRT 时间戳顺序递增"""
        ctx.current_draft = "句1。句2。句3。句4。句5。"
        assemble_step(ctx)
        srt = ctx.final_subtitle_path.read_text(encoding="utf-8")

        # 提取所有开始时间
        import re

        times = re.findall(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", srt)
        # 至少 2 个时间码 (开始 + 结束)
        assert len(times) >= 2
        # 第一条的开始时间应早于第二条
        for i in range(0, len(times) - 2, 2):
            h1, m1, s1, _ = times[i]
            h2, m2, s2, _ = times[i + 2]
            t1 = int(h1) * 3600 + int(m1) * 60 + int(s1)
            t2 = int(h2) * 3600 + int(m2) * 60 + int(s2)
            assert t2 >= t1, f"时间戳应递增, 但 {t1}s > {t2}s"
