#!/usr/bin/env python3
"""Unit tests for v2.5.0 multi-strategy / series-context features.

Covers:
- ``build_prompt`` / ``build_batch_prompt`` propagating ``multi_strategy``
  and ``series_context`` (Phase I)
- ``ScriptGenerator.generate`` / ``generate_monologue`` accepting both
- ``compute_adaptive_parallel`` + ``MonologueMaker.create_batch``
  defaulting to CPU-adaptive parallelism (Phase K)
- ``SeriesContextDialog`` form round-trip (Phase J)
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.models.project import (
    MultiVideoSource,
    SeriesContext,
)
from app.services.ai.script_generator import (
    ScriptConfig,
    ScriptGenerator,
    ScriptStyle,
)
from app.services.ai.script_generator._prompt_builder import (
    build_batch_prompt,
    build_prompt,
)
from app.services.ai.script_generator._style_prompts import (
    STRATEGY_INSTRUCTIONS,
    series_context_block,
)
from app.services.video.monologue_maker import (
    MonologueMaker,
    _format_episode_name,
    compute_adaptive_parallel,
)


@pytest.fixture
def fake_video_dir():
    """Local copy of the same fixture in tests/models/test_multi_video.py
    so this test module is self-contained.
    """
    with tempfile.TemporaryDirectory() as td:
        for name in ("a.mp4", "b.mp4", "c.mp4"):
            (Path(td) / name).write_bytes(b"\x00" * 1024)
        yield td


def _paths(fake_dir: str, names=("a.mp4", "b.mp4", "c.mp4")) -> list[str]:
    return [str(Path(fake_dir) / n) for n in names]


# ============================================================================
# Phase I: prompt builder multi_strategy / series_context
# ============================================================================


class TestBuildPromptStrategy:
    """build_prompt should append the right strategy snippet + series block."""

    def test_no_strategy_keeps_v24_shape(self):
        """向后兼容：不传 strategy 时，prompt 没有任何 v2.5.0 新增片段。"""
        cfg = ScriptConfig(style=ScriptStyle.MONOLOGUE, target_duration=30.0)
        prompt = build_prompt("test topic", cfg)
        assert "【单视频场景】" not in prompt
        assert "【整季系列场景】" not in prompt
        assert "【系列背景（v2.5.0）】" not in prompt

    @pytest.mark.parametrize(
        "strategy,marker",
        [
            ("single", "【单视频场景】"),
            ("concat", "【拼接场景】"),
            ("batch", "【批量独立场景】"),
            ("series", "【整季系列场景】"),
        ],
    )
    def test_each_strategy_injects_marker(self, strategy, marker):
        cfg = ScriptConfig(style=ScriptStyle.MONOLOGUE)
        prompt = build_prompt("topic", cfg, multi_strategy=strategy)
        assert marker in prompt
        assert "字数要求" in prompt  # 既有模板内容保留

    def test_unknown_strategy_silently_ignored(self):
        """未知 strategy 值不应抛错，也不应被注入。"""
        cfg = ScriptConfig(style=ScriptStyle.MONOLOGUE)
        prompt = build_prompt("topic", cfg, multi_strategy="bogus")
        assert "【单视频场景】" not in prompt
        assert "【整季系列场景】" not in prompt

    def test_series_strategy_requires_series_context(self):
        """series 策略 + 非空 SeriesContext → 渲染系列背景块。"""
        cfg = ScriptConfig(style=ScriptStyle.MONOLOGUE)
        ctx = SeriesContext(
            series_title="深夜短剧",
            genre="都市",
            total_episodes=20,
            shared_characters=["女主", "男主"],
            shared_plot="一段跨越二十年的爱情",
            world_setting="现代都市",
        )
        prompt = build_prompt(
            "主题", cfg, multi_strategy="series", series_context=ctx)
        assert "【整季系列场景】" in prompt
        assert "【系列背景（v2.5.0）】" in prompt
        assert "深夜短剧" in prompt
        assert "都市" in prompt
        assert "20" in prompt
        assert "女主、男主" in prompt
        assert "一段跨越二十年的爱情" in prompt
        assert "现代都市" in prompt

    def test_series_strategy_without_series_context_no_block(self):
        """series 策略但 ctx=None/空 → 不渲染背景块，但不抛错。"""
        cfg = ScriptConfig(style=ScriptStyle.MONOLOGUE)
        prompt = build_prompt(
            "主题", cfg, multi_strategy="series", series_context=None)
        assert "【整季系列场景】" in prompt
        assert "【系列背景（v2.5.0）】" not in prompt

    def test_non_series_strategy_ignores_series_context(self):
        """非 series 策略 + 提供 ctx → 不应渲染系列背景块。"""
        cfg = ScriptConfig(style=ScriptStyle.MONOLOGUE)
        ctx = SeriesContext(series_title="不应出现")
        prompt = build_prompt(
            "主题", cfg, multi_strategy="batch", series_context=ctx)
        assert "【批量独立场景】" in prompt
        assert "不应出现" not in prompt
        assert "【系列背景（v2.5.0）】" not in prompt


class TestBuildBatchPromptStrategy:
    def test_no_strategy_keeps_v24_shape(self):
        cfg = ScriptConfig(style=ScriptStyle.MONOLOGUE, target_duration=10.0)
        batch = [("a", cfg), ("b", cfg)]
        prompt = build_batch_prompt(batch)
        assert "【批量独立场景】" not in prompt

    def test_batch_strategy_renders_header(self):
        cfg = ScriptConfig(style=ScriptStyle.MONOLOGUE, target_duration=10.0)
        batch = [("a", cfg), ("b", cfg)]
        prompt = build_batch_prompt(batch, multi_strategy="batch")
        assert "【批量独立场景】" in prompt
        # 子段落仍存在
        assert "=== 段落 1 ===" in prompt
        assert "=== 段落 2 ===" in prompt

    def test_series_strategy_renders_context(self):
        cfg = ScriptConfig(style=ScriptStyle.MONOLOGUE, target_duration=10.0)
        batch = [("a", cfg)]
        ctx = SeriesContext(series_title="剧名A")
        prompt = build_batch_prompt(
            batch, multi_strategy="series", series_context=ctx)
        assert "【整季系列场景】" in prompt
        assert "剧名A" in prompt


class TestSeriesContextBlock:
    def test_none_returns_empty(self):
        assert series_context_block(None) == ""

    def test_empty_ctx_returns_header_only(self):
        """全空 ctx 至少返回头部标记，提示词一致性。"""
        block = series_context_block(SeriesContext())
        # 至少包含头部
        assert "【系列背景（v2.5.0）】" in block

    def test_partial_fields_skipped(self):
        ctx = SeriesContext(series_title="X", shared_characters=["A", "B"])
        block = series_context_block(ctx)
        assert "X" in block
        assert "A、B" in block
        # 题材未填 → 不应有"题材：" 行
        assert "题材：" not in block
        # 总集数=0 → 不应有"总集数：" 行
        assert "总集数：" not in block


# ============================================================================
# Phase I: ScriptGenerator.generate / generate_monologue
# ============================================================================


class TestScriptGeneratorStrategyPassThrough:
    def test_generate_accepts_multi_strategy(self):
        """generate() 应把 multi_strategy / series_context 透传给 build_prompt。"""
        gen = ScriptGenerator(use_llm_manager=False, api_key="dummy-key")
        captured: dict = {}

        def fake_generate_openai(
            topic, cfg, *, multi_strategy=None, series_context=None
        ):
            captured["multi_strategy"] = multi_strategy
            captured["series_context"] = series_context
            # 模拟 _generate_openai 内部调用 build_prompt 的事实
            from app.services.ai.script_generator._prompt_builder import build_prompt

            build_prompt(
                topic, cfg, multi_strategy=multi_strategy, series_context=series_context
            )
            return "ok"

        with patch.object(gen, "_generate_openai", side_effect=fake_generate_openai):
            gen.generate("t", ScriptConfig(), multi_strategy="series")

        assert captured.get("multi_strategy") == "series"

    def test_generate_monologue_signature(self):
        """generate_monologue 接受 multi_strategy + series_context 关键字参数。"""
        gen = ScriptGenerator(use_llm_manager=False, api_key="dummy-key")
        with patch.object(gen, "generate", return_value=None) as mock_gen:
            gen.generate_monologue(
                context="ctx",
                emotion="惆怅",
                duration=30.0,
                multi_strategy="series",
                series_context=SeriesContext(series_title="X"),
            )
            # kwargs 应被原样透传
            kwargs = mock_gen.call_args.kwargs
            assert kwargs["multi_strategy"] == "series"
            assert kwargs["series_context"].series_title == "X"

    def test_generate_monologue_backward_compat(self):
        """不传新参数时也能正常工作（v2.4 路径）。"""
        gen = ScriptGenerator(use_llm_manager=False, api_key="dummy-key")
        with patch.object(gen, "generate", return_value=None) as mock_gen:
            gen.generate_monologue("ctx", "惆怅", 30.0)
            kwargs = mock_gen.call_args.kwargs
            assert kwargs["multi_strategy"] is None
            assert kwargs["series_context"] is None


# ============================================================================
# Phase K: compute_adaptive_parallel + create_batch
# ============================================================================


class TestComputeAdaptiveParallel:
    @pytest.mark.parametrize(
        "n_tasks,expected",
        [
            (0, 1),
            (1, 1),
            (2, 2),
            (3, 3),
        ],
    )
    def test_small_task_sets(self, n_tasks, expected):
        assert compute_adaptive_parallel(n_tasks) == expected

    def test_large_task_set_clamped_to_max_parallel(self):
        """任务数超过 max_parallel 时，取 max(max_parallel, n_tasks) 不超 2x。"""
        cpu = os.cpu_count() or 1
        max_parallel = max(1, cpu * 2)
        result = compute_adaptive_parallel(1000, max_parallel=max_parallel)
        assert result <= max_parallel * 2

    def test_explicit_max_parallel(self):
        """显式 max_parallel 应控制上限 (cap = max_parallel * 2)。"""
        # n_tasks >> max_parallel：实际并发度 = max_parallel * 2
        assert compute_adaptive_parallel(50, max_parallel=4) == 8
        # n_tasks 较少：实际并发度 = n_tasks
        assert compute_adaptive_parallel(2, max_parallel=4) == 2
        # n_tasks == max_parallel：实际并发度 = n_tasks
        assert compute_adaptive_parallel(4, max_parallel=4) == 4

    def test_max_parallel_none_default(self):
        """max_parallel=None → 走 os.cpu_count() 自适应。"""
        # 至少不抛错，且 >= 1
        result = compute_adaptive_parallel(5, max_parallel=None)
        assert result >= 1


class TestCreateBatchAdaptiveParallel:
    def test_default_parallel_uses_cpu_adaptive(self, fake_video_dir):
        """create_batch 不传 parallel 时走自适应，而不是写死 2。"""
        paths = _paths(fake_video_dir)
        maker = MonologueMaker()
        # 拦截：检查是否走 compute_adaptive_parallel
        with patch(
            "app.services.video.monologue_maker.compute_adaptive_parallel",
            wraps=compute_adaptive_parallel,
        ) as spy:
            maker.create_batch(sources=paths, context="X")
        assert spy.called

    def test_explicit_parallel_clamps_to_max(self, fake_video_dir):
        """显式 parallel=9999 应被 clamp 到 max_parallel。"""
        paths = _paths(fake_video_dir, names=("a.mp4", "b.mp4"))
        maker = MonologueMaker()
        # 不抛错即可
        projects = maker.create_batch(
            sources=paths, context="X", parallel=9999)
        assert len(projects) >= 1

    def test_series_strategy_propagates_series_context(self, fake_video_dir):
        """series 策略 + SeriesContext → 每个子项目都携带 series_context。"""
        paths = _paths(fake_video_dir, names=("a.mp4", "b.mp4"))
        mvs = MultiVideoSource(
            strategy="series",
            series_context=SeriesContext(series_title="深夜短剧"),
        )
        mvs.add_many(paths)
        maker = MonologueMaker()
        projects = maker.create_batch(sources=mvs, context="X")
        assert all(p.series_context is not None for p in projects)
        assert all(p.series_context.series_title == "深夜短剧" for p in projects)

    def test_series_strategy_uses_episode_naming_template(self, fake_video_dir):
        """series 策略 + 非空 episode_naming → 项目名按模板渲染。"""
        paths = _paths(fake_video_dir, names=("a.mp4", "b.mp4", "c.mp4"))
        mvs = MultiVideoSource(
            strategy="series",
            series_context=SeriesContext(
                series_title="深夜短剧",
                episode_naming="{title}_EP{ep:02d}",
            ),
        )
        mvs.add_many(paths)
        maker = MonologueMaker()
        projects = maker.create_batch(sources=mvs, context="X")
        names = [p.name for p in projects]
        assert "深夜短剧_EP01" in names
        assert "深夜短剧_EP02" in names
        assert "深夜短剧_EP03" in names

    def test_non_series_strategy_keeps_legacy_naming(self, fake_video_dir):
        """非 series 策略仍走旧的 ``{name_prefix}{idx:02d}_{stem}``。"""
        paths = _paths(fake_video_dir, names=("a.mp4", "b.mp4"))
        mvs = MultiVideoSource(
            strategy="batch",
            series_context=SeriesContext(
                series_title="深夜短剧",
                episode_naming="{title}_EP{ep:02d}",
            ),
        )
        mvs.add_many(paths)
        maker = MonologueMaker()
        projects = maker.create_batch(
            sources=mvs, context="X", name_prefix="EP")
        names = [p.name for p in projects]
        assert "EP01_a" in names
        assert "EP02_b" in names
        # 不应被模板污染
        assert "深夜短剧_EP" not in " ".join(names)


# ============================================================================
# Phase J 收尾：_format_episode_name 模板渲染
# ============================================================================


class TestFormatEpisodeName:
    """``_format_episode_name`` 单集命名模板渲染。"""

    def test_default_template(self):
        """默认模板 ``{title}_EP{ep:02d}`` 正常渲染。"""
        assert (
            _format_episode_name("{title}_EP{ep:02d}",
                                 title="深夜短剧", ep=1, stem="a")
            == "深夜短剧_EP01"
        )

    def test_custom_template(self):
        """自定义模板 ``EP{ep:02d}_{title}`` 反转顺序。"""
        assert (
            _format_episode_name(
                "EP{ep:02d}_{title}", title="深夜短剧", ep=12, stem="a"
            )
            == "EP12_深夜短剧"
        )

    def test_includes_stem_placeholder(self):
        """模板里的 ``{stem}`` 占位符。"""
        assert (
            _format_episode_name(
                "{title}_{stem}_EP{ep:02d}",
                title="X",
                ep=3,
                stem="clip01",
            )
            == "X_clip01_EP03"
        )

    def test_empty_template_falls_back(self):
        """空模板 → 回退到 ``{stem}_EP{ep:02d}``。"""
        assert _format_episode_name(
            "", title="X", ep=5, stem="clip") == "clip_EP05"

    def test_broken_template_falls_back(self):
        """模板里有未定义占位符 → 安全回退，不抛错。"""
        result = _format_episode_name(
            "{title}_{unknown_field}", title="X", ep=2, stem="c"
        )
        assert result == "c_EP02"

    def test_rendered_empty_falls_back(self):
        """模板渲染后为空字符串(例如 ``{}``)→ 回退。"""
        assert _format_episode_name(
            "{}", title="X", ep=2, stem="c") == "c_EP02"


# ============================================================================
# Phase M + O: STRATEGY_INSTRUCTIONS 快照与错误降级
# ============================================================================


class TestStrategyPromptSnapshots:
    """锁定 ``STRATEGY_INSTRUCTIONS`` 的关键短语与覆盖范围。

    防止后续修改无意删除或重写各策略的核心指引。这是 v2.5.0
    系列功能稳定运行的“防漂移”屏障。
    """

    def test_all_four_strategies_present(self):
        """STRATEGY_INSTRUCTIONS 必须覆盖 single / concat / batch / series。"""
        assert set(STRATEGY_INSTRUCTIONS.keys()) == {
            "single",
            "concat",
            "batch",
            "series",
        }

    def test_single_snapshot(self):
        """单视频场景：含明确“单视频场景”标语。"""
        assert "单视频场景" in STRATEGY_INSTRUCTIONS["single"]
        assert "单一原始视频" in STRATEGY_INSTRUCTIONS["single"]

    def test_concat_snapshot(self):
        """拼接场景：提到“拼接”与“过渡”。"""
        text = STRATEGY_INSTRUCTIONS["concat"]
        assert "拼接场景" in text
        assert "拼接" in text
        assert "过渡" in text

    def test_batch_snapshot(self):
        """批量独立场景：强调“独立”与“不依赖”。"""
        text = STRATEGY_INSTRUCTIONS["batch"]
        assert "批量独立场景" in text
        assert "独立" in text

    def test_series_snapshot(self):
        """整季系列场景：强调“系列” / “人物名称” / “世界观”。"""
        text = STRATEGY_INSTRUCTIONS["series"]
        assert "整季系列场景" in text
        assert "人物名称" in text
        assert "世界观" in text

    def test_no_empty_prompt(self):
        """不允许任何一个策略的提示词为空字符串或仅换行。"""
        for key, text in STRATEGY_INSTRUCTIONS.items():
            stripped = text.strip()
            assert stripped, f"策略 {key} 的提示词为空"

    def test_prompts_have_marker_header(self):
        """提示词必须以【xxx场景】开头，LLM 才能识别场景类型。"""
        for key in ("single", "concat", "batch", "series"):
            assert "【" in STRATEGY_INSTRUCTIONS[key]
            assert "场景】" in STRATEGY_INSTRUCTIONS[key]


class TestStrategyErrorFallback:
    """传入未知 / 为空的 ``multi_strategy`` 不能踩坏 prompt。"""

    def test_unknown_strategy_does_not_inject(self):
        """未注册的 strategy 走 silent skip，不注入到 prompt。"""
        cfg = ScriptConfig(target_duration=10.0)
        out = build_prompt(topic="demo", config=cfg, multi_strategy="type")
        assert "【单视频场景】" not in out
        assert "【拼接场景】" not in out
        assert "【整季系列场景】" not in out

    def test_empty_strategy_does_not_inject(self):
        """空字符串走 silent skip。"""
        cfg = ScriptConfig(target_duration=10.0)
        out = build_prompt(topic="demo", config=cfg, multi_strategy="")
        assert "【单视频场景】" not in out

    def test_series_strategy_without_context_does_not_inject_block(self):
        """series 策略但 series_context 为 None → 不注入【系列背景（v2.5.0）】块。"""
        cfg = ScriptConfig(target_duration=10.0)
        out = build_prompt(
            topic="demo", config=cfg, multi_strategy="series", series_context=None
        )
        # series 提示词本身会注入（含裸【系列背景】引用）
        assert "【整季系列场景】" in out
        # 但 SeriesContext 渲染块不出现（v2.5.0 标记的版本头）
        assert "【系列背景（v2.5.0）】" not in out


# ============================================================================
# Phase L 收尾：SeriesContext.from_dict 往返
# ============================================================================


class TestSeriesContextFromDict:
    """``SeriesContext.from_dict`` 重复 from_json 场景。"""

    def test_round_trip(self):
        """to_dict → from_dict → 字段一致。"""
        original = SeriesContext(
            series_title="深夜短剧",
            episode_naming="{title}_EP{ep:02d}",
            shared_characters=["小志", "阿娇"],
            shared_plot="凌晨 3 点的便利店故事",
            world_setting="都市 / 雾夜",
            genre="悬疑",
            total_episodes=24,
        )
        restored = SeriesContext.from_dict(original.to_dict())
        assert restored.series_title == original.series_title
        assert restored.episode_naming == original.episode_naming
        assert restored.shared_characters == original.shared_characters
        assert restored.shared_plot == original.shared_plot
        assert restored.world_setting == original.world_setting
        assert restored.genre == original.genre
        assert restored.total_episodes == original.total_episodes

    def test_empty_dict_returns_default(self):
        """空字典 → 默认值实例。"""
        restored = SeriesContext.from_dict({})
        assert restored.series_title == ""
        assert restored.episode_naming == "{title}_EP{ep:02d}"
        assert restored.shared_characters == []
        assert restored.total_episodes == 0

    def test_non_dict_returns_default(self):
        """非 dict 输入 → 默认值实例，不抛错。"""
        assert SeriesContext.from_dict(
            None).series_title == ""  # type: ignore[arg-type]
        assert SeriesContext.from_dict(
            "xx").series_title == ""  # type: ignore[arg-type]
        assert SeriesContext.from_dict(
            42).series_title == ""  # type: ignore[arg-type]

    def test_broken_types_safely_fall_back(self):
        """字段类型错误（如 total_episodes 为字符串）→ 默认实例。"""
        restored = SeriesContext.from_dict(
            {"total_episodes": "not_a_number", "shared_characters": "not_a_list"}
        )
        assert restored.total_episodes == 0
        assert restored.shared_characters == []


# ============================================================================
# Phase J: SeriesContextDialog form round-trip
# ============================================================================


@pytest.fixture(scope="module")
def qt_app():
    """Headless QApplication for QDialog tests."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestSeriesContextDialog:
    def test_result_ctx_round_trip(self, qt_app):
        """填表 + OK → result_ctx() 返回填入的数据。"""
        from app.ui.main.dialogs.series_context_dialog import (
            SeriesContextDialog,
        )

        dlg = SeriesContextDialog()
        dlg._title_edit.setText("深夜短剧")
        dlg._naming_edit.setText("{title}_EP{ep:03d}")
        dlg._genre_edit.setText("都市")
        dlg._eps_spin.setValue(20)
        dlg._chars_edit.setPlainText("女主\n男主\n反派")
        dlg._plot_edit.setPlainText("一段跨越二十年的爱情")
        dlg._world_edit.setPlainText("现代都市")

        ctx = dlg.result_ctx()
        assert ctx.series_title == "深夜短剧"
        assert ctx.episode_naming == "{title}_EP{ep:03d}"
        assert ctx.genre == "都市"
        assert ctx.total_episodes == 20
        assert ctx.shared_characters == ["女主", "男主", "反派"]
        assert ctx.shared_plot == "一段跨越二十年的爱情"
        assert ctx.world_setting == "现代都市"
        dlg.deleteLater()

    def test_default_naming_when_empty(self, qt_app):
        """命名模板留空 → result 应回退到默认 ``{title}_EP{ep:02d}``。"""
        from app.ui.main.dialogs.series_context_dialog import (
            SeriesContextDialog,
        )

        dlg = SeriesContextDialog()
        dlg._naming_edit.setText("")
        ctx = dlg.result_ctx()
        assert ctx.episode_naming == "{title}_EP{ep:02d}"
        dlg.deleteLater()

    def test_characters_dedup_and_strip(self, qt_app):
        """共享人物：去重 + strip 空行 + 跳过空名。"""
        from app.ui.main.dialogs.series_context_dialog import (
            SeriesContextDialog,
        )

        dlg = SeriesContextDialog()
        dlg._chars_edit.setPlainText(" 女主 \n\n男主\n女主\n  ")
        ctx = dlg.result_ctx()
        assert ctx.shared_characters == ["女主", "男主"]
        dlg.deleteLater()

    def test_initial_populates_fields(self, qt_app):
        """initial=SeriesContext(...) → 表单被预填。"""
        from app.ui.main.dialogs.series_context_dialog import (
            SeriesContextDialog,
        )

        initial = SeriesContext(
            series_title="已存在剧名",
            episode_naming="{title}_{ep:02d}",
            shared_characters=["A", "B"],
            shared_plot="已存在主线",
            world_setting="已存在世界观",
            genre="甜宠",
            total_episodes=10,
        )
        dlg = SeriesContextDialog(initial=initial)
        assert dlg._title_edit.text() == "已存在剧名"
        assert dlg._naming_edit.text() == "{title}_{ep:02d}"
        assert dlg._genre_edit.text() == "甜宠"
        assert dlg._eps_spin.value() == 10
        assert dlg._chars_edit.toPlainText() == "A\nB"
        assert dlg._plot_edit.toPlainText() == "已存在主线"
        dlg.deleteLater()

    def test_reset_button_clears_form(self, qt_app):
        """点 reset → 表单全部回到默认空值。"""
        from app.ui.main.dialogs.series_context_dialog import (
            SeriesContextDialog,
        )

        dlg = SeriesContextDialog()
        # 填一些值
        dlg._title_edit.setText("临时剧名")
        dlg._naming_edit.setText("CUSTOM_{ep}")
        dlg._genre_edit.setText("甜宠")
        dlg._eps_spin.setValue(20)
        dlg._chars_edit.setPlainText("A\nB")
        dlg._plot_edit.setPlainText("临时剧情")
        dlg._world_edit.setPlainText("临时世界")

        # 触发 reset
        dlg._on_reset_clicked()

        assert dlg._title_edit.text() == ""
        assert dlg._naming_edit.text() == "{title}_EP{ep:02d}"
        assert dlg._genre_edit.text() == ""
        assert dlg._eps_spin.value() == 0
        assert dlg._chars_edit.toPlainText() == ""
        assert dlg._plot_edit.toPlainText() == ""
        assert dlg._world_edit.toPlainText() == ""
        # reset 后 result_ctx 给出空默认实例
        ctx = dlg.result_ctx()
        assert ctx.series_title == ""
        assert ctx.shared_characters == []
        assert ctx.total_episodes == 0
        dlg.deleteLater()


# ============================================================================
# Phase I+J: monologue_maker.generate_script 集成 multi_strategy + series
# ============================================================================


class TestMonologueMakerGenerateScript:
    def test_generate_script_passes_strategy_and_context(self, fake_video_dir):
        """MonologueMaker.generate_script 应把 multi_strategy+series_context 透传。"""
        paths = _paths(fake_video_dir, names=("a.mp4",))
        maker = MonologueMaker()
        project = maker.create_project(
            source_video=paths[0],
            source_videos=paths,
            multi_strategy="series",
            series_context=SeriesContext(series_title="深夜短剧"),
            context="X",
        )

        captured: dict = {}

        def fake_gen_monologue(context, emotion="neutral", duration=30.0, **kw):
            captured.update(kw)
            from app.services.ai.script_generator import GeneratedScript

            return GeneratedScript(content="fake script")

        with patch.object(
            maker.script_generator,
            "generate_monologue",
            side_effect=fake_gen_monologue,
        ):
            maker.generate_script(project)

        assert captured.get("multi_strategy") == "series"
        assert captured.get("series_context") is not None
        assert captured["series_context"].series_title == "深夜短剧"
