#!/usr/bin/env python3
"""测试剪映导出器"""


from app.services.export.jianying_exporter import (
    TrackType,
    MaterialType,
    TimeRange,
    Track,
    Segment,
    JianyingDraft,
    JianyingExporter,
)
from app.services.export.jianying_models import (
    JianyingMaterials,
    VideoMaterial,
    AudioMaterial,
    TextMaterial,
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


class TestJianyingMaterials:
    """测试素材集合"""

    def test_to_dict(self):
        """测试 to_dict 方法（JianyingMaterials 无 to_dict 会导致 to_draft_content 失败）"""
        mats = JianyingMaterials(
            videos=[VideoMaterial(path="/test.mp4", duration=5000000)],
            audios=[AudioMaterial(path="/a.mp3", duration=3000000)],
            texts=[TextMaterial(content="测试字幕")],
        )
        result = mats.to_dict()
        assert "videos" in result
        assert "audios" in result
        assert "texts" in result
        assert result["videos"][0]["path"] == "/test.mp4"


class TestJianyingDraftContent:
    """测试 draft 内容生成"""

    def test_to_draft_content(self):
        """测试 to_draft_content 生成完整 JSON（JianyingMaterials 缺失 to_dict 会触发 AttributeError）"""
        draft = JianyingDraft(name="Test")
        draft.materials = JianyingMaterials(
            videos=[VideoMaterial(path="/a.mp4", duration=5000000)],
            audios=[],
            texts=[],
        )
        content = draft.to_draft_content()
        assert content["name"] == "Test"
        assert "materials" in content
        assert "tracks" in content
        assert content["materials"]["videos"][0]["path"] == "/a.mp4"

    def test_to_draft_content_with_segments(self):
        """测试带轨道片段的 to_draft_content"""
        draft = JianyingDraft(name="With Segments")
        draft.materials = JianyingMaterials(
            videos=[VideoMaterial(id="v1", path="/a.mp4", duration=5000000)],
            audios=[],
            texts=[],
        )
        track = Track(id="t1", type=TrackType.VIDEO)
        track.add_segment(
            Segment(
                material_id="v1",
                target_timerange=TimeRange(start=0, duration=5000000),
                source_timerange=TimeRange(start=0, duration=5000000),
            )
        )
        draft.tracks.append(track)
        content = draft.to_draft_content()
        assert len(content["tracks"]) == 1
        assert content["tracks"][0]["type"] == "video"
        assert len(content["tracks"][0]["segments"]) == 1
