"""
Voxplore 音频分析服务

提供音频处理能力:
- BeatDetector: 节拍检测
- SyncEngine: 音画同步
"""

from dataclasses import dataclass

from .beat_detector import (
    BeatDetector,
    BeatInfo,
    BeatStrength,
    BeatSyncCutpoint,
    MusicSection,
    SectionInfo,
    AudioAnalysisResult,
)
from .sync_engine import (
    SyncEngine,
    SyncPoint,
    SyncPlan,
    SyncStrategy,
    TransitionType,
)


# ============ 配置类 ============

@dataclass
class SyncConfig:
    """音画同步配置"""
    strategy: SyncStrategy = SyncStrategy.BEAT_SYNC
    transition: TransitionType = TransitionType.HARD_CUT
    beat_match_tolerance: float = 0.1  # 秒
    energy_match_threshold: float = 0.5
    auto_transition: bool = True


__all__ = [
    # Beat Detector
    "BeatDetector",
    "BeatInfo",
    "BeatStrength",
    "BeatSyncCutpoint",
    "MusicSection",
    "SectionInfo",
    "AudioAnalysisResult",

    # Sync Engine
    "SyncEngine",
    "SyncConfig",
    "SyncStrategy",
    "TransitionType",
    "SyncPoint",
    "SyncPlan",
]
