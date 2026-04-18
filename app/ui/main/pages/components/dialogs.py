#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目管理对话框组件

保留导入接口，具体的对话框实现已拆分到独立文件。
"""

from .create_project_dialog import CreateProjectDialog
from .project_settings_dialog import ProjectSettingsDialog

__all__ = ["CreateProjectDialog", "ProjectSettingsDialog"]
