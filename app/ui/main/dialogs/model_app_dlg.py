#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Model Application Dialog (Backward Compatibility)

此文件已弃用，请使用 model_app_pages.py + model_app_dialog.py。
"""

from .model_app_dialog import ModelApplicationDialog
from .model_app_pages import (
    ApplicationStep,
    ProviderInfo,
    ProviderSelectionPage,
    RequirementsPage,
    ApplicationFormPage,
    SubmitApplicationPage,
)

__all__ = [
    "ModelApplicationDialog",
    "ApplicationStep",
    "ProviderInfo",
    "ProviderSelectionPage",
    "RequirementsPage",
    "ApplicationFormPage",
    "SubmitApplicationPage",
]
