"""
SceneFab 合规性服务模块

提供素材版权预检、合理使用建议、敏感内容检测等合规性功能。

核心功能：
- 素材来源溯源记录
- 合理使用时长建议（< 10% 或 < 2min 安全阈值）
- 敏感内容初筛（暴力/裸露/政治风险提示）
"""

from .copyright_checker import CopyrightChecker, CopyrightCheckResult
from .fair_use_advisor import FairUseAdvisor, FairUseAssessment
from .sensitive_content_detector import SensitiveContentDetector, SensitiveContentResult

__all__ = [
    "CopyrightChecker",
    "CopyrightCheckResult",
    "SensitiveContentDetector",
    "SensitiveContentResult",
    "FairUseAdvisor",
    "FairUseAssessment",
]
