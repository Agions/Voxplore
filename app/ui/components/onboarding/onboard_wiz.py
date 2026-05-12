#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Onboarding Wizard (Backward Compatibility)

此文件已弃用，请使用 onboard_wizard.py + onboard_steps.py。
"""

from .onboard_wizard import OnboardingWizard
from .onboard_steps import (
    StepIndicator, StepContent,
    WelcomeStep, AIProviderStep,
    PreferencesStep, CompletionStep,
)
from .feature_tour import COLORS

__all__ = [
    "OnboardingWizard",
    "StepIndicator",
    "StepContent",
    "WelcomeStep",
    "AIProviderStep",
    "PreferencesStep",
    "CompletionStep",
]
