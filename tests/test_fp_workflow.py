#!/usr/bin/env python3
"""Tests for reusable first-person narration workflow definitions."""

from scenefab.pipeline.fp_workflow import (
    FIRST_PERSON_QUALITY_GATES,
    FIRST_PERSON_SCRIPT_RULES,
    FIRST_PERSON_WORKFLOW,
    build_first_person_system_prompt,
    numbered_workflow,
    validate_first_person_script,
)
from scenefab.ui.main.pages.page_view_models import (
    EXPORT_QUALITY_CHECKS,
    PRODUCTION_STEPS,
    SCRIPT_BRIEF_RULES,
)


def test_first_person_workflow_has_stable_order():
    numbered = numbered_workflow()

    assert numbered[0][0] == "01"
    assert numbered[0][1].id == "source_review"
    assert numbered[-1][0] == "06"
    assert numbered[-1][1].id == "publish_review"


def test_ui_production_steps_are_derived_from_workflow():
    assert [step.name for step in PRODUCTION_STEPS] == [
        stage.title for stage in FIRST_PERSON_WORKFLOW
    ]


def test_ui_quality_rules_are_derived_from_workflow():
    assert [rule.label for rule in SCRIPT_BRIEF_RULES] == [
        rule.label for rule in FIRST_PERSON_SCRIPT_RULES
    ]
    assert EXPORT_QUALITY_CHECKS[: len(FIRST_PERSON_QUALITY_GATES)] == (
        FIRST_PERSON_QUALITY_GATES
    )


def test_validate_first_person_script_valid():
    valid_script = "我没想到自己居然陷入了这场蓄谋已久的危机。我紧握着拳头，发誓一定要让他们付出代价！"
    violations = validate_first_person_script(valid_script)
    assert len(violations) == 0


def test_validate_first_person_script_detects_third_person_leak():
    invalid_script = "只见男主走进了房间，旁白说道他要开始复仇。"
    violations = validate_first_person_script(invalid_script)
    assert any("第一人称主语" in v for v in violations)
    assert any("第三人称旁白" in v for v in violations)


def test_build_first_person_system_prompt():
    prompt = build_first_person_system_prompt("顾清雪", "短剧甜宠风")
    assert "顾清雪" in prompt
    assert "视角锁死" in prompt
    assert "黄金 3 秒 Hook" in prompt
