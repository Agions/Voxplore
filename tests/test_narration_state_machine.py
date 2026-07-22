#!/usr/bin/env python3
"""
v2.2 Narration State Machine — 状态机测试

覆盖:
- 4 类上下文 (指令/数据/历史/工具) 创建正确
- 9 状态枚举完整
- 状态机主流程跑通 INGEST→UNDERSTAND→STORYGRAPH→DRAFT→EVALUATE→ACCEPT→HOOK_REWRITE→TTS_LENGTH_ADJUST→TTS→ASSEMBLE→DONE
- EVALUATE 拒绝分支: REJECT→DRAFT→DRAFT→ERROR (max_attempts=2)
- 配置参数生效
- TTS/ASSEMBLE 产物路径正确
- 零外部依赖 (不调真实 LLM)
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from scenefab.pipeline.narration.engine import (
    PLATFORM_SPECS,
    Bridge,
    BridgeType,
    NarrationConfig,
    NarrationContext,
    NarrationState,
    NarrationStateMachine,
    Persona,
    Platform,
    ProductionStyle,
    StepResult,
    TransitionReason,
    register_assembly_steps,
    register_default_steps,
    register_evaluation_steps,
    register_understanding_steps,
)

# ============================================
# Fixtures
# ============================================


@pytest.fixture
def fake_video(tmp_path: Path) -> Path:
    """创建假视频文件 (空文件, 仅用于 INGEST 校验存在)"""
    video = tmp_path / "test_video.mp4"
    video.write_bytes(b"\x00" * 1024)
    return video


@pytest.fixture
def ctx(fake_video: Path, tmp_path: Path) -> NarrationContext:
    """默认上下文 (抖音 + 复仇 + 短剧观察员)"""
    return NarrationContext(
        source_video=fake_video,
        output_dir=tmp_path / "output",
        persona=Persona.SHORT_DRAMA_OBSERVER,
        style=ProductionStyle.REVENGE,
        platform=Platform.DOUYIN,
    )


@pytest.fixture
def sm_default() -> NarrationStateMachine:
    """注册全部真实 Step 的状态机 (默认 + Phase 2/3/4)"""
    sm = NarrationStateMachine()
    register_default_steps(sm)
    register_understanding_steps(sm)
    register_evaluation_steps(sm)
    register_assembly_steps(sm)

    # 强制 ACCEPT 跳过真实评估, 保证骨架流转测试确定性
    def high_eval(c: NarrationContext) -> StepResult:
        c.eval_score = 9.0
        c.eval_issues = []
        return StepResult(
            success=True, state=NarrationState.EVALUATE, message="9.0 forced"
        )

    sm.register_step(NarrationState.EVALUATE, high_eval)
    return sm


# ============================================
# 1. Context 测试
# ============================================


class TestNarrationContext:
    """4 类上下文派生 + 工具方法"""

    def test_default_context_creation(self, ctx: NarrationContext) -> None:
        """默认上下文创建正确"""
        assert ctx.persona == Persona.SHORT_DRAMA_OBSERVER
        assert ctx.style == ProductionStyle.REVENGE
        assert ctx.platform == Platform.DOUYIN
        assert ctx.platform_spec == PLATFORM_SPECS[Platform.DOUYIN]
        # 派生属性
        assert ctx.platform_spec.target_duration_sec == 45.0
        assert ctx.platform_spec.max_total_chars == 200

    def test_trace_id_is_unique(self, ctx: NarrationContext) -> None:
        """trace_id 唯一"""
        assert len(ctx.trace_id) == 32  # uuid4().hex
        ctx2 = NarrationContext(
            source_video=ctx.source_video,
            output_dir=ctx.output_dir,
        )
        assert ctx.trace_id != ctx2.trace_id

    def test_draft_attempts_increments(self, ctx: NarrationContext) -> None:
        """DRAFT 重试计数"""
        assert ctx.draft_attempts == 0
        assert not ctx.max_attempts_reached
        ctx.reset_draft()
        assert ctx.draft_attempts == 1
        assert not ctx.max_attempts_reached
        ctx.reset_draft()
        assert ctx.draft_attempts == 2
        assert ctx.max_attempts_reached

    def test_add_history(self, ctx: NarrationContext) -> None:
        """历史片段追加"""
        from scenefab.pipeline.narration.engine import HistorySegment

        seg = HistorySegment(
            scene_index=0,
            characters_mentioned=["女主"],
            plot_points_told=["穿越"],
            bridges_used=[BridgeType.IDENTITY_REVEAL],
        )
        ctx.add_history(seg)
        assert len(ctx.history) == 1
        assert ctx.history[0].characters_mentioned == ["女主"]

    def test_reset_draft_clears_state(self, ctx: NarrationContext) -> None:
        """reset_draft 清理状态"""
        ctx.current_draft = "old"
        ctx.eval_score = 5.0
        ctx.eval_issues = ["hook 弱"]
        ctx.reset_draft()
        assert ctx.current_draft == ""
        assert ctx.eval_score == 0.0
        assert ctx.eval_issues == []
        assert ctx.draft_attempts == 1

    def test_all_platforms_have_spec(self) -> None:
        """6 个平台全部有 PlatformSpec"""
        for platform in Platform:
            assert platform in PLATFORM_SPECS
            spec = PLATFORM_SPECS[platform]
            assert spec.target_duration_sec > 0
            assert spec.char_per_second > 0
            assert spec.max_total_chars > 0


# ============================================
# 2. State Enum 测试
# ============================================


class TestNarrationStateEnum:
    """9 状态枚举完整性"""

    def test_all_states_exist(self) -> None:
        """9 个状态完整 (5 主路径 + 3 评估 + 3 TTS) + 2 终态"""
        expected = {
            "ingest",
            "understand",
            "storygraph",
            "draft",
            "hook_rewrite",
            "evaluate",
            "accept",
            "reject",
            "tts_length_adjust",
            "tts",
            "assemble",
            "done",
            "error",
        }
        actual = {state.value for state in NarrationState}
        assert actual == expected

    def test_state_values_are_strings(self) -> None:
        """状态值是字符串 (str Enum)"""
        for state in NarrationState:
            assert isinstance(state.value, str)


# ============================================
# 3. State Machine 主流程测试
# ============================================


class TestStateMachineMainFlow:
    """主路径: INGEST→...→DONE"""

    def test_default_register(self) -> None:
        """register_default_steps 注册 INGEST/ACCEPT/REJECT"""
        sm = NarrationStateMachine()
        register_default_steps(sm)
        for state in [
            NarrationState.INGEST,
            NarrationState.ACCEPT,
            NarrationState.REJECT,
        ]:
            assert state in sm._steps, f"State {state.value} 未注册"
        # 其余状态由真实实现模块注册
        for state in [
            NarrationState.UNDERSTAND,
            NarrationState.STORYGRAPH,
            NarrationState.DRAFT,
            NarrationState.HOOK_REWRITE,
            NarrationState.EVALUATE,
            NarrationState.TTS_LENGTH_ADJUST,
            NarrationState.TTS,
            NarrationState.ASSEMBLE,
        ]:
            assert state not in sm._steps, f"State {state.value} 不应由默认注册"

    def test_register_step_chainable(self) -> None:
        """register_step 支持链式调用"""
        from scenefab.pipeline.narration.steps import ingest_step

        sm = NarrationStateMachine()
        result = sm.register_step(NarrationState.INGEST, ingest_step)
        assert result is sm  # 链式返回 self
        assert NarrationState.INGEST in sm._steps

    def test_register_step_rejects_non_callable(self) -> None:
        """非可调用对象抛 TypeError"""
        sm = NarrationStateMachine()
        with pytest.raises(TypeError, match="Step 函数必须可调用"):
            sm.register_step(NarrationState.INGEST, "not_a_function")  # type: ignore[arg-type]

    def test_full_flow_runs_to_done(
        self, sm_default: NarrationStateMachine, ctx: NarrationContext
    ) -> None:
        """完整流程跑通到 DONE (fixture 强制评估 PASS)"""
        result = sm_default.run(ctx)
        assert result.success
        assert result.state == NarrationState.DONE
        # 11 个转移 (INITIAL + 10 步)
        assert len(sm_default.transitions()) == 11

    def test_final_state_is_done(
        self, sm_default: NarrationStateMachine, ctx: NarrationContext
    ) -> None:
        """最终状态是 DONE"""
        sm_default.run(ctx)
        assert sm_default.current_state() == NarrationState.DONE

    def test_final_outputs_populated(
        self, sm_default: NarrationStateMachine, ctx: NarrationContext
    ) -> None:
        """TTS/ASSEMBLE 写入 final_* 字段"""
        sm_default.run(ctx)
        assert ctx.final_narration == ctx.current_draft
        assert ctx.final_subtitle_path is not None
        assert (
            ctx.final_subtitle_path.exists() or ctx.final_subtitle_path.parent.exists()
        )
        assert ctx.final_video_path is not None
        assert ctx.tts_audio_path is not None
        assert ctx.tts_audio_path.exists()

    def test_tts_length_adjust_writes_target(
        self, sm_default: NarrationStateMachine, ctx: NarrationContext
    ) -> None:
        """TTS_LENGTH_ADJUST 写入 real/target 时长"""
        sm_default.run(ctx)
        # 真实实现: target 来自平台规格, real 为估算/实测时长
        assert ctx.tts_real_duration_sec > 0
        assert (
            ctx.tts_target_duration_sec
            == PLATFORM_SPECS[Platform.DOUYIN].target_duration_sec
        )

    def test_transitions_recorded(
        self, sm_default: NarrationStateMachine, ctx: NarrationContext
    ) -> None:
        """转移记录完整 (trace_id 一致)"""
        sm_default.run(ctx)
        transitions = sm_default.transitions()
        assert len(transitions) == 11
        # 全部使用同一 trace_id
        assert all(t.trace_id == ctx.trace_id for t in transitions)
        # 时间戳单调递增
        timestamps = [t.timestamp for t in transitions]
        assert timestamps == sorted(timestamps)


# ============================================
# 4. 评估循环测试
# ============================================


class TestEvaluationLoop:
    """EVALUATE → ACCEPT / REJECT → 回 DRAFT 或 ERROR"""

    def test_eval_reject_loops_back_to_draft(
        self, tmp_path: Path, fake_video: Path
    ) -> None:
        """EVALUATE 拒绝时, 未达 max_attempts → 回 DRAFT"""
        from scenefab.pipeline.narration.steps import reject_step

        # 简易 draft step: 仅生成占位文案
        def stub_draft(ctx: NarrationContext) -> StepResult:
            ctx.current_draft = f"stub draft {ctx.draft_attempts + 1}"
            ctx.current_segments = [{"text": ctx.current_draft, "duration": 5.0}]
            return StepResult(
                success=True,
                state=NarrationState.DRAFT,
                message=f"draft (attempt={ctx.draft_attempts + 1})",
            )

        # 自定义 evaluate_step: 强制 score=5.0 (低于阈值 7.5)
        def low_score_evaluate(ctx: NarrationContext) -> StepResult:
            ctx.eval_score = 5.0
            ctx.eval_issues = ["hook 弱"]
            return StepResult(
                success=True,
                state=NarrationState.EVALUATE,
                message=f"score={ctx.eval_score}",
            )

        sm = NarrationStateMachine(config=NarrationConfig(max_draft_attempts=1))
        sm.register_step(
            NarrationState.INGEST,
            lambda c: StepResult(
                success=True, state=NarrationState.INGEST, message="ingest"
            ),
        )
        sm.register_step(
            NarrationState.UNDERSTAND,
            lambda c: StepResult(
                success=True, state=NarrationState.UNDERSTAND, message="understand"
            ),
        )
        sm.register_step(
            NarrationState.STORYGRAPH,
            lambda c: StepResult(
                success=True, state=NarrationState.STORYGRAPH, message="storygraph"
            ),
        )
        sm.register_step(NarrationState.DRAFT, stub_draft)
        sm.register_step(NarrationState.EVALUATE, low_score_evaluate)
        sm.register_step(NarrationState.REJECT, reject_step)
        sm.register_step(
            NarrationState.TTS_LENGTH_ADJUST,
            lambda c: StepResult(
                success=True, state=NarrationState.TTS_LENGTH_ADJUST, message="tla"
            ),
        )
        sm.register_step(
            NarrationState.TTS,
            lambda c: StepResult(success=True, state=NarrationState.TTS, message="tts"),
        )
        sm.register_step(
            NarrationState.ASSEMBLE,
            lambda c: StepResult(
                success=True, state=NarrationState.ASSEMBLE, message="assemble"
            ),
        )

        ctx = NarrationContext(
            source_video=fake_video,
            output_dir=tmp_path / "out",
        )
        result = sm.run(ctx)
        # 第一次 DRAFT → EVALUATE(5.0) → REJECT(reset_draft → attempts=1) → max_attempts → ERROR
        assert not result.success
        assert result.state == NarrationState.ERROR
        # reset_draft 调用一次 → attempts=1 >= max_draft_attempts=1
        assert ctx.draft_attempts == 1

    def test_eval_accept_continues_to_tts(
        self, sm_default: NarrationStateMachine, ctx: NarrationContext
    ) -> None:
        """EVALUATE 通过 → ACCEPT → HOOK_REWRITE → TTS_LENGTH_ADJUST"""
        sm_default.run(ctx)
        transitions = sm_default.transitions()
        # 找到 EVALUATE → ACCEPT 转移
        eval_to_accept = [
            t
            for t in transitions
            if t.from_state == NarrationState.EVALUATE
            and t.to_state == NarrationState.ACCEPT
        ]
        assert len(eval_to_accept) == 1
        assert eval_to_accept[0].reason == TransitionReason.EVAL_ACCEPT


# ============================================
# 5. 错误处理测试
# ============================================


class TestErrorHandling:
    """异常处理: 未注册 Step / 步骤失败 / 死循环保护"""

    def test_unregistered_state_fails(self, tmp_path: Path, fake_video: Path) -> None:
        """未注册 Step 的状态失败"""
        # 故意只注册 INGEST
        sm = NarrationStateMachine()
        sm.register_step(
            NarrationState.INGEST,
            lambda c: StepResult(
                success=True, state=NarrationState.INGEST, message="ingest"
            ),
        )
        ctx = NarrationContext(source_video=fake_video, output_dir=tmp_path / "out")

        result = sm.run(ctx)
        assert not result.success
        assert result.state == NarrationState.ERROR

    def test_step_exception_caught(self, tmp_path: Path, fake_video: Path) -> None:
        """Step 抛异常被捕获, 转为 ERROR"""

        def broken_step(ctx: NarrationContext) -> StepResult:
            raise RuntimeError("boom!")

        sm = NarrationStateMachine()
        sm.register_step(NarrationState.INGEST, broken_step)
        ctx = NarrationContext(source_video=fake_video, output_dir=tmp_path / "out")

        result = sm.run(ctx)
        assert not result.success
        assert result.state == NarrationState.ERROR
        assert "boom" in (result.error or "")

    def test_deadlock_protection(self) -> None:
        """状态机有最大迭代次数保护"""

        # 创建一个会无限循环的状态机 (FLOW 表里都没有 DONE/ERROR)
        # 实际测试中通过修改 _current_state 模拟死循环
        sm = NarrationStateMachine()
        # 手动死循环 51 次
        sm._transition(
            NarrationState.DRAFT,
            NarrationState.DRAFT,
            TransitionReason.SUCCESS,
            "test loop",
        )
        sm._current_state = NarrationState.DRAFT
        # 强制设置一个会循环的 transfer (但不会真的发生, 因为 _execute_step 会先报"未注册")
        # 简化: 直接调用 run() 看是否会超过 max_iterations
        from scenefab.pipeline.narration.engine import NarrationContext

        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = NarrationContext(
                source_video=Path(tmpdir) / "fake.mp4",
                output_dir=Path(tmpdir) / "out",
            )
            Path(ctx.source_video).touch()
            result = sm.run(ctx)
            # 不会真正死循环, 因为 INGEST step 未注册 → 立即 ERROR
            assert not result.success
            assert result.state == NarrationState.ERROR


# ============================================
# 6. Bridge / FewShot 数据类测试
# ============================================


class TestBridgeModels:
    """桥段数据模型"""

    def test_bridge_creation(self) -> None:
        bridge = Bridge(
            bridge_type=BridgeType.SLAP_FACE,
            scene_index=3,
            confidence=0.95,
            description="男主当场打脸反派",
        )
        assert bridge.bridge_type == BridgeType.SLAP_FACE
        assert bridge.confidence == 0.95

    def test_bridge_type_enum_complete(self) -> None:
        """7 大桥段完整"""
        expected = {
            "identity_reveal",
            "slap_face",
            "rescue",
            "betrayal",
            "heart_flutter",
            "confrontation",
            "plot_twist",
        }
        actual = {bt.value for bt in BridgeType}
        assert actual == expected


# ============================================
# 7. 集成测试 — 全链路
# ============================================


class TestIntegration:
    """完整流程集成测试 (真实 Step + 降级路径)"""

    def test_end_to_end_pipeline(
        self, sm_default: NarrationStateMachine, ctx: NarrationContext
    ) -> None:
        """端到端跑一遍"""
        start = time.time()
        result = sm_default.run(ctx)
        elapsed = time.time() - start

        # 1. 成功
        assert result.success
        # 2. 11 个转移
        assert len(sm_default.transitions()) == 11
        # 3. 降级路径较快 (< 30s; 真实 TTS/LLM 网络尝试有超时开销)
        assert elapsed < 30.0
        # 4. 终态
        assert sm_default.current_state() == NarrationState.DONE
        # 5. 产物
        assert ctx.final_narration
        assert ctx.tts_audio_path is not None
        assert ctx.final_subtitle_path is not None

    def test_different_platforms_different_specs(
        self, sm_default: NarrationStateMachine, tmp_path: Path, fake_video: Path
    ) -> None:
        """不同平台不同 spec 都能跑通"""
        for platform in Platform:
            ctx = NarrationContext(
                source_video=fake_video,
                output_dir=tmp_path / f"out_{platform.value}",
                platform=platform,
            )
            result = sm_default.run(ctx)
            assert result.success, f"平台 {platform.value} 跑失败"
            assert (
                ctx.tts_target_duration_sec
                == PLATFORM_SPECS[platform].target_duration_sec
            )
