#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 版本管理
从 pyproject.toml 读取版本信息
"""

from pathlib import Path
from typing import NamedTuple
import re


def _safe_import():
    """安全导入 tomli"""
    try:
        import tomli
        return tomli
    except ImportError:
        try:
            import tomllib
            return tomllib
        except ImportError:
            return None


class Version(NamedTuple):
    """版本信息"""

    major: int
    minor: int
    patch: int
    prerelease: str = ""
    build: str = ""

    def __str__(self) -> str:
        """字符串表示"""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    @classmethod
    def parse(cls, version_str: str) -> "Version":
        """
        解析版本字符串

        Args:
            version_str: 版本字符串

        Returns:
            版本信息

        Raises:
            ValueError: 无效的版本字符串
        """
        # 匹配: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
        pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-(.+?))?(?:\+(.+)?)?$"
        match = re.match(pattern, version_str)

        if not match:
            raise ValueError(f"Invalid version: {version_str}")

        major, minor, patch, prerelease, build = match.groups()

        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            prerelease=prerelease or "",
            build=build or "",
        )


def get_version() -> Version:
    """
    从 pyproject.toml 读取版本

    Returns:
        版本信息
    """
    try:
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

        if pyproject_path.exists():
            tomli = _safe_import()

            if tomli:
                with open(pyproject_path, "rb") as f:
                    data = tomli.load(f)

                version_str = data["project"]["version"]
                return Version.parse(version_str)

    except Exception as e:
        print(f"Warning: Failed to read version from pyproject.toml: {e}")

    # 后备方案: 返回默认版本
    return Version(2, 0, 0, prerelease="rc.1")


def get_version_string() -> str:
    """
    获取版本字符串

    Returns:
        版本字符串
    """
    return str(get_version())


# 便捷导出
VERSION = get_version()
__version__ = VERSION


if __name__ == "__main__":
    print(__version__)
