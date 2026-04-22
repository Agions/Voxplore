#!/usr/bin/env python3
"""Test Sync Engine"""


from app.services.audio.sync_engine import (
    SyncStrategy,
    TransitionType,
    SyncPoint,
    SyncPlan,
    SyncEngine,
)


class TestSyncStrategy:
    """Test sync strategy enum"""

    def test_all_strategies(self):
        """Test all strategies"""
        strategies = [
            SyncStrategy.BEAT_SYNC,
            SyncStrategy.PHRASE_SYNC,
            SyncStrategy.ENERGY_SYNC,
            SyncStrategy.HYBRID,
        ]
        
        assert len(strategies) == 4
        assert SyncStrategy.BEAT_SYNC.value == "beat_sync"


class TestTransitionType:
    """Test transition type enum"""

    def test_all_types(self):
        """Test all transition types"""
        assert TransitionType.HARD_CUT.value == "hard_cut"
        assert TransitionType.CROSSFADE.value == "crossfade"
        assert TransitionType.FADE_IN.value == "fade_in"
        assert TransitionType.FADE_OUT.value == "fade_out"
        assert TransitionType.ZOOM.value == "zoom"
        assert TransitionType.WHIP.value == "whip"


class TestSyncPoint:
    """Test sync point"""

    def test_creation(self):
        """Test creation"""
        point = SyncPoint(
            timestamp=1.5,
            clip_index=0,
            transition=TransitionType.HARD_CUT,
        )
        
        assert point.timestamp == 1.5
        assert point.transition == TransitionType.HARD_CUT
        assert point.clip_index == 0


class TestSyncPlan:
    """Test sync plan"""

    def test_creation(self):
        """Test creation"""
        plan = SyncPlan(
            total_duration=60.0,
            bpm=120.0,
            strategy=SyncStrategy.BEAT_SYNC,
            sync_points=[],
        )
        
        assert plan.total_duration == 60.0
        assert plan.bpm == 120.0
        assert plan.strategy == SyncStrategy.BEAT_SYNC
        assert plan.sync_points == []


class TestSyncEngine:
    """Test sync engine"""

    def test_init(self):
        """Test initialization"""
        engine = SyncEngine()
        
        assert engine is not None
