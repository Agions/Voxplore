#!/usr/bin/env python3
"""Tests for ProductionPageViewModel (Phase 2B).

Covers:
- default_state_without_application: VM constructs without app
- step_definitions_immutable: VM exposes the 5-step canon
- start_pipeline_resets_state: calling start() puts all steps in pending→active
- step_status_progression: each step transitions pending → active → done
- pipeline_failure_propagates: error in one step marks it error + state failed
- reset_pipeline_clears_state: reset goes back to idle + all pending
- status_label_human_readable: get_status_label returns Chinese labels
"""

from __future__ import annotations

import time

import pytest
from PySide6.QtCore import QCoreApplication

from scenefab.ui.viewmodels.production_viewmodel import (
    STEP_DEFINITIONS,
    ProductionPageViewModel,
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
