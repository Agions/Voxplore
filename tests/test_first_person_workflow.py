#!/usr/bin/env python3
"""Tests for reusable first-person narration workflow definitions."""

from scenefab.pipeline.first_person_workflow import (
    FIRST_PERSON_QUALITY_GATES,
    FIRST_PERSON_SCRIPT_RULES,
    FIRST_PERSON_WORKFLOW,
    numbered_workflow,
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
