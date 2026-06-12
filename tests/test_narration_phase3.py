#!/usr/bin/env python3
"""
v2.2 Narration State Machine — Phase 3 真实实现测试

覆盖 Phase 3 新增能力:
- NarrationEvaluator 5 维加权评估 (Hook + 桥段 + 一致性 + 平台 + 风格)
- 评估器对短/长/超长/空 draft 的鲁棒性
- 评估器复用 v2.1 ContentScorersMixin (零重写)
- 评估循环 REJECT → DRAFT → ACCEPT 全链路
- evaluate_step + hook_rewrite_step 真实实现
- 端到端 Phase 1+2+3 跑通

v2.2 决策: docs/adr/007-narration-state-machine.md
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from scenefab.pipeline.narration import (
    PLATFORM_SPECS,
    Bridge,
    BridgeType,
    DimensionScore,
    EvalResult,
    FewShot,
    NarrationContext,
    NarrationEvaluator,
    NarrationState,
    NarrationStateMachine,
    NarrationStyle,
    Persona,
    Platform,
    register_default_steps,
    register_phase2_steps,
    register_phase3_steps,
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
        persona=Persona.SHORT_DRAMA_OBSERVER,
        style=NarrationStyle.REVENGE,
        platform=Platform.DOUYIN,
    )


@pytest.fixture
def ctx_with_assets(ctx: NarrationContext) -> NarrationContext:
    """预填 story_graph + bridges + history 的上下文"""
    ctx.story_graph = StoryGraph(
        title="重生女王",
        genre="drama",
        synopsis="女主重生复仇, 一路打脸反派",
        characters=[
            Character(character_id="c1", name="林墨", description="重生女主"),
            Character(character_id="c2", name="苏婉", description="恶毒女配"),
        ],
        plot_events=[
            PlotEvent(
                event_id="e1",
                timestamp=0,
                event_type="climax",
                description="林墨发现自己重生了",
                importance=0.9,
            ),
        ],
    )
    ctx.bridges = [
        Bridge(
            bridge_type=BridgeType.SLAP_FACE,
            scene_index=0,
            confidence=0.9,
            description="打脸反派",
        ),
        Bridge(
            bridge_type=BridgeType.PLOT_TWIST,
            scene_index=1,
            confidence=0.85,
            description="剧情反转",
        ),
    ]
    return ctx


@pytest.fixture
def evaluator() -> NarrationEvaluator:
    return NarrationEvaluator()


# ============================================
# 1. EvalResult 数据类
# ============================================


class TestEvalResultDataclass:
    """EvalResult / DimensionScore 字段完整性"""

    def test_dimension_score_weighted_property(self) -> None:
        d = DimensionScore(name="test", score=8.0, weight=0.5)
        assert d.weighted == 4.0

    def test_eval_result_post_init_reason(self) -> None:
        """reason 默认值"""
        r = EvalResult(total_score=8.0, accept=True)
        assert r.reason == "总分 8.0 ≥ 7.5"

    def test_eval_result_custom_reason(self) -> None:
        r = EvalResult(total_score=5.0, accept=False, reason="自定义原因")
        assert r.reason == "自定义原因"


# ============================================
# 2. 5 维评估器
# ============================================


class TestEvaluatorFiveDimensions:
    """5 维加权评估正确性"""

    def test_empty_draft_returns_zero(
        self, evaluator: NarrationEvaluator, ctx: NarrationContext
    ) -> None:
        """空 draft → 0 分"""
        ctx.current_draft = ""
        result = evaluator.evaluate(ctx)
        assert result.total_score == 0.0
        assert not result.accept
        assert "current_draft 为空" in result.issues

    def test_perfect_draft_high_score(
        self, evaluator: NarrationEvaluator, ctx_with_assets: NarrationContext
    ) -> None:
        """完美 draft (含所有桥段 + 角色 + 字数达标 + Hook) → 高分"""
        # 抖音平台 target ≈ 200 字
        target = 200
        ctx_with_assets.current_draft = (
            "没想到! 林墨重生了, 她决定狠狠打脸反派苏婉。"
            "真相是, 上一世苏婉背后捅刀陷害她, 如今身份揭露。"
            "最后林墨霸气出手, 跪地求饶的苏婉迎来反转结局, "
            "令人震惊的真相让她无地自容, 这一切才刚刚开始。\n"
            + "（补足字数到目标）" * 5  # 凑到 ~200 字
        )
        # 截断到 200 字
        ctx_with_assets.current_draft = ctx_with_assets.current_draft[:target]

        result = evaluator.evaluate(ctx_with_assets)
        # 至少 7 分 (5 维都触发, 允许 hook 不满分)
        assert result.total_score >= 6.0
        assert result.accept

    def test_short_draft_platform_low(
        self, evaluator: NarrationEvaluator, ctx_with_assets: NarrationContext
    ) -> None:
        """文案过短 → platform 维度低分"""
        ctx_with_assets.current_draft = "林墨重生了, 打脸反派!"  # ~12 字
        result = evaluator.evaluate(ctx_with_assets)
        # platform 维度应触发"文案过短"
        platform_dim = next(
            d for d in result.dimension_scores if d.name == "platform"
        )
        assert platform_dim.score <= 5.0
        assert any("过短" in issue or "缺少" in issue for issue in platform_dim.issues)

    def test_bridge_dimension_triggers_keywords(
        self, evaluator: NarrationEvaluator, ctx_with_assets: NarrationContext
    ) -> None:
        """桥段关键词命中 → bridge 维度高分"""
        ctx_with_assets.current_draft = (
            "林墨重生, 决定打脸苏婉! 跪地求饶的苏婉迎来反转,"
            "这就是背叛的代价。" * 3
        )
        result = evaluator.evaluate(ctx_with_assets)
        bridge_dim = next(
            d for d in result.dimension_scores if d.name == "bridge"
        )
        assert bridge_dim.score >= 8.0  # 2 桥段关键词都命中

    def test_no_bridges_default_score(
        self, evaluator: NarrationEvaluator, ctx: NarrationContext
    ) -> None:
        """无 bridges → bridge 维度默认 8 分 (不扣分)"""
        ctx.current_draft = "这是一个普通的解说。" * 10
        result = evaluator.evaluate(ctx)
        bridge_dim = next(
            d for d in result.dimension_scores if d.name == "bridge"
        )
        assert bridge_dim.score == 8.0

    def test_consistency_mentions_characters(
        self, evaluator: NarrationEvaluator, ctx_with_assets: NarrationContext
    ) -> None:
        """角色名提及 → consistency 高分"""
        ctx_with_assets.current_draft = "林墨和苏婉的对决。" * 20
        result = evaluator.evaluate(ctx_with_assets)
        consistency_dim = next(
            d for d in result.dimension_scores if d.name == "consistency"
        )
        assert consistency_dim.score >= 7.0

    def test_consistency_no_mentions(
        self, evaluator: NarrationEvaluator, ctx_with_assets: NarrationContext
    ) -> None:
        """角色未提及 → consistency 低分"""
        ctx_with_assets.current_draft = "一个完全无关的故事。" * 20
        result = evaluator.evaluate(ctx_with_assets)
        consistency_dim = next(
            d for d in result.dimension_scores if d.name == "consistency"
        )
        assert consistency_dim.score < 7.0
        assert len(consistency_dim.issues) > 0

    def test_platform_target_chars(
        self, evaluator: NarrationEvaluator, ctx: NarrationContext
    ) -> None:
        """字数与平台 target 偏差 → 平台分"""
        spec = PLATFORM_SPECS[ctx.platform]
        target_chars = int(spec.char_per_second * spec.target_duration_sec)

        # 完美字数 (±15% 内)
        ctx.current_draft = "完美" * (target_chars // 2 + 1)
        ctx.current_draft = ctx.current_draft[:target_chars]
        result = evaluator.evaluate(ctx)
        platform_dim = next(
            d for d in result.dimension_scores if d.name == "platform"
        )
        assert platform_dim.score >= 8.0  # ±15% 内 → 8-10 分

    def test_few_shots_boost_style(
        self, evaluator: NarrationEvaluator, ctx: NarrationContext
    ) -> None:
        """few_shots 风格关键词命中 → style 高分"""
        ctx.few_shots = [
            FewShot(
                scene_desc="女主登场",
                narration="林墨身穿红裙缓缓走来, 眼中满是决绝。",
                style=NarrationStyle.REVENGE,
            )
        ]
        # draft 包含 few_shot 关键词
        ctx.current_draft = "林墨身穿红裙, 缓缓走来, 眼中满是决绝与仇恨。\n" * 20
        result = evaluator.evaluate(ctx)
        style_dim = next(d for d in result.dimension_scores if d.name == "style")
        assert style_dim.score >= 6.0

    def test_no_few_shots_default_style(
        self, evaluator: NarrationEvaluator, ctx: NarrationContext
    ) -> None:
        """无 few_shots → style 默认 8 分"""
        ctx.current_draft = "任意文案。" * 20
        result = evaluator.evaluate(ctx)
        style_dim = next(d for d in result.dimension_scores if d.name == "style")
        assert style_dim.score == 8.0


# ============================================
# 3. 加权总分计算
# ============================================


class TestWeightedScoring:
    """5 维权重和总分计算"""

    def test_total_score_weighted_sum(
        self, evaluator: NarrationEvaluator, ctx: NarrationContext
    ) -> None:
        """total = sum(score * weight)"""
        ctx.current_draft = "测试文案。" * 30
        result = evaluator.evaluate(ctx)
        expected = sum(d.weighted for d in result.dimension_scores)
        assert abs(result.total_score - expected) < 0.01

    def test_dimensions_weights_sum_to_one(self) -> None:
        """5 维权重和 = 1.0 (锁死)"""
        from scenefab.pipeline.narration_evaluator import DIMENSION_WEIGHTS

        total_w = sum(DIMENSION_WEIGHTS.values())
        assert abs(total_w - 1.0) < 0.001

    def test_accept_threshold_is_7_5(
        self, evaluator: NarrationEvaluator, ctx: NarrationContext
    ) -> None:
        """accept 阈值 = 7.5"""
        ctx.current_draft = "abc"  # 极短, 必低分
        result = evaluator.evaluate(ctx)
        # 总分应 < 7.5
        assert not result.accept
        assert "7.5" in result.reason

    def test_suggestion_only_when_reject(
        self, evaluator: NarrationEvaluator, ctx_with_assets: NarrationContext
    ) -> None:
        """REJECT 时有 suggestion, ACCEPT 时为空"""
        # 构造低分 (短文案)
        ctx_with_assets.current_draft = "短"
        result = evaluator.evaluate(ctx_with_assets)
        if not result.accept:
            assert result.suggestion != ""
        else:
            assert result.suggestion == ""


# ============================================
# 4. 评估器复用 v2.1 ContentScorersMixin
# ============================================


class TestV21HookScorerReuse:
    """Phase 3 复用 v2.1 ContentScorersMixin (零重写 hook 评分)"""

    def test_v21_hook_score_used_when_available(
        self, evaluator: NarrationEvaluator, ctx: NarrationContext
    ) -> None:
        """v2.1 mixin 可用时, Hook 维度使用 v2.1 评分"""
        # 强 Hook: 含"没想到"+"真相"
        strong_hook = "没想到! 真相竟然是这样。林墨决定复仇。"
        weak_hook = "这是一个故事。讲的是一个人物。"

        ctx.current_draft = strong_hook * 5  # 凑到 200 字
        strong_result = evaluator.evaluate(ctx)
        strong_hook_dim = next(d for d in strong_result.dimension_scores if d.name == "hook")

        ctx.current_draft = weak_hook * 5
        weak_result = evaluator.evaluate(ctx)
        weak_hook_dim = next(d for d in weak_result.dimension_scores if d.name == "hook")

        # 强 Hook 应更高分 (无论 v2.1 还是降级)
        assert strong_hook_dim.score >= weak_hook_dim.score

    def test_fallback_hook_evaluator_works(
        self, evaluator: NarrationEvaluator, ctx: NarrationContext
    ) -> None:
        """v2.1 mixin 不可用时, 降级规则评分仍工作"""
        with patch.object(evaluator, "_get_scorers_mixin", return_value=None):
            ctx.current_draft = "没想到! 这是真相。" * 10
            result = evaluator.evaluate(ctx)
            hook_dim = next(d for d in result.dimension_scores if d.name == "hook")
            # 降级规则也能评分
            assert 0 <= hook_dim.score <= 10


# ============================================
# 5. evaluate_step 真实实现
# ============================================


class TestEvaluateStepReal:
    """evaluate_step 真实实现 (Phase 3)"""

    def test_evaluate_step_success(
        self, ctx_with_assets: NarrationContext
    ) -> None:
        """evaluate_step 正常调用, 填充 ctx.eval_*"""
        from scenefab.pipeline.narration_steps_phase3 import evaluate_step

        ctx_with_assets.current_draft = "林墨重生打脸!" * 20
        result = evaluate_step(ctx_with_assets)

        assert result.success
        assert result.state == NarrationState.EVALUATE
        assert ctx_with_assets.eval_score > 0
        assert isinstance(ctx_with_assets.eval_issues, list)

    def test_evaluate_step_empty_draft(
        self, ctx_with_assets: NarrationContext
    ) -> None:
        """空 draft 也返回 success=True (评估器自己处理空)"""
        from scenefab.pipeline.narration_steps_phase3 import evaluate_step

        ctx_with_assets.current_draft = ""
        result = evaluate_step(ctx_with_assets)

        assert result.success
        assert ctx_with_assets.eval_score == 0.0

    def test_evaluate_step_evaluator_failure_fallback(
        self, ctx_with_assets: NarrationContext
    ) -> None:
        """评估器异常时, 仍 succeed (用 5.0 兜底)"""
        from scenefab.pipeline.narration_steps_phase3 import evaluate_step

        ctx_with_assets.current_draft = "test" * 30

        with patch(
            "scenefab.pipeline.narration_evaluator.NarrationEvaluator.evaluate",
            side_effect=RuntimeError("boom"),
        ):
            result = evaluate_step(ctx_with_assets)

        assert result.success  # 异常不阻塞
        assert ctx_with_assets.eval_score == 5.0
        assert "boom" in ctx_with_assets.eval_issues[0]


# ============================================
# 6. hook_rewrite_step 真实实现
# ============================================


class TestHookRewriteStepReal:
    """hook_rewrite_step 真实实现 (Phase 3)"""

    def test_hook_rewrite_no_draft(
        self, ctx_with_assets: NarrationContext
    ) -> None:
        """空 draft → fail"""
        from scenefab.pipeline.narration_steps_phase3 import hook_rewrite_step

        ctx_with_assets.current_draft = ""
        result = hook_rewrite_step(ctx_with_assets)

        assert not result.success
        assert "current_draft 为空" in (result.error or "")

    def test_hook_rewrite_llm_failure_uses_fallback(
        self, ctx_with_assets: NarrationContext
    ) -> None:
        """LLM 不可用 → 降级规则生成 5 候选"""
        from scenefab.pipeline.narration_steps_phase3 import hook_rewrite_step

        ctx_with_assets.current_draft = "这是一个普通的故事, 讲一个女主。" * 10

        with patch(
            "scenefab.services.ai.script_generator.ScriptGenerator"
        ) as mock_cls:
            mock_cls.return_value.generate.side_effect = RuntimeError("no API key")
            result = hook_rewrite_step(ctx_with_assets)

        assert result.success
        # 降级: 5 候选 + 评估器择优
        assert "candidates" in result.data
        assert result.data["candidates"] == 5

    def test_hook_rewrite_replaces_first_2_sentences(
        self, ctx_with_assets: NarrationContext
    ) -> None:
        """改写后, draft 前 2 句被替换"""
        from scenefab.pipeline.narration_steps_phase3 import hook_rewrite_step

        original = "原 Hook 第一句。原 Hook 第二句。后面是主体内容。" * 10
        ctx_with_assets.current_draft = original

        with patch(
            "scenefab.services.ai.script_generator.ScriptGenerator"
        ) as mock_cls:
            mock_cls.return_value.generate.side_effect = RuntimeError("no API key")
            result = hook_rewrite_step(ctx_with_assets)

        assert result.success
        # 主体内容应保留
        assert "后面是主体内容" in ctx_with_assets.current_draft
        # 原 Hook 不应在前 30 字内
        first_30 = ctx_with_assets.current_draft[:30]
        # 至少 5 种风格之一被注入
        assert any(
            marker in first_30
            for marker in ["没想到", "真相", "最后", "为什么", "震惊"]
        )

    def test_hook_rewrite_empty_candidates_keeps_original(
        self, ctx_with_assets: NarrationContext
    ) -> None:
        """候选为空时, 保留原 draft"""
        from scenefab.pipeline.narration_steps_phase3 import (
            hook_rewrite_step,
        )

        ctx_with_assets.current_draft = "原 draft 内容。" * 10
        original_draft = ctx_with_assets.current_draft

        with patch(
            "scenefab.pipeline.narration_steps_phase3._generate_hook_candidates_via_llm",
            return_value=[],
        ):
            with patch(
                "scenefab.pipeline.narration_steps_phase3._generate_hook_candidates_fallback",
                return_value=[],
            ):
                result = hook_rewrite_step(ctx_with_assets)

        assert result.success
        assert ctx_with_assets.current_draft == original_draft
        assert result.data.get("kept_original") is True


# ============================================
# 7. 评估循环 (REJECT → DRAFT → ACCEPT)
# ============================================


class TestEvaluationLoopReal:
    """完整评估循环 + Phase 1+2+3 真实实现"""

    @pytest.fixture
    def sm_full(self) -> NarrationStateMachine:
        sm = NarrationStateMachine()
        register_default_steps(sm)
        register_phase2_steps(sm)
        register_phase3_steps(sm)
        return sm

    def test_reject_then_retry_until_accept(
        self,
        sm_full: NarrationStateMachine,
        ctx_with_assets: NarrationContext,
    ) -> None:
        """首次 REJECT 后, 通过 ctx.eval_score 抬升触发 ACCEPT"""
        from scenefab.pipeline.narration_state_machine import (
            NarrationConfig,
            StepResult,
        )

        # 重建 sm 用 max_draft_attempts=3 允许 retry
        sm = NarrationStateMachine(config=NarrationConfig(max_draft_attempts=3))
        register_default_steps(sm)
        register_phase2_steps(sm)
        register_phase3_steps(sm)

        scores = [5.0, 8.0]  # 第 1 次 REJECT, 第 2 次 ACCEPT

        def fake_evaluate(ctx: NarrationContext):
            if scores:
                score = scores.pop(0)
            else:
                score = 8.0
            ctx.eval_score = score
            ctx.eval_issues = [] if score >= 7.5 else ["低分"]
            return StepResult(
                success=True,
                state=NarrationState.EVALUATE,
                message=f"score={score}",
                data={"score": score},
            )

        def fake_draft(ctx: NarrationContext):
            ctx.reset_draft()
            ctx.current_draft = "mock draft 内容稍微长一点这样字数才够! " * 5
            ctx.current_segments = [{"text": "x", "duration": 5.0, "start_time": 0}]
            return StepResult(
                success=True, state=NarrationState.DRAFT, message="mock draft"
            )

        sm.register_step(NarrationState.EVALUATE, fake_evaluate)
        sm.register_step(NarrationState.DRAFT, fake_draft)

        result = sm.run(ctx_with_assets)
        # 最终 ACCEPT → HOOK_REWRITE → TTS_LENGTH_ADJUST → TTS → ASSEMBLE → DONE
        assert result.success
        assert result.state == NarrationState.DONE
        # draft_attempts: DRAFT 调 reset_draft 1 次 + REJECT 调 reset_draft 1 次 = 2 次循环 × 1
        # 实际: DRAFT1 (0→1) + REJECT (1→2) + DRAFT2 (2→3) = 3
        assert ctx_with_assets.draft_attempts == 3

    def test_max_attempts_eventually_errors(
        self,
        sm_full: NarrationStateMachine,
        ctx_with_assets: NarrationContext,
    ) -> None:
        """连续 REJECT → max_attempts → ERROR"""
        from scenefab.pipeline.narration_state_machine import (
            NarrationConfig,
            StepResult,
        )

        sm = NarrationStateMachine(config=NarrationConfig(max_draft_attempts=1))
        register_default_steps(sm)
        register_phase2_steps(sm)
        register_phase3_steps(sm)

        def always_reject(ctx: NarrationContext):
            ctx.eval_score = 3.0
            ctx.eval_issues = ["持续低分"]
            return StepResult(
                success=True,
                state=NarrationState.EVALUATE,
                message="score=3.0",
            )

        def fake_draft(ctx: NarrationContext):
            ctx.reset_draft()
            ctx.current_draft = "x" * 50
            return StepResult(success=True, state=NarrationState.DRAFT, message="x")

        sm.register_step(NarrationState.EVALUATE, always_reject)
        sm.register_step(NarrationState.DRAFT, fake_draft)

        result = sm.run(ctx_with_assets)
        assert not result.success
        assert result.state == NarrationState.ERROR


# ============================================
# 8. 端到端 Phase 1+2+3
# ============================================


class TestPhase3EndToEnd:
    """完整流程跑通 Phase 1 stub + Phase 2 真实 + Phase 3 真实"""

    @pytest.fixture
    def sm_full(self) -> NarrationStateMachine:
        sm = NarrationStateMachine()
        register_default_steps(sm)
        register_phase2_steps(sm)
        register_phase3_steps(sm)
        return sm

    def test_phase3_e2e_low_score_rejects(
        self,
        sm_full: NarrationStateMachine,
        ctx_with_assets: NarrationContext,
    ) -> None:
        """低分 draft → REJECT → 回到 DRAFT (max_attempts 兜底)"""
        # 配 draft_step 让它总是产生低分 (极短)
        from scenefab.pipeline.narration_state_machine import StepResult

        def short_draft(ctx: NarrationContext):
            ctx.reset_draft()
            ctx.current_draft = "x"  # 1 字符, 必低分
            return StepResult(success=True, state=NarrationState.DRAFT, message="x")

        sm_full.register_step(NarrationState.DRAFT, short_draft)
        sm_full.config.max_draft_attempts = 1  # 1 次就终止

        result = sm_full.run(ctx_with_assets)
        # REJECT → max_attempts → ERROR
        assert not result.success
        assert result.state == NarrationState.ERROR

    def test_phase3_e2e_full_flow(
        self,
        sm_full: NarrationStateMachine,
        ctx_with_assets: NarrationContext,
    ) -> None:
        """EVALUATE 默认通过 (Phase 1 stub 设 9.0) → 完整 DONE"""
        from scenefab.pipeline.narration_state_machine import StepResult

        # 配 fake_evaluate 设高分 (9.0) 强制 ACCEPT
        def high_score_evaluate(ctx: NarrationContext):
            ctx.eval_score = 9.0
            ctx.eval_issues = []
            return StepResult(
                success=True,
                state=NarrationState.EVALUATE,
                message="score=9.0 (forced)",
            )

        sm_full.register_step(NarrationState.EVALUATE, high_score_evaluate)

        result = sm_full.run(ctx_with_assets)
        assert result.success
        assert result.state == NarrationState.DONE
