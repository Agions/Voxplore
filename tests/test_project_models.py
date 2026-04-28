"""Test project_models data classes"""
from app.core.models.project_models import (
    ProjectStatus,
    ProjectType,
    ProjectMetadata,
    ProjectSettings,
    ProjectMedia,
    ProjectTimeline,
)


class TestProjectStatus:
    def test_all_statuses(self):
        assert ProjectStatus.ACTIVE.value == "active"
        assert ProjectStatus.ARCHIVED.value == "archived"
        assert ProjectStatus.TEMPLATE.value == "template"
        assert ProjectStatus.CORRUPTED.value == "corrupted"


class TestProjectType:
    def test_video_editing(self):
        assert ProjectType.VIDEO_EDITING.value == "video_editing"
        assert ProjectType.VIDEO_EDITING.display_name == "视频剪辑"

    def test_ai_enhancement(self):
        assert ProjectType.AI_ENHANCEMENT.value == "ai_enhancement"
        assert ProjectType.AI_ENHANCEMENT.display_name == "AI 增强"

    def test_missing_by_value(self):
        t = ProjectType("ai_enhancement")
        assert t == ProjectType.AI_ENHANCEMENT


class TestProjectMetadata:
    def test_creation(self):
        meta = ProjectMetadata(
            name="Test Project",
            project_type=ProjectType.VIDEO_EDITING
        )
        assert meta.name == "Test Project"
        assert meta.project_type == ProjectType.VIDEO_EDITING
        assert meta.status == ProjectStatus.ACTIVE

    def test_to_dict(self):
        meta = ProjectMetadata(name="Test", project_type=ProjectType.VIDEO_EDITING)
        d = meta.to_dict()
        assert d["name"] == "Test"
        assert d["project_type"] == "video_editing"

    def test_from_dict(self):
        data = {"name": "From Dict", "project_type": "ai_enhancement", "status": "archived"}
        meta = ProjectMetadata.from_dict(data)
        assert meta.name == "From Dict"
        assert meta.project_type == ProjectType.AI_ENHANCEMENT
        assert meta.status == ProjectStatus.ARCHIVED


class TestProjectSettings:
    def test_creation(self):
        settings = ProjectSettings()
        assert settings.resolution == "1920x1080"
        assert settings.fps == 30
        assert settings.codec == "h264"

    def test_custom_settings(self):
        settings = ProjectSettings(resolution="3840x2160", fps=60)
        assert settings.resolution == "3840x2160"
        assert settings.fps == 60

    def test_to_dict(self):
        settings = ProjectSettings()
        d = settings.to_dict()
        assert d["resolution"] == "1920x1080"
        assert d["fps"] == 30

    def test_from_dict(self):
        data = {"resolution": "1280x720", "fps": 24}
        settings = ProjectSettings.from_dict(data)
        assert settings.resolution == "1280x720"
        assert settings.fps == 24


class TestProjectMedia:
    def test_creation(self):
        media = ProjectMedia(id="media1", name="test.mp4", type="video", path="/path/test.mp4")
        assert media.id == "media1"
        assert media.type == "video"
        assert media.path == "/path/test.mp4"

    def test_to_dict(self):
        media = ProjectMedia(id="m1", name="t.mp4", type="video", path="/p/t.mp4")
        d = media.to_dict()
        assert d["id"] == "m1"
        assert d["type"] == "video"

    def test_from_dict(self):
        data = {"id": "id2", "name": "video.mp4", "type": "video", "path": "/v.mp4"}
        media = ProjectMedia.from_dict(data)
        assert media.id == "id2"
        assert media.name == "video.mp4"


class TestProjectTimeline:
    def test_creation(self):
        timeline = ProjectTimeline()
        assert timeline.tracks == []
        assert timeline.duration == 0.0

    def test_with_tracks(self):
        timeline = ProjectTimeline(tracks=[{"id": "t1"}], duration=60.0)
        assert len(timeline.tracks) == 1
        assert timeline.duration == 60.0

    def test_to_dict(self):
        timeline = ProjectTimeline(tracks=[], duration=30.0)
        d = timeline.to_dict()
        assert d["duration"] == 30.0
        assert d["tracks"] == []
