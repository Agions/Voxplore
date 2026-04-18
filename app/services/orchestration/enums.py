"""
工作流枚举定义

从 workflow_engine.py 提取，保持独立便于复用。
"""

from enum import Enum


class WorkflowStep(Enum):
    """工作流步骤枚举"""
    IMPORT = "import"
    ANALYZE = "analyze"
    MODE_SELECT = "mode_select"
    SCRIPT_GENERATE = "script_gen"
    SCRIPT_EDIT = "script_edit"
    TIMELINE = "timeline"
    VOICEOVER = "voiceover"
    PREVIEW = "preview"
    EXPORT = "export"


class CreationMode(Enum):
    """创作模式枚举"""
    COMMENTARY = "commentary"
    MASHUP = "mashup"
    MONOLOGUE = "monologue"


class WorkflowStatus(Enum):
    """工作流状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class ExportFormat(Enum):
    """导出格式枚举"""
    MP4 = "mp4"
    MOV = "mov"
    AVI = "avi"
    MKV = "mkv"
    XML = "xml"  # Adobe Premiere Pro
    FCP_XML = "fcpxml"  # Final Cut Pro X
    DRP = "drp"  # DaVinci Resolve
