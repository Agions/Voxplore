#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
单元测试 - 版本管理
"""

import pytest
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.utils.version import Version, get_version, get_version_string


class TestVersion:
    """测试 Version 类"""

    def test_parse_standard(self):
        """测试解析标准版本"""
        v = Version.parse("2.0.0")
        assert v.major == 2
        assert v.minor == 0
        assert v.patch == 0
        assert str(v) == "2.0.0"

    def test_parse_prerelease(self):
        """测试解析 prerelease 版本"""
        v = Version.parse("2.0.0-rc.1")
        assert v.major == 2
        assert v.minor == 0
        assert v.patch == 0
        assert v.prerelease == "rc.1"
        assert str(v) == "2.0.0-rc.1"

    def test_parse_with_build(self):
        """测试解析带 build 版本"""
        v = Version.parse("2.0.0+20260214")
        assert v.major == 2
        assert v.minor == 0
        assert v.patch == 0
        assert v.build == "20260214"
        assert str(v) == "2.0.0+20260214"

    def test_parse_invalid(self):
        """测试解析无效版本"""
        with pytest.raises(ValueError):
            Version.parse("invalid")

    def test_string_representation(self):
        """测试字符串表示"""
        assert str(Version(2, 0, 0)) == "2.0.0"
        assert str(Version(1, 2, 3, "rc.1")) == "1.2.3-rc.1"
        assert str(Version(1, 2, 3, "", "build")) == "1.2.3+build"


class TestVersionFunctions:
    """测试版本函数"""

    def test_get_version_string(self):
        """测试获取版本字符串"""
        version_str = get_version_string()
        assert version_str
        assert isinstance(version_str, str)

    def test_get_version(self):
        """测试获取版本对象"""
        version = get_version()
        assert version.major >= 0
        assert version.minor >= 0
        assert version.patch >= 0
