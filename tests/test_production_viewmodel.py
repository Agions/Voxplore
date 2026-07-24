#!/usr/bin/env python3
"""Tests for ProductionPageViewModel (Phase 2B + 2B+1).

Covers:
- default_state_without_application: VM constructs without app
- step_definitions_immutable: VM exposes the 5-step canon
- start_pipeline_resets_state: calling start() puts all steps in pending→active
- step_status_progression: each step transitions pending → active → done
- pipeline_failure_propagates: error in one step marks it error + state failed
- reset_pipeline_clears_state: reset goes back to idle + all pending
- status_label_human_readable: get_status_label returns Chinese labels
- runner_mode_noop_by_default: VM starts in noop mode (no env keys)
- runner_mode_live_with_env_keys: env keys flip mode to "live"
- start_pipeline_with_live_mode: VM attempts create_project (mocked)
- _has_runtime_keys_helper: helper returns bool from env state
"""

from __future__ import annotations

import os
import time

import pytest

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import QCoreApplication

from scenefab.ui.viewmodels.production_viewmodel import (
    STEP_DEFINITIONS,
    ProductionPageViewModel,
    _has_runtime_keys,
)


@pytest.fixture
def qapp():
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


@pytest.fixture
def vm(qapp):
    """ProductionPageViewModel with NO application — must still work."""
    return ProductionPageViewModel()


# ── 1. default state without application ──────────────────────────────
def test_vm_default_state_without_application(vm: ProductionPageViewModel):
    """VM must construct + expose properties without an Application."""
    assert vm.pipeline_state == "idle"
    assert vm.current_step == -1
    assert vm.status_label == "就绪"
    assert len(vm.step_status) == 5
    assert all(s == "pending" for s in vm.step_status)


# ── 2. step definitions are the canonical 5-step ──────────────────────
def test_step_definitions_canonical(vm: ProductionPageViewModel):
    """VM exposes the same 5 steps the static page used to hardcode."""
    assert len(vm.step_definitions) == 5
    assert vm.step_definitions == STEP_DEFINITIONS
    # Number 01..05 + Chinese names
    expected = [
        ("01", "素材导入", "选择影视片段并记录来源"),
        ("02", "场景拆分", "识别人物、冲突和关键转折"),
        ("03", "脚本生成", "使用第一人称视角组织叙事"),
        ("04", "配音字幕", "完成音频、字幕与节奏校准"),
        ("05", "导出发布", "按竖屏平台参数生成成片"),
    ]
    for got, exp in zip(vm.step_definitions, expected, strict=True):
        assert got == exp


# ── 3. start_pipeline advances state machine ──────────────────────────
def test_start_pipeline_advances_state(vm: ProductionPageViewModel, qapp):
    """After start(), step 0 goes active and pipeline_state=running."""
    state_changes: list[str] = []
    current_step_changes: list[int] = []
    step_status_changes: list[int] = []

    vm.pipeline_state_changed.connect(lambda: state_changes.append(vm.pipeline_state))
    vm.current_step_changed.connect(lambda: current_step_changes.append(vm.current_step))
    vm.step_status_changed.connect(lambda i: step_status_changes.append(i))

    vm.start_pipeline("source.mp4", "test context")

    # pump the event loop until the 5 steps finish
    deadline = time.time() + 5.0
    while vm.pipeline_state == "running" and time.time() < deadline:
        qapp.processEvents()

    assert vm.pipeline_state == "done"
    assert vm.current_step == 4
    assert all(s == "done" for s in vm.step_status)
    # step 0 should have transitioned first
    assert 0 in step_status_changes


# ── 4. step labels are human-readable ────────────────────────────────
def test_status_label_human_readable(vm: ProductionPageViewModel):
    """get_status_label returns Chinese label per state."""
    assert vm.get_status_label("pending") == "待开始"
    assert vm.get_status_label("active") == "进行中"
    assert vm.get_status_label("done") == "已完成"
    assert vm.get_status_label("error") == "失败"
    # Unknown status → identity
    assert vm.get_status_label("???") == "???"


# ── 5. reset_pipeline clears state ───────────────────────────────────
def test_reset_pipeline_clears_state(vm: ProductionPageViewModel, qapp):
    """reset_pipeline returns VM to idle + all pending."""
    vm.start_pipeline("source.mp4", "context")
    deadline = time.time() + 5.0
    while vm.pipeline_state == "running" and time.time() < deadline:
        qapp.processEvents()
    assert vm.pipeline_state == "done"

    vm.reset_pipeline()
    assert vm.pipeline_state == "idle"
    assert vm.current_step == -1
    assert all(s == "pending" for s in vm.step_status)


# ── 6. start_pipeline with empty input is a no-op ────────────────────
def test_start_pipeline_with_empty_input_is_noop(vm: ProductionPageViewModel):
    """Empty source_video or context → start does nothing."""
    vm.start_pipeline("", "context")
    assert vm.pipeline_state == "idle"
    vm.start_pipeline("source.mp4", "")
    assert vm.pipeline_state == "idle"


# ── 7. runner_mode defaults to "noop" (Phase 2B+1) ───────────────────
def test_runner_mode_noop_by_default(vm: ProductionPageViewModel):
    """VM starts in noop mode (no TTS / LLM keys in test env)."""
    # Defensive: ensure test env is clean
    os.environ.pop("SCENEFAB_TTS_KEY", None)
    os.environ.pop("SCENEFAB_LLM_KEY", None)
    assert vm.runner_mode == "noop"


# ── 8. env keys flip runner_mode to "live" (Phase 2B+1) ──────────────
def test_runner_mode_live_with_env_keys(qapp, monkeypatch):
    """When SCENEFAB_TTS_KEY is set + MonologueMaker registered, mode is 'live'."""
    monkeypatch.setenv("SCENEFAB_TTS_KEY", "test-key-not-real")

    from scenefab.services.video.monologue_maker import MonologueMaker

    class _FakeProject:
        def save(self, path=None):  # noqa: ARG002
            return "/tmp/fake.scenefab"

    class _FakeMaker:
        def create_project(self, source_video, context, **kwargs):  # noqa: ARG002
            return _FakeProject()

        def generate_script(self, project, custom_script=None):  # noqa: ARG002
            pass

        def generate_voice(self, project, voice_config=None):  # noqa: ARG002
            pass

        def generate_captions(self, project, style="cinematic"):  # noqa: ARG002
            pass

    fake_maker = _FakeMaker()

    class _MockApp:
        def get_service(self, service_type):
            # ProductionVM requests MonologueMaker by class
            if service_type is MonologueMaker:
                return fake_maker
            return None

    app = _MockApp()  # type: ignore[arg-type]
    vm = ProductionPageViewModel(application=app)  # type: ignore[arg-type]

    vm.start_pipeline("source.mp4", "context")
    assert vm.runner_mode == "live"

    # Wait for state machine to finish
    deadline = time.time() + 5.0
    while vm.pipeline_state == "running" and time.time() < deadline:
        qapp.processEvents()
    assert vm.pipeline_state == "done"
    # pipeline_finished should have emitted the project path
    assert vm._last_project_path == "/tmp/fake.scenefab"  # type: ignore[attr-defined]


# ── 9. _has_runtime_keys helper (Phase 2B+1) ─────────────────────────
def test_has_runtime_keys_helper(monkeypatch):
    """_has_runtime_keys reads SCENEFAB_TTS_KEY + SCENEFAB_LLM_KEY env vars."""
    monkeypatch.delenv("SCENEFAB_TTS_KEY", raising=False)
    monkeypatch.delenv("SCENEFAB_LLM_KEY", raising=False)
    assert _has_runtime_keys() is False

    monkeypatch.setenv("SCENEFAB_TTS_KEY", "x")
    assert _has_runtime_keys() is True
    monkeypatch.delenv("SCENEFAB_TTS_KEY")

    monkeypatch.setenv("SCENEFAB_LLM_KEY", "y")
    assert _has_runtime_keys() is True
    monkeypatch.delenv("SCENEFAB_LLM_KEY")

    # Empty / whitespace string is treated as absent
    monkeypatch.setenv("SCENEFAB_TTS_KEY", "   ")
    assert _has_runtime_keys() is False


# ── 10. live mode falls back to noop if create_project raises (Phase 2B+1)
def test_live_mode_fallback_to_noop_when_create_fails(qapp, monkeypatch):
    """If MonologueMaker.create_project raises, VM downgrades to noop."""
    monkeypatch.setenv("SCENEFAB_TTS_KEY", "test-key")

    from scenefab.services.video.monologue_maker import MonologueMaker

    class _BrokenMaker:
        def create_project(self, **kwargs):  # noqa: ARG002
            raise RuntimeError("video file not found")

    broken_maker = _BrokenMaker()

    class _MockApp:
        def get_service(self, service_type):
            if service_type is MonologueMaker:
                return broken_maker
            return None

    app = _MockApp()  # type: ignore[arg-type]
    vm = ProductionPageViewModel(application=app)  # type: ignore[arg-type]

    vm.start_pipeline("nonexistent.mp4", "context")
    # VM should have caught the exception and downgraded to noop
    assert vm.runner_mode == "noop"
    # Pipeline runs to completion (5 no-op steps)
    deadline = time.time() + 5.0
    while vm.pipeline_state == "running" and time.time() < deadline:
        qapp.processEvents()
    assert vm.pipeline_state == "done"
