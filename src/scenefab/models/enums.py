#!/usr/bin/env python3

"""
SceneFab 全局枚举集中地

.. versionadded:: Phase 5 重构
   集中管理分散在各模块的枚举类，便于统一查找和维护。

每个枚举的权威位置如下（历史路径已迁移到此处）：

应用层：
- ApplicationState: 应用状态（从 application.py + core/__init__.py 合并）
- ErrorType: 错误类型（从 application.py 迁移）
- ErrorSeverity: 错误严重程度（从 application.py 迁移，字段：LOW/MEDIUM/HIGH/CRITICAL）

服务层：
- ServiceStatus: 服务状态（已在 services/ai/base.py 统一为权威，Phase 1 完成）
- ServiceLifetime: 服务生命周期（从 service_container.py 迁移）

AI/媒体层：
- NarrationStyle: 解说风格（从 models/narration.py 迁移）
- EmotionType: 情感类型（已在 models/narration.py 统一为权威，Phase 1 完成）
- ProjectStatus, ProjectType: 项目状态/类型（从 models/project_models.py 迁移）

管道层：
- PipelineStage: 流水线阶段（从 orchestration/pipeline_controller.py 迁移）

说明：本模块对枚举类**做重新导出**（re-export），不重新定义，以保留
每个枚举的语义归属。导入新代码推荐::

    from scenefab.models.enums import ApplicationState, ErrorType

或继续从权威模块导入（两者指向同一对象）::

    from scenefab.models.narration import EmotionType
"""

# ── 应用层 ──────────────────────────────────────────────
from scenefab.application import (
    ApplicationState,
    ErrorSeverity,
    ErrorType,
)

# ── 媒体/AI ─────────────────────────────────────────────
from scenefab.models.narration import EmotionType, NarrationStyle
from scenefab.models.project_models import ProjectStatus, ProjectType

# ── 服务层 ──────────────────────────────────────────────
from scenefab.service_container import ServiceLifetime
from scenefab.services.ai.base import (  # noqa: F401  # re-exported
    ServiceHealth,
    ServiceStatus,
)

# ── 管道 ────────────────────────────────────────────────
# PipelineStage 暂不集中（pipeline_controller 强依赖 PySide6，
# 在无 PySide6 环境下 import 会失败；Phase 5 后续 PR 再处理）


__all__ = [
    # 应用层
    "ApplicationState",
    "ErrorType",
    "ErrorSeverity",
    # 服务层
    "ServiceStatus",
    "ServiceHealth",
    "ServiceLifetime",
    # 媒体/AI
    "NarrationStyle",
    "EmotionType",
    "ProjectStatus",
    "ProjectType",
    # 管道
    # "PipelineStage",  # 见上方说明
]
