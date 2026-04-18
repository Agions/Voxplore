#!/usr/bin/env python3
"""测试剪映导出器"""

import pytest
from dataclasses import asdict

from app.services.export.jianying_exporter import (
    TrackType,
    MaterialType,
    TimeRange,
    Track,
    JianyingDraft,
    JianyingExporter,
)


class TestTrackType:
    """测试轨道类型枚举"""

    def test_all_types(self):
        """测试所有轨道类型"""
        types = [
            TrackType.VIDEO,
            TrackType.AUDIO,
            TrackType.TEXT,
            TrackType.STICKER,
            TrackType.EFFECT,
        ]
        
        assert len(types) == 5
        assert TrackType.VIDEO.value == "video"


class TestMaterialType:
    """测试素材类型枚举"""

    def test_all_types(self):
        """测试所有素材类型"""
        types = [
            MaterialType.VIDEO,
            MaterialType.AUDIO,
            MaterialType.TEXT,
            MaterialType.IMAGE,
            MaterialType.SOUND_CHANNEL,
        ]
        
        assert len(types) == 5
        assert MaterialType.VIDEO.value == "video"


class TestTimeRange:
    """测试时间范围"""

    def test_creation(self):
        """测试创建"""
        tr = TimeRange(
            start=1000000,  # 1秒 = 1000000微秒
            duration=500000,  # 0.5秒
        )
        
        assert tr.start == 1000000
        assert tr.duration == 500000

    def test_seconds_to_microseconds(self):
        """测试秒转微秒（使用 TimeRange.from_seconds）"""
        tr = TimeRange.from_seconds(start=1.0, duration=0.5)

        assert tr.start == 1000000
        assert tr.duration == 500000


class TestJianyingDraft:
    """测试剪映草稿"""

    def test_creation(self):
        """测试创建"""
        draft = JianyingDraft(
            name="测试项目",
        )

        assert draft.name == "测试项目"
        assert draft.duration == 0
        assert draft.canvas_config.width == 1080
        assert draft.canvas_config.height == 1920


class TestJianyingExporter:
    """测试剪映导出器"""

    def test_init(self):
        """测试初始化"""
        exporter = JianyingExporter()

        assert exporter.config is not None

    def test_create_draft(self):
        """测试创建草稿"""
        exporter = JianyingExporter()

        draft = exporter.create_draft("测试项目")

        assert draft.name == "测试项目"
        # 默认画布比例 9:16 (竖屏短视频)
        assert draft.canvas_config.width == 1080
        assert draft.canvas_config.height == 1920

    def test_add_video_track(self):
        """测试添加视频轨道"""
        track = Track(type=TrackType.VIDEO)

        assert track.type == TrackType.VIDEO

    def test_add_audio_track(self):
        """测试添加音频轨道"""
        track = Track(type=TrackType.AUDIO)

        assert track.type == TrackType.AUDIO
