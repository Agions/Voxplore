#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
版本一致性检查工具
检查项目各处版本号是否一致
"""

import sys
from pathlib import Path


# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def _safe_import():
    """安全导入"""
    try:
        import tomli
        return tomli
    except ImportError:
        try:
            import tomllib
            return tomllib
        except ImportError:
            return None


def check_version() -> bool:
    """
    检查版本一致性

    Returns:
        是否一致
    """
    print("检查项目版本一致性...")
    print("=" * 50)

    # 从版本模块读取
    from app.utils.version import get_version

    version = get_version()
    version_str = str(version)

    print(f"版本模块: {version_str}")
    print(f"  - {version.major}.{version.minor}.{version.patch}")
    if version.prerelease:
        print(f"  - prerelease: {version.prerelease}")
    if version.build:
        print(f"  - build: {version.build}")

    # 从 pyproject.toml 读取
    pyproject_path = project_root / "pyproject.toml"

    print("\npyproject.toml:")

    if not pyproject_path.exists():
        print("  ❌ 文件不存在!")
        return False

    tomli = _safe_import()
    if not tomli:
        print("  ❌ 无法导入 tomli/tomllib!")
        return False

    with open(pyproject_path, "rb") as f:
        data = tomli.load(f)

    pyproject_version = data["project"]["version"]
    print(f"  - version: {pyproject_version}")

    # 检查一致性
    print("\n" + "=" * 50)

    if version_str == pyproject_version:
        print("✅ 版本一致!")
        return True
    else:
        print("❌ 版本不一致!")
        print(f"  版本模块: {version_str}")
        print(f"  pyproject.toml: {pyproject_version}")
        return False


if __name__ == "__main__":
    success = check_version()
    sys.exit(0 if success else 1)
