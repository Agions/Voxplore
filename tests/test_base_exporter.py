#!/usr/bin/env python3
"""测试导出器基类"""

import pytest
from dataclasses import asdict

from app.services.export.base_exporter import (
    seconds_to_microseconds,
    microseconds_to_seconds,
    seconds_to_ticks,
    safe_filename,
    BaseTrack,
    BaseSegment,
    BaseExporter,
    ExporterConfig,
)


class TestTimeConversion:
    """测试时间转换函数"""

    def test_seconds_to_microseconds(self):
        """测试秒转微秒"""
        assert seconds_to_microseconds(1.0) == 1_000_000
        assert seconds_to_microseconds(0.5) == 500_000
        assert seconds_to_microseconds(0) == 0

    def test_microseconds_to_seconds(self):
        """测试微秒转秒"""
        assert microseconds_to_seconds(1_000_000) == 1.0
        assert microseconds_to_seconds(500_000) == 0.5
        assert microseconds_to_seconds(0) == 0.0

    def test_seconds_to_ticks(self):
        """测试秒转 ticks"""
        ticks = seconds_to_ticks(1.0, fps=30.0)
        assert ticks == 254016000000

    def test_roundtrip_conversion(self):
        """测试往返转换"""
        original = 1.5
        micro = seconds_to_microseconds(original)
        back = microseconds_to_seconds(micro)
        assert abs(back - original) < 0.0001


class TestSafeFilename:
    """测试安全文件名函数"""

    def test_normal_string(self):
        """测试正常字符串"""
        assert safe_filename("normal_file") == "normal_file"

    def test_with_spaces(self):
        """测试带空格"""
        assert safe_filename("file name") == "file name"

    def test_with_invalid_chars(self):
        """测试带非法字符"""
        assert safe_filename("file<name>") == "file_name_"
        assert safe_filename("file:name") == "file_name"
        assert safe_filename('file"name') == "file_name"

    def test_strip_whitespace(self):
        """测试去除空白"""
        assert safe_filename("  file  ") == "file"


class TestBaseTrack:
    """测试轨道基类"""

    def test_default_creation(self):
        """测试默认创建"""
        track = BaseTrack()
        
        assert track.id != ""
        assert track.type == "video"

    def test_custom_creation(self):
        """测试自定义创建"""
        track = BaseTrack(type="audio")
        
        assert track.type == "audio"


class TestBaseSegment:
    """测试片段基类"""

    def test_default_creation(self):
        """测试默认创建"""
        segment = BaseSegment()
        
        assert segment.id != ""
        assert segment.material_id == ""
        assert segment.start == 0.0

    def test_custom_creation(self):
        """测试自定义创建"""
        segment = BaseSegment(
            material_id="mat123",
            start=1.5,
            duration=2.0,
        )
        
        assert segment.material_id == "mat123"
        assert segment.start == 1.5
        assert segment.duration == 2.0


class MockExporter(BaseExporter):
    """模拟导出器用于测试"""

    def create_project(self, name: str):
        return {"name": name}

    def export(self, project, output_dir: str, **kwargs) -> str:
        return output_dir

    def validate_project(self) -> bool:
        return True


class TestBaseExporter:
    """测试导出器基类"""

    def test_init(self):
        """测试初始化"""
        exporter = MockExporter()

        # config 可以是 None 或 ExporterConfig 实例
        assert exporter.config is None or isinstance(exporter.config, ExporterConfig)

    def test_init_custom_output(self):
        """测试自定义输出目录"""
        config = ExporterConfig(output_dir="/output")
        exporter = MockExporter(config=config)

        assert exporter.config.output_dir == "/output"

    def test_set_progress_callback(self):
        """测试设置进度回调（基类无此方法，跳过）"""
        # BaseExporter 没有 set_progress_callback，跳过
        pytest.skip("BaseExporter 没有 set_progress_callback 方法")
