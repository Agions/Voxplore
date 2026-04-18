"""
Voxplore 音频分析服务

提供音频处理能力:
- BeatDetector: 节拍检测
- SyncEngine: 音画同步
"""

from enum import Enum
from dataclasses import dataclass

from .beat_detector import (
    BeatDetector,
    BeatInfo,
    BeatSyncCutpoint,
    AudioAnalysisResult,
)
from .sync_engine import (
    SyncEngine,
    SyncPoint,
    SyncPlan,
)


# ============ 枚举定义 ============

class BeatStrength(Enum):
    """节拍强度"""
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


class MusicSection(Enum):
    """音乐段落"""
    INTRO = "intro"
    VERSE = "verse"
    CHORUS = "chorus"
    BRIDGE = "bridge"
    OUTRO = "outro"


class SyncStrategy(Enum):
    """同步策略"""
    BEAT_SYNC = "beat_sync"
    ENERGY_SYNC = "energy_sync"
    MANUAL = "manual"


class TransitionType(Enum):
    """转场类型"""
    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPE = "wipe"


# ============ 配置类 ============

@dataclass
class SyncConfig:
    """音画同步配置"""
    strategy: SyncStrategy = SyncStrategy.BEAT_SYNC
    transition: TransitionType = TransitionType.CUT
    beat_match_tolerance: float = 0.1  # 秒
    energy_match_threshold: float = 0.5
    auto_transition: bool = True


@dataclass
class SectionInfo:
    """音乐段落信息"""
    section: MusicSection
    start_time: float
    end_time: float
    energy: float


__all__ = [
    # Beat Detector
    "BeatDetector",
    "BeatInfo",
    "BeatSyncCutpoint",
    "BeatStrength",
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
