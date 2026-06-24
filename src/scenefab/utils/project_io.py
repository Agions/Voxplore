"""
项目/模板 I/O 工具

提取 ProjectManager 和 ProjectTemplateManager 共享的：
- 项目子目录常量
- ZIP 导入/导出
- 错误处理装饰器
"""

from __future__ import annotations

import functools
import json
import logging
import shutil
import zipfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 项目标准子目录
PROJECT_SUBDIRS = ["media", "exports", "backups", "cache", "assets"]


def ensure_directories(*dirs: Path | str) -> None:
    """确保所有目录存在"""
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


def export_to_zip(
    source_dir: str | Path,
    export_path: str | Path,
    extra_info: dict[str, Any] | None = None,
    file_filter: Callable[[Path], bool] | None = None,
) -> None:
    """
    将目录导出为 ZIP 文件。

    Args:
        source_dir: 源目录
        export_path: 输出 ZIP 路径
        extra_info: 额外的 export_info.json 内容
        file_filter: 文件过滤函数（返回 True 表示包含）
    """
    source_dir = Path(source_dir)
    with zipfile.ZipFile(str(export_path), "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                if file_filter and not file_filter(file_path):
                    continue
                arcname = file_path.relative_to(source_dir)
                zipf.write(file_path, str(arcname))
        export_info = {
            "exported_at": datetime.now().isoformat(),
            "cineai_version": "2.0.0",
            **(extra_info or {}),
        }
        zipf.writestr("export_info.json", json.dumps(export_info, indent=2))


def import_from_zip(
    import_path: str | Path,
    temp_dir: str | Path,
    final_dest: str | Path,
    required_file: str = "export_info.json",
) -> Path | None:
    """
    从 ZIP 文件导入。

    Args:
        import_path: ZIP 文件路径
        temp_dir: 临时解压目录
        final_dest: 最终目标目录
        required_file: ZIP 中必须存在的文件

    Returns:
        最终目标目录路径，失败返回 None
    """
    temp_dir = Path(temp_dir)
    final_dest = Path(final_dest)
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(str(import_path), "r") as zipf:
            zipf.extractall(str(temp_dir))
        required_path = temp_dir / required_file
        if not required_path.exists():
            logger.error(f"Invalid import: missing {required_file}")
            return None
        shutil.copytree(str(temp_dir), str(final_dest))
        return final_dest
    finally:
        if temp_dir.exists():
            shutil.rmtree(str(temp_dir))


def handle_error(action_code: str, action_name: str):
    """
    统一错误处理装饰器。

    捕获异常、记录日志、发送 error_occurred 信号、返回默认值。
    适用于所有返回 bool / Optional[str] 的方法。
    """

    def decorator(method: Callable) -> Callable:
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            try:
                return method(self, *args, **kwargs)
            except Exception as e:
                self.logger.error(f"Failed to {action_name}: {e}")
                self.error_occurred.emit(
                    f"{action_code}_ERROR", f"{action_name}失败: {str(e)}"
                )
                hints = {"bool": False, "str": None}
                ret_type = method.__annotations__.get("return", "")
                return hints.get(
                    str(ret_type).split("'")[1] if "'" in str(ret_type) else ""
                )

        return wrapper

    return decorator


__all__ = [
    "PROJECT_SUBDIRS",
    "ensure_directories",
    "export_to_zip",
    "import_from_zip",
    "handle_error",
]
