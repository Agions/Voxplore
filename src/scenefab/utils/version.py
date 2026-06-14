#!/usr/bin/env python3

import re
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import NamedTuple

DEFAULT_VERSION = "2.1.1"
PACKAGE_NAME = "scenefab"


def _load_toml():
    try:
        import tomllib  # type: ignore[import-not-found]

        return tomllib
    except ImportError:
        try:
            import tomli  # type: ignore[import-not-found]

            return tomli
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


def _read_pyproject_version() -> str | None:
    toml = _load_toml()
    if toml is None:
        return None

    for parent in Path(__file__).resolve().parents:
        pyproject_path = parent / "pyproject.toml"
        if not pyproject_path.exists():
            continue
        try:
            with open(pyproject_path, "rb") as f:
                return str(toml.load(f)["project"]["version"])
        except (OSError, KeyError, TypeError, ValueError):
            return None
    return None


def _read_installed_version() -> str | None:
    try:
        return importlib_metadata.version(PACKAGE_NAME)
    except importlib_metadata.PackageNotFoundError:
        return None


def get_version_string() -> str:
    """获取版本字符串。"""
    return _read_pyproject_version() or _read_installed_version() or DEFAULT_VERSION


def get_version() -> Version:
    """获取版本对象。"""
    return Version.parse(get_version_string())


# 便捷导出
VERSION = get_version()
__version__ = str(VERSION)


if __name__ == "__main__":
    print(__version__)
