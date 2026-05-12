"""
编排服务模块

子模块：
- enums.py        工作流枚举（WorkflowStep/CreationMode/WorkflowStatus/ExportFormat）
- pipe_models.py  工作流数据模型（VideoSource/ScriptData/TimelineData 等）
- pipeline_proj_mgr.py  项目管理
"""

from .enums import (
    WorkflowStep,
    CreationMode,
    WorkflowStatus,
    ExportFormat,
)

from .pipe_models import (
    VideoSource,
    AnalysisResult,
    ScriptData,
    TimelineData,
    VoiceoverData,
    WorkflowState,
    WorkflowCallbacks,
)

from .pipeline_proj_mgr import (
    ProjectManager,
    ProjectType,
    ProjectVersion,
    ProjectMetadata,
    ProjectSource,
    ProjectConfig,
    VoxploreProject,
    save_project,
    load_project,
)

__all__ = [
    # 枚举
    "WorkflowStep",
    "CreationMode",
    "WorkflowStatus",
    "ExportFormat",
    # 模型
    "VideoSource",
    "AnalysisResult",
    "ScriptData",
    "TimelineData",
    "VoiceoverData",
    "WorkflowState",
    "WorkflowCallbacks",
    # 项目管理
    "ProjectManager",
    "ProjectType",
    "ProjectVersion",
    "ProjectMetadata",
    "ProjectSource",
    "ProjectConfig",
    "VoxploreProject",
    "save_project",
    "load_project",
]
