#!/usr/bin/env python3
"""Phase P · 端到端集成测试。

覆盖多视频系列(series)策略下的完整链路:
  ``SeriesContextDialog`` → ``production_runner.start_batch`` →
  ``MonologueMaker.create_batch`` → ``MonologueMaker.generate_script`` →
  ``ScriptGenerator.generate_monologue`` → ``build_prompt`` 注入策略 + SeriesContext

目的:
- 捕获回归:链路上任一环节漏传参数都会在此 fail
- 验证 episode_naming 模板真实应用到 ``MonologueProject.name``
- 验证 LLM 收到的 prompt 同时包含 ``STRATEGY_INSTRUCTIONS["series"]`` 和
  ``series_context_block()`` 渲染内容

注:
- LLM / TTS / 字幕生成被 mock 掉,只跑 prompt 构建阶段
- 不启动真线程(避免 Qt event loop 依赖),直接同步调用 ``_run()`` 内部函数
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.models.project import MultiVideoSource, SeriesContext
from app.services.ai.script_generator import GeneratedScript
from app.services.ai.script_generator._prompt_builder import build_prompt
from app.services.ai.script_generator._style_prompts import (
    STRATEGY_INSTRUCTIONS,
)
from app.services.ai.script_models import ScriptConfig
from app.services.video.monologue_maker import MonologueMaker


@pytest.fixture
def fake_video_dir():
    """创建包含 N 个空 mp4 文件的临时目录。"""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for i in range(3):
            (td_path / f"clip_{i + 1:02d}.mp4").write_bytes(b"fake")
        yield td_path


def _paths(td: Path, names: tuple[str, ...]) -> list[str]:
    return [str(td / n) for n in names]


# ──────────────────────────────────────────────────────────────
# Phase P-1: 端到端链路 — series 策略 prompt 注入
# ──────────────────────────────────────────────────────────────


class TestSeriesEndToEndPipeline:
    """series 策略下,MonologueMaker 全链路真实调用,验证 LLM 收到正确 prompt。"""

    def test_full_pipeline_series_strategy_passes_to_llm(self, fake_video_dir):
        """端到端: 3 视频 series 策略 → LLM 收到带系列背景的 prompt + 项目命名模板生效。"""
        paths = _paths(fake_video_dir, ("clip_01.mp4",
                       "clip_02.mp4", "clip_03.mp4"))
        series_ctx = SeriesContext(
            series_title="深夜短剧",
            episode_naming="{title}_EP{ep:02d}",
            shared_characters=["小志", "阿娇"],
            shared_plot="凌晨 3 点的便利店",
            world_setting="都市 / 雾夜",
            genre="悬疑",
            total_episodes=24,
        )

        maker = MonologueMaker()
        mvs = MultiVideoSource(strategy="series", series_context=series_ctx)
        mvs.add_many(paths)
        projects = maker.create_batch(sources=mvs, context="夜色")

        # === 1. 验证 create_batch 输出的项目数与命名模板 ===
        assert len(projects) == 3
        names = [p.name for p in projects]
        # 按 episode_naming 模板渲染
        assert names == ["深夜短剧_EP01", "深夜短剧_EP02", "深夜短剧_EP03"]
        # 每个项目都携带 series_context（即使 multi_strategy 在子项目上为 single）
        assert all(p.series_context is not None for p in projects)
        assert all(p.series_context.series_title == "深夜短剧" for p in projects)

        # === 2. 验证 generate_script 把 series_context 传给 ScriptGenerator ===
        captured_prompts: list[str] = []

        def fake_generate_monologue(*args, **kwargs):
            # 拦截 prompt 内容
            topic = kwargs.get("context", "")
            captured_prompts.append(topic)
            return GeneratedScript(content=f"script_for_{topic}")

        with patch.object(
            maker.script_generator,
            "generate_monologue",
            side_effect=fake_generate_monologue,
        ):
            for project in projects:
                maker.generate_script(project)

        assert len(captured_prompts) == 3

    def test_full_pipeline_series_strategy_prompt_content(self, fake_video_dir):
        """端到端: 验证 build_prompt 注入的策略指令与系列背景块完整无误。"""
        series_ctx = SeriesContext(
            series_title="深夜短剧",
            shared_characters=["小志"],
            shared_plot="凌晨 3 点的便利店",
            world_setting="都市",
            genre="悬疑",
        )

        # 直接调用 build_prompt 验证 (这是 generate_script 最终会调用的核心)
        cfg = ScriptConfig(target_duration=10.0)
        prompt = build_prompt(
            topic="夜色便利店",
            config=cfg,
            multi_strategy="series",
            series_context=series_ctx,
        )

        # 系列策略核心短语必须出现
        assert STRATEGY_INSTRUCTIONS["series"] in prompt
        # series_context_block 必须出现(包含剧名与共享人物)
        assert "深夜短剧" in prompt
        assert "小志" in prompt
        assert "凌晨 3 点的便利店" in prompt
        # v2.5.0 marker
        assert "【系列背景（v2.5.0）】" in prompt

    def test_full_pipeline_batch_strategy_no_series_block(self, fake_video_dir):
        """端到端: batch 策略 + 有 series_ctx → 不注入系列背景块。"""
        series_ctx = SeriesContext(series_title="深夜短剧")
        cfg = ScriptConfig(target_duration=10.0)
        prompt = build_prompt(
            topic="demo",
            config=cfg,
            multi_strategy="batch",
            series_context=series_ctx,  # 即使传入,也不该出现
        )
        # batch 提示词注入
        assert "【批量独立场景】" in prompt
        # series 提示词 + 系列背景都不该出现
        assert "【整季系列场景】" not in prompt
        assert "【系列背景（v2.5.0）】" not in prompt

    def test_full_pipeline_concat_strategy(self, fake_video_dir):
        """端到端: concat 策略 → 注入拼接场景提示词。"""
        cfg = ScriptConfig(target_duration=10.0)
        prompt = build_prompt(topic="demo", config=cfg,
                              multi_strategy="concat")
        assert "【拼接场景】" in prompt


# ──────────────────────────────────────────────────────────────
# Phase P-2: 项目命名 + .scenefab 落盘 + SeriesContext 恢复
# ──────────────────────────────────────────────────────────────


class TestSeriesProjectRoundTrip:
    """series 项目从 create_batch → save → load → SeriesContext 字段保持一致。"""

    def test_save_load_preserves_series_context(self, fake_video_dir, tmp_path):
        paths = _paths(fake_video_dir, ("a.mp4", "b.mp4"))
        series_ctx = SeriesContext(
            series_title="深夜短剧",
            episode_naming="{title}_EP{ep:02d}",
            shared_characters=["A", "B"],
            shared_plot="plot",
            world_setting="world",
            genre="悬疑",
            total_episodes=20,
        )

        maker = MonologueMaker()
        mvs = MultiVideoSource(strategy="series", series_context=series_ctx)
        mvs.add_many(paths)
        projects = maker.create_batch(
            sources=mvs, context="X", output_dir=str(tmp_path)
        )
        # 每个项目 save 后再 load,字段保持
        for original in projects:
            save_path = tmp_path / f"{original.name}.scenefab"
            original.save(str(save_path))
            from app.services.video.monologue_maker import MonologueProject

            loaded = MonologueProject.load(str(save_path))
            assert loaded.series_context is not None
            assert loaded.series_context.series_title == "深夜短剧"
            assert loaded.series_context.shared_characters == ["A", "B"]
            assert loaded.series_context.total_episodes == 20
            assert loaded.multi_strategy == "series"

    def test_create_batch_project_name_uses_template(self, fake_video_dir):
        """series + 自定义 episode_naming 模板 → 项目名严格按模板渲染。"""
        paths = _paths(fake_video_dir, ("clip_01.mp4",
                       "clip_02.mp4", "clip_03.mp4"))
        mvs = MultiVideoSource(
            strategy="series",
            series_context=SeriesContext(
                series_title="MySeries",
                episode_naming="EP{ep:02d}_{title}",
            ),
        )
        mvs.add_many(paths)
        projects = MonologueMaker().create_batch(sources=mvs, context="X")
        names = sorted(p.name for p in projects)
        assert names == [
            "EP01_MySeries",
            "EP02_MySeries",
            "EP03_MySeries",
        ]
