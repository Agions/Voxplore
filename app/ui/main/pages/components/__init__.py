"""
页面组件模块
"""

from .project_cards import ProjectCard, TemplateCard
from .dialogs import CreateProjectDialog, ProjectSettingsDialog
from . import stats
from .project_details_panel import ProjectDetailsPanel
from .projects_list_panel import ProjectsListPanel

__all__ = [
    "ProjectCard", "TemplateCard",
    "CreateProjectDialog", "ProjectSettingsDialog",
    "ProjectDetailsPanel", "ProjectsListPanel",
    "stats",
]
