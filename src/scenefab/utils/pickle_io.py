"""安全 pickle 文件读写工具。"""

from __future__ import annotations

import os
import pickle
import stat
from pathlib import Path
from typing import Any

OWNER_READ_WRITE = stat.S_IRUSR | stat.S_IWUSR
INSECURE_PICKLE_PERMISSIONS = (
    stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH
)


def safe_pickle_load(file_path: Path) -> Any:
    """只读取当前用户私有的 pickle 文件。"""
    file_stat = file_path.stat()
    if file_stat.st_mode & INSECURE_PICKLE_PERMISSIONS:
        raise PermissionError(f"Cache file {file_path} has insecure permissions")
    if os.getuid() != file_stat.st_uid:
        raise PermissionError(f"Cache file {file_path} not owned by current user")
    with open(file_path, "rb") as f:
        return pickle.load(f)


def safe_pickle_dump(value: Any, file_path: Path) -> None:
    """写入 owner-only 权限的 pickle 文件。"""
    with open(file_path, "wb") as f:
        pickle.dump(value, f)
    os.chmod(file_path, OWNER_READ_WRITE)


__all__ = ["safe_pickle_dump", "safe_pickle_load"]
