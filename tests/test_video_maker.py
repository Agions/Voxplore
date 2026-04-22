#!/usr/bin/env python3
"""测试视频制作器基类"""

from dataclasses import asdict
from unittest.mock import Mock

from app.services.video.base_maker import (
    BaseProject,
    ProgressMixin,
    BaseVideoMaker,
)


class TestBaseProject:
    """测试基础项目类"""

    def test_default_creation(self):
        """测试默认创建"""
        project = BaseProject()
        
        assert project.id == ""
        assert project.name == "新建项目"
        assert project.source_video == ""
        assert project.video_duration == 0.0
        assert project.output_dir == ""
        assert project.scenes == []

    def test_custom_creation(self):
        """测试自定义创建"""
        project = BaseProject(
            id="test123",
            name="测试项目",
            source_video="/path/to/video.mp4",
            video_duration=120.5,
            output_dir="/output",
        )
        
        assert project.id == "test123"
        assert project.name == "测试项目"
        assert project.source_video == "/path/to/video.mp4"
        assert project.video_duration == 120.5
        assert project.output_dir == "/output"

    def test_to_dict(self):
        """测试转换为字典"""
        project = BaseProject(
            name="测试项目",
            video_duration=60.0,
        )
        
        data = asdict(project)
        
        assert data["name"] == "测试项目"
        assert data["video_duration"] == 60.0


class TestProgressMixin:
    """测试进度回调混入"""

    def test_init(self):
        """测试初始化"""
        mixin = ProgressMixin()
        
        assert mixin._progress_callback is None

    def test_set_callback(self):
        """测试设置回调"""
        mixin = ProgressMixin()
        callback = Mock()
        
        mixin.set_progress_callback(callback)
        
        assert mixin._progress_callback is callback

    def test_report_progress_with_callback(self):
        """测试报告进度（有回调）"""
        mixin = ProgressMixin()
        callback = Mock()
        mixin.set_progress_callback(callback)
        
        mixin._report_progress("测试阶段", 0.5)
        
        callback.assert_called_once_with("测试阶段", 0.5)

    def test_report_progress_without_callback(self):
        """测试报告进度（无回调）"""
        mixin = ProgressMixin()
        
        # 不应该抛出异常
        mixin._report_progress("测试阶段", 0.5)


class MockVideoMaker(BaseVideoMaker):
    """模拟视频制作器用于测试"""
    
    def create_project(self, source_video, name=None, output_dir=None, **kwargs):
        return BaseProject()


class TestBaseVideoMaker:
    """测试视频制作器基类"""

    def test_init(self):
        """测试初始化"""
        maker = MockVideoMaker()
        
        assert maker.scene_analyzer is not None
        assert maker.jianying_exporter is not None

    def test_inheritance(self):
        """测试继承"""
        maker = MockVideoMaker()
        
        # 应该包含 ProgressMixin 的功能
        assert hasattr(maker, '_progress_callback')
        assert hasattr(maker, 'set_progress_callback')
        assert hasattr(maker, '_report_progress')

    def test_progress_callback_integration(self):
        """测试进度回调集成"""
        maker = MockVideoMaker()
        progress_values = []
        
        def callback(stage, progress):
            progress_values.append((stage, progress))
        
        maker.set_progress_callback(callback)
        maker._report_progress("开始", 0.0)
        maker._report_progress("进行中", 0.5)
        maker._report_progress("完成", 1.0)
        
        assert len(progress_values) == 3
        assert progress_values[0] == ("开始", 0.0)
        assert progress_values[1] == ("进行中", 0.5)
        assert progress_values[2] == ("完成", 1.0)
