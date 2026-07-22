"""SceneFab 项目管理包。

公开 API:
- ProjectManager: 项目生命周期管理（原 scenefab.project_manager）
- TemplateManager: 项目模板管理（原 scenefab.project_template_manager）
- TemplateCategory / TemplateInfo / TemplateMetadata: 模板数据模型（原 template_models）
"""

from .manager import ProjectManager
from .template_mgr import TemplateManager
from .template_models import TemplateCategory, TemplateInfo, TemplateMetadata

__all__ = [
    "ProjectManager",
    "TemplateManager",
    "TemplateCategory",
    "TemplateInfo",
    "TemplateMetadata",
]
