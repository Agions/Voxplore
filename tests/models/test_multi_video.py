"""v2.5.0 多文件上传扩展 - 数据模型 / 服务层 / Runner / DropZone / UI 单元测试。

覆盖范围：
- models/project.py: VideoSource / MultiVideoSource / SeriesContext
- services/video/monologue_maker.py: create_project 多视频参数 + create_batch + 持久化兼容
- ui/main/main_window/production_runner.py: start / start_batch
- ui/main/main_window/drop_zone.py: collect_paths 多 URL + 向后兼容单 callback
- ui/main/pages/production_page.py: VideoDropzoneFrame 多文件 API
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

# ═══════════════════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════════════════


class TestVideoSource:
    """VideoSource 单元测试。"""

    def test_default_label_from_path(self):
        from app.models.project import VideoSource

        vs = VideoSource(path="/tmp/raw_clip.mp4")
        assert vs.label == "raw_clip"
        assert vs.basename == "raw_clip.mp4"
        assert vs.order == 0
        assert vs.duration == 0.0

    def test_explicit_label(self):
        from app.models.project import VideoSource

        vs = VideoSource(path="/tmp/raw.mp4", label="自定义")
        assert vs.label == "自定义"


class TestMultiVideoSource:
    """MultiVideoSource 单元测试。"""

    def test_default_empty(self):
        from app.models.project import MultiVideoSource

        mvs = MultiVideoSource()
        assert mvs.is_empty
        assert mvs.count == 0
        assert mvs.paths == []
        assert mvs.strategy == "single"

    def test_add_with_dedup(self):
        from app.models.project import MultiVideoSource

        mvs = MultiVideoSource()
        assert mvs.add("/tmp/a.mp4") is not None
        assert mvs.add("/tmp/b.mp4") is not None
        # 重复添加不增计数
        again = mvs.add("/tmp/a.mp4")
        assert mvs.count == 2
        # 重复添加返回已存在的 VideoSource
        assert again.path == "/tmp/a.mp4"

    def test_add_many(self):
        from app.models.project import MultiVideoSource

        mvs = MultiVideoSource()
        added = mvs.add_many(["/tmp/a.mp4", "/tmp/b.mp4", "/tmp/a.mp4"])
        assert added == 2
        assert mvs.count == 2

    def test_move_preserves_order_semantics(self):
        from app.models.project import MultiVideoSource

        mvs = MultiVideoSource()
        mvs.add_many(["/tmp/a.mp4", "/tmp/b.mp4", "/tmp/c.mp4"])
        # 0 → 2: [b, c, a]
        assert mvs.move(0, 2)
        assert mvs.paths == ["/tmp/b.mp4", "/tmp/c.mp4", "/tmp/a.mp4"]
        for i, v in enumerate(mvs.videos):
            assert v.order == i

    def test_move_invalid_returns_false(self):
        from app.models.project import MultiVideoSource

        mvs = MultiVideoSource()
        mvs.add("/tmp/a.mp4")
        assert not mvs.move(0, 1)
        assert not mvs.move(-1, 0)
        assert not mvs.move(0, 0)

    def test_remove(self):
        from app.models.project import MultiVideoSource

        mvs = MultiVideoSource()
        mvs.add_many(["/tmp/a.mp4", "/tmp/b.mp4", "/tmp/c.mp4"])
        removed = mvs.remove(1)
        assert removed is not None
        assert removed.path == "/tmp/b.mp4"
        assert mvs.count == 2
        assert mvs.paths == ["/tmp/a.mp4", "/tmp/c.mp4"]

    def test_rename(self):
        from app.models.project import MultiVideoSource

        mvs = MultiVideoSource()
        mvs.add("/tmp/a.mp4")
        assert mvs.rename(0, "新版")
        assert mvs.videos[0].label == "新版"
        assert not mvs.rename(99, "X")

    def test_to_dict(self):
        from app.models.project import MultiVideoSource

        mvs = MultiVideoSource(strategy="batch")
        mvs.add("/tmp/a.mp4")
        mvs.add("/tmp/b.mp4")
        d = mvs.to_dict()
        assert d["strategy"] == "batch"
        assert len(d["videos"]) == 2
        assert d["videos"][0]["path"] == "/tmp/a.mp4"

    def test_clear(self):
        from app.models.project import MultiVideoSource

        mvs = MultiVideoSource()
        mvs.add_many(["/tmp/a.mp4", "/tmp/b.mp4"])
        mvs.clear()
        assert mvs.is_empty


class TestSeriesContext:
    """SeriesContext 单元测试。"""

    def test_default(self):
        from app.models.project import SeriesContext

        sc = SeriesContext()
        assert sc.series_title == ""
        assert sc.shared_characters == []
        assert sc.total_episodes == 0

    def test_to_dict(self):
        from app.models.project import SeriesContext

        sc = SeriesContext(
            series_title="深夜短剧",
            shared_characters=["女主", "男主"],
            total_episodes=10,
        )
        d = sc.to_dict()
        assert d["series_title"] == "深夜短剧"
        assert d["shared_characters"] == ["女主", "男主"]
        assert d["total_episodes"] == 10


# ═══════════════════════════════════════════════════════════════════════
# MonologueProject 多视频字段 + 持久化兼容
# ═══════════════════════════════════════════════════════════════════════


class TestMonologueProjectMulti:
    """MonologueProject 新字段 + 持久化向后兼容。"""

    def test_all_source_videos_prefers_list(self):
        from app.services.video.monologue_maker import MonologueProject

        p = MonologueProject(
            source_video="/x/a.mp4",
            source_videos=["/x/a.mp4", "/x/b.mp4"],
            multi_strategy="batch",
        )
        assert p.all_source_videos == ["/x/a.mp4", "/x/b.mp4"]
        assert p.multi_strategy == "batch"

    def test_all_source_videos_fallback(self):
        from app.services.video.monologue_maker import MonologueProject

        p = MonologueProject(source_video="/x/a.mp4")
        assert p.all_source_videos == ["/x/a.mp4"]

    def test_all_source_videos_empty(self):
        from app.services.video.monologue_maker import MonologueProject

        p = MonologueProject()
        assert p.all_source_videos == []

    def test_save_and_load_roundtrip(self):
        from app.services.video.monologue_maker import MonologueProject

        with tempfile.TemporaryDirectory() as td:
            p = MonologueProject(
                name="Multi",
                source_video="/x/a.mp4",
                source_videos=["/x/a.mp4", "/x/b.mp4"],
                multi_strategy="batch",
                output_dir=td,
            )
            path = p.save()
            assert Path(path).exists()
            loaded = MonologueProject.load(path)
            assert loaded.source_video == "/x/a.mp4"
            assert loaded.source_videos == ["/x/a.mp4", "/x/b.mp4"]
            assert loaded.multi_strategy == "batch"

    def test_load_backward_compatible_source_video_only(self):
        """旧 .scenefab（只有 source_video 字段）应能正常加载。"""
        from app.services.video.monologue_maker import MonologueProject

        with tempfile.TemporaryDirectory() as td:
            # 手工写一个旧格式（只有 source_video）
            old_data = {
                "version": "1.0",
                "type": "monologue",
                "id": "legacy",
                "name": "Legacy",
                "source_video": "/old/x.mp4",
                "video_duration": 0.0,
                "output_dir": td,
                "context": "",
                "emotion": "",
                "full_script": "",
                "style": "melancholic",
                "caption_style": "cinematic",
                "segments": [],
            }
            save_path = Path(td) / "legacy.scenefab"
            from app.utils.json_io import write_json

            write_json(save_path, old_data, indent=2)
            loaded = MonologueProject.load(str(save_path))
            # source_videos 应自动回退为 [source_video]
            assert loaded.source_video == "/old/x.mp4"
            assert loaded.source_videos == ["/old/x.mp4"]
            assert loaded.multi_strategy == "single"
            assert loaded.series_context is None

    def test_load_with_series_context(self):
        from app.services.video.monologue_maker import MonologueProject

        with tempfile.TemporaryDirectory() as td:
            p = MonologueProject(
                name="Series",
                source_video="/x/ep1.mp4",
                source_videos=["/x/ep1.mp4", "/x/ep2.mp4"],
                multi_strategy="series",
                output_dir=td,
            )
            from app.models.project import SeriesContext

            p.series_context = SeriesContext(
                series_title="深夜短剧",
                shared_characters=["A", "B"],
                total_episodes=12,
            )
            path = p.save()
            loaded = MonologueProject.load(path)
            assert loaded.series_context is not None
            assert loaded.series_context.series_title == "深夜短剧"
            assert loaded.series_context.total_episodes == 12


# ═══════════════════════════════════════════════════════════════════════
# MonologueMaker.create_project 多视频参数 + create_batch
# ═══════════════════════════════════════════════════════════════════════


class TestMonologueMakerMultiVideo:
    """MonologueMaker 多视频 API。"""

    @pytest.fixture
    def fake_video_dir(self):
        with tempfile.TemporaryDirectory() as td:
            for name in ("a.mp4", "b.mp4", "c.mp4"):
                (Path(td) / name).write_bytes(b"\x00" * 1024)
            yield td

    def test_create_project_single_path_legacy(self, fake_video_dir):
        """老调用方式仍然工作。"""
        from app.services.video.monologue_maker import MonologueMaker

        maker = MonologueMaker()
        p = maker.create_project(
            source_video=str(Path(fake_video_dir) / "a.mp4"),
            context="测试",
            emotion="惆怅",
        )
        assert p.source_video.endswith("a.mp4")
        assert p.all_source_videos == [str(Path(fake_video_dir) / "a.mp4")]

    def test_create_project_multi_videos_strategy_single_auto_upgrade(self, fake_video_dir):
        """多文件 + strategy=single 应自动升级为 batch。"""
        from app.services.video.monologue_maker import MonologueMaker

        maker = MonologueMaker()
        p = maker.create_project(
            source_videos=[
                str(Path(fake_video_dir) / "a.mp4"),
                str(Path(fake_video_dir) / "b.mp4"),
            ],
            context="测试",
            emotion="惆怅",
            multi_strategy="single",
        )
        assert p.multi_strategy == "batch"
        assert len(p.all_source_videos) == 2

    def test_create_project_multi_videos_batch(self, fake_video_dir):
        from app.services.video.monologue_maker import MonologueMaker

        maker = MonologueMaker()
        paths = [
            str(Path(fake_video_dir) / n)
            for n in ("a.mp4", "b.mp4", "c.mp4")
        ]
        p = maker.create_project(
            source_videos=paths,
            context="测试",
            emotion="惆怅",
            multi_strategy="batch",
        )
        assert p.multi_strategy == "batch"
        assert p.all_source_videos == paths

    def test_create_project_empty_raises(self):
        from app.services.video.monologue_maker import MonologueMaker

        maker = MonologueMaker()
        with pytest.raises(ValueError, match="source_video"):
            maker.create_project(context="空")

    def test_create_batch_list_input(self, fake_video_dir):
        from app.services.video.monologue_maker import MonologueMaker

        maker = MonologueMaker()
        paths = [
            str(Path(fake_video_dir) / n)
            for n in ("a.mp4", "b.mp4", "c.mp4")
        ]
        projects = maker.create_batch(
            sources=paths,
            context="测试",
            emotion="惆怅",
            parallel=1,
        )
        assert len(projects) == 3
        names = [p.name for p in projects]
        assert any(n.startswith("EP01") for n in names)
        assert any(n.startswith("EP02") for n in names)
        assert any(n.startswith("EP03") for n in names)

    def test_create_batch_multi_video_source(self, fake_video_dir):
        from app.models.project import MultiVideoSource
        from app.services.video.monologue_maker import MonologueMaker

        mvs = MultiVideoSource(strategy="batch")
        for n in ("a.mp4", "b.mp4"):
            mvs.add(str(Path(fake_video_dir) / n))
        maker = MonologueMaker()
        projects = maker.create_batch(sources=mvs, context="X", emotion="惆怅")
        assert len(projects) == 2

    def test_create_batch_empty_input(self):
        from app.services.video.monologue_maker import MonologueMaker

        maker = MonologueMaker()
        assert maker.create_batch(sources=[], context="X", emotion="惆怅") == []


# ═══════════════════════════════════════════════════════════════════════
# ProductionRunner.start_batch
# ═══════════════════════════════════════════════════════════════════════


class TestProductionRunnerStartBatch:
    """ProductionRunner.start / start_batch 行为。"""

    def _build_runner(self):
        # 延迟导入 PySide6，避免无关测试报无 display
        from app.ui.main.main_window.production_runner import ProductionRunner

        return ProductionRunner()

    def test_start_delegates_to_start_batch(self, monkeypatch):
        """老 start() 应当委派给 start_batch()，并把单路径包装为列表。"""
        from app.ui.main.main_window.production_runner import ProductionRunner

        runner = ProductionRunner()
        captured: dict[str, Any] = {}

        def fake_start_batch(paths, context, emotion, *, strategy="single", series_context=None):
            captured["paths"] = list(paths)
            captured["strategy"] = strategy
            return True

        monkeypatch.setattr(runner, "start_batch", fake_start_batch)
        ok = runner.start("/x/single.mp4", "ctx", "惆怅")
        assert ok is True
        assert captured["paths"] == ["/x/single.mp4"]
        assert captured["strategy"] == "single"

    def test_start_batch_single_path_downgrade_strategy(self):
        """1 路径 + strategy=batch 应降级为 single。"""
        from PySide6.QtCore import QObject, Signal

        runner = self._build_runner()
        captured: dict[str, Any] = {}

        class _StubWorker(QObject):
            progress = Signal(int, int, str)
            finished = Signal(object)
            error = Signal(str)
            cancelled = Signal()

            def start(self):
                pass

        def fake_make_worker(paths, ctx, emo, strategy, sc):
            captured["args"] = (list(paths), strategy)
            return _StubWorker()

        runner._make_worker = fake_make_worker  # type: ignore[assignment]
        runner.start_batch(["/x/single.mp4"], "ctx", "惆怅", strategy="batch")
        assert captured["args"][1] == "single"

    def test_start_batch_empty_paths_returns_false(self):
        runner = self._build_runner()
        assert runner.start_batch([], "ctx", "惆怅") is False

    def test_start_batch_already_running(self):
        runner = self._build_runner()
        runner.is_running = lambda: True  # type: ignore[assignment]
        assert runner.start_batch(["/x/a.mp4"], "ctx", "惆怅") is False


class TestMultiProjectResult:
    """MultiProjectResult 容器。"""

    def test_single(self):
        from app.ui.main.main_window.production_runner import MultiProjectResult

        r = MultiProjectResult([object()], ["/x/a.scenefab"], "single")
        assert r.count == 1
        assert not r.is_multi
        assert r.first_path == "/x/a.scenefab"
        assert r.strategy == "single"

    def test_multi(self):
        from app.ui.main.main_window.production_runner import MultiProjectResult

        objs = [object(), object(), object()]
        r = MultiProjectResult(objs, ["/a", "/b", "/c"], "batch")
        assert r.count == 3
        assert r.is_multi
        assert r.first_project is objs[0]
        assert r.first_path == "/a"
        assert len(list(r)) == 3
        assert r[1] is objs[1]


# ═══════════════════════════════════════════════════════════════════════
# MainWindowDropZone 多 URL 收集 + 向后兼容
# ═══════════════════════════════════════════════════════════════════════


class _FakeUrl:
    def __init__(self, path):
        self._path = path

    def toLocalFile(self):
        return self._path


class _FakeMime:
    def __init__(self, urls):
        self._urls = urls

    def hasUrls(self):
        return bool(self._urls)

    def urls(self):
        return self._urls


class _FakeDropEvent:
    def __init__(self, urls, accepted=False, ignored=False):
        self._mime = _FakeMime(urls)
        self._accepted = accepted
        self._ignored = ignored

    def mimeData(self):
        return self._mime

    def acceptProposedAction(self):
        self._accepted = True

    def ignore(self):
        self._ignored = True


class TestMainWindowDropZoneCollect:
    """collect_paths / handle_drop 多文件行为。"""

    @pytest.fixture(autouse=True, scope="class")
    def _qapp(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        yield app

    def _build(self, **kwargs):
        from PySide6.QtWidgets import QMainWindow

        from app.ui.main.main_window.drop_zone import MainWindowDropZone

        win = QMainWindow()
        return MainWindowDropZone(win, **kwargs), win

    def test_collect_paths_filters_and_dedups(self):
        dz, _win = self._build()
        event = _FakeDropEvent(
            urls=[
                _FakeUrl("/tmp/a.mp4"),
                _FakeUrl("/tmp/b.mov"),
                _FakeUrl("/tmp/c.txt"),   # 非视频，过滤
                _FakeUrl("/tmp/a.mp4"),   # 重复
                _FakeUrl("/tmp/d.MP4"),   # 大小写
            ]
        )
        paths = dz.collect_paths(event)
        assert "/tmp/a.mp4" in paths
        assert "/tmp/b.mov" in paths
        assert "/tmp/c.txt" not in paths
        assert "/tmp/d.MP4" in paths
        # 去重：a.mp4 只出现一次
        assert paths.count("/tmp/a.mp4") == 1
        # 顺序保持
        assert paths[0] == "/tmp/a.mp4"

    def test_handle_drop_backward_compat_single_callback(self):
        """未提供 multi_on_drop 时，老 callback 仍只接收首个路径。"""
        dz, _win = self._build()
        seen: list[str] = []
        dz._on_drop = seen.append  # type: ignore[assignment]
        event = _FakeDropEvent(
            urls=[_FakeUrl("/x/a.mp4"), _FakeUrl("/x/b.mp4")])
        dz.handle_drop(event)
        assert seen == ["/x/a.mp4"]
        assert event._accepted is True

    def test_handle_drop_multi_callback(self):
        """提供 multi_on_drop 时，收到完整列表。"""
        dz, _win = self._build(multi_on_drop=lambda paths: None)
        seen: list[list[str]] = []
        dz._multi_on_drop = seen.append  # type: ignore[assignment]
        event = _FakeDropEvent(
            urls=[_FakeUrl("/x/a.mp4"), _FakeUrl("/x/b.mp4"),
                  _FakeUrl("/x/c.txt")]
        )
        dz.handle_drop(event)
        assert seen == [["/x/a.mp4", "/x/b.mp4"]]

    def test_handle_drop_no_video_ignores(self):
        dz, _win = self._build(multi_on_drop=lambda p: None)
        called: list[list[str]] = []
        dz._multi_on_drop = called.append  # type: ignore[assignment]
        event = _FakeDropEvent(urls=[_FakeUrl("/x/a.txt")])
        dz.handle_drop(event)
        assert called == []
        assert event._ignored is True


# ═══════════════════════════════════════════════════════════════════════
# VideoDropzoneFrame 多文件 UI 测试
# ═══════════════════════════════════════════════════════════════════════


class TestVideoDropzoneFrameMulti:
    """VideoDropzoneFrame 多文件 API 测试。"""

    @pytest.fixture(scope="class")
    def qapp(self, qapp_args=None):  # noqa: ARG003 - pytest-qt 约定
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        yield app

    def test_empty_state(self, qapp):
        from app.ui.main.pages.production_page import VideoDropzoneFrame

        frame = VideoDropzoneFrame()
        assert frame.selected_path == ""
        assert frame.paths == []
        assert frame.sources.is_empty

    def test_set_file_backward_compat(self, qapp, tmp_path):
        from app.ui.main.pages.production_page import VideoDropzoneFrame

        frame = VideoDropzoneFrame()
        captured: list[str] = []
        frame.file_selected.connect(captured.append)
        p = str(tmp_path / "a.mp4")
        frame.set_file(p)
        assert frame.selected_path == p
        assert frame.paths == [p]
        assert captured == [p]

    def test_add_paths_emits_files_changed(self, qapp, tmp_path):
        from app.ui.main.pages.production_page import VideoDropzoneFrame

        frame = VideoDropzoneFrame()
        captured: list[list] = []
        frame.files_changed.connect(captured.append)
        paths = [
            str(tmp_path / "a.mp4"),
            str(tmp_path / "b.mp4"),
        ]
        added = frame.add_paths(paths)
        assert added == 2
        assert frame.sources.count == 2
        assert len(captured) == 1
        assert len(captured[0]) == 2
        # selected_path 仍指向首个（向后兼容）
        assert frame.selected_path == paths[0]

    def test_add_paths_dedup(self, qapp, tmp_path):
        from app.ui.main.pages.production_page import VideoDropzoneFrame

        frame = VideoDropzoneFrame()
        p = str(tmp_path / "a.mp4")
        frame.add_paths([p, p])
        assert frame.sources.count == 1

    def test_remove(self, qapp, tmp_path):
        from app.ui.main.pages.production_page import VideoDropzoneFrame

        frame = VideoDropzoneFrame()
        frame.add_paths([str(tmp_path / n)
                        for n in ("a.mp4", "b.mp4", "c.mp4")])
        assert frame.remove(1)
        assert frame.sources.count == 2
        assert frame.sources.paths[0].endswith("a.mp4")
        assert frame.sources.paths[1].endswith("c.mp4")

    def test_move(self, qapp, tmp_path):
        from app.ui.main.pages.production_page import VideoDropzoneFrame

        frame = VideoDropzoneFrame()
        frame.add_paths([str(tmp_path / n)
                        for n in ("a.mp4", "b.mp4", "c.mp4")])
        assert frame.move(0, 2)
        # 顺序：b, c, a
        assert frame.sources.paths[0].endswith("b.mp4")
        assert frame.sources.paths[2].endswith("a.mp4")

    def test_clear(self, qapp, tmp_path):
        from app.ui.main.pages.production_page import VideoDropzoneFrame

        frame = VideoDropzoneFrame()
        frame.add_paths([str(tmp_path / "a.mp4")])
        frame.clear()
        assert frame.sources.is_empty
        assert frame.selected_path == ""
