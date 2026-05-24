"""
页面组件模块
"""

from .project_cards import ProjectCard, TemplateCard
from .create_proj_dlg import CreateProjectDialog
from .settings_dialog import ProjectSettingsDialog
from . import stats
from .proj_details_pnl import ProjectDetailsPanel
from .proj_list_pnl import ProjectsListPanel

__all__ = [
    "ProjectCard", "TemplateCard",
    "CreateProjectDialog", "ProjectSettingsDialog",
    "ProjectDetailsPanel", "ProjectsListPanel",
    "stats",
]
