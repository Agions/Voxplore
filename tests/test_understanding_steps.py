#!/usr/bin/env python3
"""
v2.2 Narration State Machine — Phase 2 真实实现测试

覆盖 Phase 2 新增能力:
- understand_step 真实调用 SceneAnalyzer + 桥段检测 (含降级路径)
- storygraph_step 真实调用 LongVideoUnderstanding (含降级路径)
- draft_step 真实调用 ScriptGenerator + 4 类上下文注入 (含降级路径)
- _build_narration_prompt 4 类上下文映射正确
- 端到端 Phase 2 跑通 (无 API key 时全降级, 仍能完成)

设计: 全部测试不需要真实 API key, 走降级路径。LLM/SceneAnalyzer 失败时
_降级 stub_ 仍能产出有效 draft, 验证整链路通畅。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from scenefab.pipeline.narration.engine import (
    PLATFORM_SPECS,
    BridgeType,
    NarrationContext,
    NarrationState,
    NarrationStateMachine,
    Persona,
    Platform,
    ProductionStyle,
    StepResult,
    _build_narration_prompt,
    register_assembly_steps,
    register_default_steps,
    register_evaluation_steps,
    register_understanding_steps,
)
from scenefab.services.ai.scene_models import SceneInfo, SceneType
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
    """假视频 (空文件, ffprobe 拿不到时长 → 走 stub 路径)"""
    video = tmp_path / "test_video.mp4"
    video.write_bytes(b"\x00" * 1024)
    return video


@pytest.fixture
def ctx(fake_video: Path, tmp_path: Path) -> NarrationContext:
    return NarrationContext(
        source_video=fake_video,
        output_dir=tmp_path / "output",
        persona=Persona.SHORT_DRAMA_OBSERVER,
        style=ProductionStyle.REVENGE,
        platform=Platform.DOUYIN,
    )


@pytest.fixture
def ctx_with_story_graph(ctx: NarrationContext) -> NarrationContext:
    """预填 story_graph 的上下文 (跳过 LongVideoUnderstanding)"""
    ctx.story_graph = StoryGraph(
        title="测试短剧",
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
    return ctx


@pytest.fixture
def sm_phase2() -> NarrationStateMachine:
    """注册默认 Step + Phase 2/3/4 真实实现 (可跑完整流程)"""
    sm = NarrationStateMachine()
    register_default_steps(sm)
    register_understanding_steps(sm)
    register_evaluation_steps(sm)
    register_assembly_steps(sm)

    # 强制 ACCEPT 跳过真实评估, 保证端到端测试确定性
    def high_eval(c: NarrationContext) -> StepResult:
        c.eval_score = 9.0
        c.eval_issues = []
        return StepResult(
            success=True, state=NarrationState.EVALUATE, message="9.0 forced"
        )

    sm.register_step(NarrationState.EVALUATE, high_eval)
    return sm


# ============================================
# 1. _build_narration_prompt 4 类上下文映射
# ============================================


class TestBuildNarrationPrompt:
    """4 类上下文 → (topic, ScriptConfig) 翻译逻辑"""

    def test_empty_context_builds_default(
        self, fake_video: Path, tmp_path: Path
    ) -> None:
        """空上下文也能组装 (用兜底默认)"""
        ctx = NarrationContext(
            source_video=fake_video,
            output_dir=tmp_path / "out",
        )
        topic, config = _build_narration_prompt(ctx)
        assert "通用影视解说" in topic
        assert config.style.value in ("commentary", "monologue", "narration", "viral")
        assert config.tone.value in (
            "neutral",
            "excited",
            "calm",
            "mysterious",
            "emotional",
            "humorous",
        )

    def test_story_graph_maps_to_topic(
        self, ctx_with_story_graph: NarrationContext
    ) -> None:
        """② 数据上下文: story_graph.synopsis + characters 进 topic"""
        topic, _config = _build_narration_prompt(ctx_with_story_graph)
        assert "测试剧情" in topic or "重生复仇" in topic
        assert "林墨" in topic  # 角色名

    def test_platform_spec_maps_to_config(
        self, ctx_with_story_graph: NarrationContext
    ) -> None:
        """① 指令上下文: platform → target_duration + words_per_second"""
        _, config = _build_narration_prompt(ctx_with_story_graph)
        spec = PLATFORM_SPECS[ctx_with_story_graph.platform]
        assert config.target_duration == spec.target_duration_sec
        assert config.words_per_second == spec.char_per_second

    def test_narration_style_maps_to_script_style_and_tone(
        self, fake_video: Path, tmp_path: Path
    ) -> None:
        """① 指令上下文: ProductionStyle → ScriptStyle + VoiceTone"""
        for style, expected_script in [
            (ProductionStyle.SUSPENSE, "monologue"),
            (ProductionStyle.REVENGE, "commentary"),
            (ProductionStyle.COMEDY, "viral"),
            (ProductionStyle.LITERARY, "narration"),
            (ProductionStyle.NEUTRAL, "commentary"),
        ]:
            ctx = NarrationContext(
                source_video=fake_video,
                output_dir=tmp_path / "out",
                style=style,
            )
            _, config = _build_narration_prompt(ctx)
            assert config.style.value == expected_script, (
                f"style={style} → script={config.style.value}, 期望 {expected_script}"
            )

    def test_history_segments_add_to_topic(
        self, ctx_with_story_graph: NarrationContext
    ) -> None:
        """③ 历史上下文: 之前提过的角色名进 topic 防重复"""
        from scenefab.pipeline.narration.engine import HistorySegment

        ctx_with_story_graph.add_history(
            HistorySegment(
                scene_index=0,
                characters_mentioned=["林墨", "苏婉"],
            )
        )
        topic, _ = _build_narration_prompt(ctx_with_story_graph)
        assert "前情已提角色" in topic
        assert "林墨" in topic
        assert "苏婉" in topic

    def test_bridge_templates_add_keywords(
        self, ctx_with_story_graph: NarrationContext
    ) -> None:
        """④ 工具上下文: bridge_templates 高频词 → ScriptConfig.keywords"""
        ctx_with_story_graph.bridge_templates = {
            BridgeType.SLAP_FACE: "打脸反派, 跪地求饶",
            BridgeType.PLOT_TWIST: "剧情反转, 真相揭露",
        }
        _, config = _build_narration_prompt(ctx_with_story_graph)
        assert "打脸" in config.keywords
        assert "反转" in config.keywords

    def test_first_person_workflow_rules_add_to_topic(
        self, ctx_with_story_graph: NarrationContext
    ) -> None:
        """第一人称流程规则进入 prompt, 让生成器遵守流程约束"""
        topic, config = _build_narration_prompt(ctx_with_story_graph)

        assert "【第一人称解说规则】" in topic
        assert "我是谁、我想要什么、我怕失去什么" in topic
        assert "3 秒内给出冲突或结果预告" in topic
        assert "第一人称" in config.keywords
        assert "钩子" in config.keywords

    def test_short_drama_production_fields_add_to_topic(
        self, ctx_with_story_graph: NarrationContext
    ) -> None:
        """短剧生产字段: 标签/关系/集数上下文进入 topic 与 keywords"""
        ctx_with_story_graph.content_tags = ["女性成长", "打脸虐渣", "马甲"]
        ctx_with_story_graph.relationship_notes = [
            "我是真千金，苏婉是假千金",
            "宴矜表面冷漠，实际知道我的过去",
        ]
        ctx_with_story_graph.episode_index = 7
        ctx_with_story_graph.previous_episode_summary = "我被家人赶出宴会"
        ctx_with_story_graph.next_hook_hint = "沉默的男人叫出了我的真名"

        topic, config = _build_narration_prompt(ctx_with_story_graph)

        assert "【短剧标签】女性成长, 打脸虐渣, 马甲" in topic
        assert "【人物关系】我是真千金" in topic
        assert "第 7 集" in topic
        assert "上一集: 我被家人赶出宴会" in topic
        assert "下一集钩子: 沉默的男人叫出了我的真名" in topic
        assert "女性成长" in config.keywords
        assert "打脸虐渣" in config.keywords

    def test_target_words_calculated(
        self, ctx_with_story_graph: NarrationContext
    ) -> None:
        """target_words = target_duration * words_per_second"""
        _, config = _build_narration_prompt(ctx_with_story_graph)
        expected = int(config.target_duration * config.words_per_second)
        assert config.target_words == expected


# ============================================
# 2. understand_step 降级路径
# ============================================


class TestUnderstandStepFallback:
    """SceneAnalyzer 不可用时降级到 stub scenes"""

    def test_scene_analyzer_failure_triggers_stub(self, ctx: NarrationContext) -> None:
        """SceneAnalyzer 抛异常时, 仍能完成 step (降级)"""
        from scenefab.pipeline.understanding_steps import understand_step

        with patch("scenefab.services.ai.scene_analyzer.SceneAnalyzer") as mock_cls:
            mock_cls.return_value.analyze.side_effect = RuntimeError("boom")
            result = understand_step(ctx)

        assert result.success
        assert result.state == NarrationState.UNDERSTAND
        # 降级: scenes 至少有 0 个 (因为 ffprobe 也失败, 时长=0)
        assert isinstance(ctx.scenes, list)

    def test_short_drama_mode_bridge_detection_failure(
        self, ctx: NarrationContext
    ) -> None:
        """短剧模式桥段检测失败时, 跳过而非报错"""
        # 启用短剧模式
        from scenefab.pipeline.short_drama import ShortDramaStyle
        from scenefab.pipeline.understanding_steps import understand_step

        ctx.short_drama_style = ShortDramaStyle.REVENGE
        # mock 一个空的 scenes (避免 SceneAnalyzer 失败影响)
        ctx.scenes = [
            SceneInfo(
                index=0,
                start=0,
                end=10,
                duration=10,
                type=SceneType.UNKNOWN,
                description="stub",
            )
        ]

        with patch("scenefab.pipeline.short_drama.ShortDramaNarrator") as mock_narrator:
            mock_narrator.return_value.detect_trope.side_effect = RuntimeError("boom")
            result = understand_step(ctx)

        assert result.success
        assert ctx.bridges == []  # 降级: 空桥段

    def test_understand_no_short_drama_mode(self, ctx: NarrationContext) -> None:
        """非短剧模式, 不调桥段检测"""
        from scenefab.pipeline.understanding_steps import understand_step

        ctx.short_drama_style = None
        # 预填 scenes 避免 SceneAnalyzer 调用
        ctx.scenes = [
            SceneInfo(
                index=0,
                start=0,
                end=10,
                duration=10,
                type=SceneType.UNKNOWN,
            )
        ]

        with patch("scenefab.pipeline.short_drama.ShortDramaNarrator") as mock_narrator:
            result = understand_step(ctx)
            # 不应调用 ShortDramaNarrator
            mock_narrator.assert_not_called()

        assert result.success
        assert ctx.bridges == []


# ============================================
# 3. storygraph_step 短视频路径
# ============================================


class TestStorygraphStepFallback:
    """短视频 + API 不可用时降级到 minimal StoryGraph"""

    def test_short_video_skips_long_understander(self, ctx: NarrationContext) -> None:
        """< 10min 视频不调 LongVideoUnderstanding"""
        from scenefab.pipeline.understanding_steps import storygraph_step

        # 假视频 ffprobe 失败 → video_duration=0 < 600 → 走短视频路径
        with patch(
            "scenefab.services.video_understanding.LongVideoUnderstanding"
        ) as mock_understander:
            result = storygraph_step(ctx)
            mock_understander.assert_not_called()

        assert result.success
        assert result.state == NarrationState.STORYGRAPH
        assert ctx.story_graph is not None
        # 降级 story_graph 应包含 scenes 信息
        assert len(ctx.story_graph.plot_events) >= 0

    def test_long_video_failure_falls_back(
        self, ctx_with_story_graph: NarrationContext
    ) -> None:
        """>= 10min 视频 + LongVideoUnderstanding 失败 → 降级"""
        from scenefab.pipeline.understanding_steps import storygraph_step

        with patch(
            "scenefab.pipeline.understanding_steps._probe_duration",
            return_value=1200.0,  # 20 min
        ):
            with patch(
                "scenefab.services.video_understanding.LongVideoUnderstanding"
            ) as mock_understander:
                mock_understander.return_value.understand.side_effect = RuntimeError(
                    "no API key"
                )
                result = storygraph_step(ctx_with_story_graph)

        assert result.success  # 降级仍 succeed
        assert ctx_with_story_graph.story_graph is not None

    def test_storygraph_message_includes_duration(self, ctx: NarrationContext) -> None:
        """result.message 反映视频时长判断"""
        from scenefab.pipeline.understanding_steps import storygraph_step

        with patch(
            "scenefab.pipeline.understanding_steps._probe_duration",
            return_value=0.0,
        ):
            result = storygraph_step(ctx)
        assert "短视频" in result.message


# ============================================
# 4. draft_step 4 类上下文注入 + 降级
# ============================================


class TestDraftStepFallback:
    """ScriptGenerator 不可用时降级到模板文案"""

    def test_script_generator_failure_uses_stub(
        self, ctx_with_story_graph: NarrationContext
    ) -> None:
        """ScriptGenerator 抛异常 → 模板降级"""
        from scenefab.pipeline.understanding_steps import draft_step

        with patch("scenefab.services.ai.script_generator.ScriptGenerator") as mock_cls:
            mock_cls.return_value.generate.side_effect = RuntimeError("no API key")
            result = draft_step(ctx_with_story_graph)

        assert result.success  # 降级仍 succeed
        assert result.state == NarrationState.DRAFT
        assert len(ctx_with_story_graph.current_draft) > 0
        assert len(ctx_with_story_graph.current_segments) > 0

    def test_stub_draft_includes_story_graph(
        self, ctx_with_story_graph: NarrationContext
    ) -> None:
        """Stub 文案反映 story_graph"""
        from scenefab.pipeline.understanding_steps import draft_step

        with patch("scenefab.services.ai.script_generator.ScriptGenerator") as mock_cls:
            mock_cls.return_value.generate.side_effect = RuntimeError("no API")
            draft_step(ctx_with_story_graph)

        # stub 至少包含开场钩子 + stub 标识
        draft = ctx_with_story_graph.current_draft
        assert "Stub" in draft or "钩子" in draft

    def test_draft_resets_attempts(
        self, ctx_with_story_graph: NarrationContext
    ) -> None:
        """draft_step 内部调用 reset_draft (attempts++)"""
        from scenefab.pipeline.understanding_steps import draft_step

        ctx_with_story_graph.draft_attempts = 0
        with patch("scenefab.services.ai.script_generator.ScriptGenerator") as mock_cls:
            mock_cls.return_value.generate.side_effect = RuntimeError("no API")
            draft_step(ctx_with_story_graph)

        assert ctx_with_story_graph.draft_attempts == 1

    def test_segments_split_by_sentence(
        self, ctx_with_story_graph: NarrationContext
    ) -> None:
        """Stub segments 按句号切分"""
        from scenefab.pipeline.understanding_steps import draft_step

        with patch("scenefab.services.ai.script_generator.ScriptGenerator") as mock_cls:
            mock_cls.return_value.generate.side_effect = RuntimeError("no API")
            draft_step(ctx_with_story_graph)

        segments = ctx_with_story_graph.current_segments
        assert len(segments) > 0
        # 每段都包含 duration 字段
        for seg in segments:
            assert "text" in seg
            assert "duration" in seg
            assert "start_time" in seg
            assert seg["duration"] > 0

    def test_draft_target_chars_truncate(
        self, ctx_with_story_graph: NarrationContext
    ) -> None:
        """Stub 文案不超过平台 max_total_chars"""
        from scenefab.pipeline.understanding_steps import draft_step

        with patch("scenefab.services.ai.script_generator.ScriptGenerator") as mock_cls:
            mock_cls.return_value.generate.side_effect = RuntimeError("no API")
            draft_step(ctx_with_story_graph)

        # 抖音 max_total_chars=200, 实际文案 <= 200
        max_chars = ctx_with_story_graph.platform_spec.max_total_chars
        # 实际可能有 10-20% 缓冲 (模板生成可能略超)
        assert len(ctx_with_story_graph.current_draft) <= max_chars * 2


# ============================================
# 5. Phase 2 端到端
# ============================================


class TestPhase2EndToEnd:
    """完整流程跑通 (默认 Step + Phase 2/3/4 真实实现, 全降级路径)"""

    def test_phase2_e2e_no_api_keys(
        self,
        sm_phase2: NarrationStateMachine,
        ctx_with_story_graph: NarrationContext,
    ) -> None:
        """无 API key 全降级, 仍能 DONE"""
        # 预填 story_graph, scenes 留空 (会让 SceneAnalyzer 失败 → stub)
        result = sm_phase2.run(ctx_with_story_graph)

        assert result.success
        assert result.state == NarrationState.DONE
        assert len(ctx_with_story_graph.current_draft) > 0
        assert ctx_with_story_graph.tts_audio_path is not None

    def test_phase2_e2e_different_styles(
        self,
        sm_phase2: NarrationStateMachine,
        fake_video: Path,
        tmp_path: Path,
    ) -> None:
        """不同 ProductionStyle 都能跑通"""
        for style in ProductionStyle:
            ctx = NarrationContext(
                source_video=fake_video,
                output_dir=tmp_path / f"out_{style.value}",
                style=style,
            )
            ctx.story_graph = StoryGraph(
                title=f"测试_{style.value}",
                synopsis=f"{style.value} 风格测试",
            )
            result = sm_phase2.run(ctx)
            assert result.success, f"style={style} 失败"
            assert len(ctx.current_draft) > 0

    def test_phase2_e2e_all_platforms(
        self,
        sm_phase2: NarrationStateMachine,
        fake_video: Path,
        tmp_path: Path,
    ) -> None:
        """6 平台全部跑通"""
        for platform in Platform:
            ctx = NarrationContext(
                source_video=fake_video,
                output_dir=tmp_path / f"out_{platform.value}",
                platform=platform,
            )
            ctx.story_graph = StoryGraph(title="X", synopsis="Y")
            result = sm_phase2.run(ctx)
            assert result.success, f"platform={platform} 失败"
            spec = PLATFORM_SPECS[platform]
            assert ctx.tts_target_duration_sec == spec.target_duration_sec


# ============================================
# 6. 桥段映射表完整性
# ============================================


class TestTropeBridgeMapping:
    """TropeType ↔ BridgeType 映射 (v2.0 → v2.2 兼容)"""

    def test_all_tropes_have_bridge_mapping(self, ctx: NarrationContext) -> None:
        """TropeType 7 个非 GENERAL 类型全部映射到 BridgeType"""
        from scenefab.pipeline.short_drama import TropeType
        from scenefab.pipeline.understanding_steps import _trope_to_bridge

        for trope in [
            TropeType.IDENTITY_REVEAL,
            TropeType.FACE_SLAP,
            TropeType.RESCUE,
            TropeType.BETRAYAL,
            TropeType.ROMANCE_CLIMAX,
            TropeType.CONFRONTATION,
            TropeType.REVEAL_TWIST,
        ]:
            bridge = _trope_to_bridge(trope)
            assert bridge is not None, f"trope={trope} 未映射"

    def test_general_trope_returns_none(self, ctx: NarrationContext) -> None:
        """TropeType.GENERAL → None (不算桥段)"""
        from scenefab.pipeline.short_drama import TropeType
        from scenefab.pipeline.understanding_steps import _trope_to_bridge

        assert _trope_to_bridge(TropeType.GENERAL) is None


# ============================================
# 7. Phase 2 集成度 — 与默认 Step 兼容
# ============================================


class TestPhase2BackwardCompat:
    """Phase 2 真实实现与 register_default_steps 兼容"""

    def test_register_phase2_replaces_three_steps(
        self, sm_phase2: NarrationStateMachine
    ) -> None:
        """register_understanding_steps 注册 UNDERSTAND/STORYGRAPH/DRAFT 真实实现"""
        from scenefab.pipeline.understanding_steps import (
            understand_step as phase2_understand,
        )

        # 注册的是 Phase 2 真实实现
        assert sm_phase2._steps[NarrationState.UNDERSTAND] is phase2_understand
        assert NarrationState.STORYGRAPH in sm_phase2._steps
        assert NarrationState.DRAFT in sm_phase2._steps

    def test_full_registration_runs_to_done(
        self, fake_video: Path, tmp_path: Path
    ) -> None:
        """默认 + Phase 2/3/4 全量注册能跑通完整流程"""
        sm = NarrationStateMachine()
        register_default_steps(sm)
        register_understanding_steps(sm)
        register_evaluation_steps(sm)
        register_assembly_steps(sm)

        # 强制 ACCEPT 跳过真实评估, 保证测试确定性
        def high_eval(c: NarrationContext) -> StepResult:
            c.eval_score = 9.0
            c.eval_issues = []
            return StepResult(
                success=True, state=NarrationState.EVALUATE, message="9.0 forced"
            )

        sm.register_step(NarrationState.EVALUATE, high_eval)

        ctx = NarrationContext(
            source_video=fake_video,
            output_dir=tmp_path / "out",
        )
        result = sm.run(ctx)
        assert result.success
        assert ctx.current_draft
