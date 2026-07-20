#!/usr/bin/env python3
"""测试导出工具函数"""

from scenefab.services.export.export_utils import (
    ensure_directory,
    ensure_parent_directory,
    safe_filename,
    seconds_to_microseconds,
    write_json_file,
)


class TestTimeConversion:
    """测试时间转换函数"""

    def test_seconds_to_microseconds(self):
        """测试秒转微秒"""
        assert seconds_to_microseconds(1.0) == 1_000_000
        assert seconds_to_microseconds(0.5) == 500_000
        assert seconds_to_microseconds(0) == 0


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


class TestFileHelpers:
    """测试导出文件工具"""

    def test_ensure_directory_creates_nested_path(self, tmp_path):
        target = tmp_path / "exports" / "nested"

        result = ensure_directory(target)

        assert result == target
        assert target.is_dir()

    def test_ensure_parent_directory_creates_parent(self, tmp_path):
        output_path = tmp_path / "exports" / "video.mp4"

        result = ensure_parent_directory(output_path)

        assert result == output_path
        assert output_path.parent.is_dir()

    def test_write_json_file(self, tmp_path):
        output = tmp_path / "data.json"

        write_json_file(output, {"name": "测试"})

        assert output.read_text(encoding="utf-8") == '{\n  "name": "测试"\n}'
