"""
SceneFab 服务模块

提供以下核心服务:
- ai: AI大模型、视觉、语音服务
- video: 视频制作（解说、混剪、独白）
- export: 导出服务（剪映、PR、FCP、DaVinci）
- video_tools: 视频处理工具（字幕、节奏分析）
- orchestration: 编排服务（工作流、撤销管理、批量处理）
"""

# 子模块
from . import ai, export, orchestration, video, video_tools
from .service_manager import (
    AIServiceManagerCompat as AIServiceManager,  # 向后兼容
)

# 兼容层
from .service_manager import (
    ServiceHealth,
    ServiceManager,
    ServiceStatus,
    get_ai_service_manager,
)

__all__ = [
    # 子模块
    "ai",
    "video",
    "export",
    "video_tools",
    "orchestration",
    # 兼容层
    "AIServiceManager",
    "ServiceStatus",
    "ServiceHealth",
    "get_ai_service_manager",
    "ServiceManager",
]
