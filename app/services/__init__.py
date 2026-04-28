"""
Voxplore 服务模块

提供以下核心服务:
- ai: AI大模型、视觉、语音服务
- video: 视频制作（解说、混剪、独白）
- audio: 音频处理（节拍检测、音画同步）
- export: 导出服务（剪映、PR、FCP、DaVinci）
- video_tools: 视频处理工具（字幕、节奏分析）
- orchestration: 编排服务（工作流、撤销管理、批量处理）
- publish: 多平台发布 [暂时关闭]
- ui: UI 图形界面（位于 app/ui/）
"""

# 子模块
from . import ai
from . import video
from . import audio
from . import export
from . import video_tools
from . import orchestration

# 多平台发布功能暂时关闭
# from . import publish

# 兼容层
from .ai_service_manager import AIServiceManager, ServiceStatus, get_ai_service_manager


__all__ = [
    # 子模块
    "ai",
    "video",
    "audio",
    "export",
    "video_tools",
    "orchestration",
    # publish,  # 暂时关闭
    # 兼容层
    "AIServiceManager",
    "ServiceStatus",
    "get_ai_service_manager",
]
