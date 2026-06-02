"""
页面组件模块
"""

from . import stats
from .create_proj_dlg import CreateProjectDialog
from .proj_details_pnl import ProjectDetailsPanel
from .proj_list_pnl import ProjectsListPanel
from .project_cards import ProjectCard, TemplateCard
from .settings_dialog import ProjectSettingsDialog

__all__ = [
    "ProjectCard", "TemplateCard",
    "CreateProjectDialog", "ProjectSettingsDialog",
    "ProjectDetailsPanel", "ProjectsListPanel",
    "stats",
]
