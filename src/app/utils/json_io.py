"""
统一 JSON I/O 工具

自动选择 orjson（高性能）或标准 json，提供原子写入。
项目中所有 JSON 文件读写应统一使用本模块。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# orjson 比标准 json 快 5-10 倍
try:
    import orjson

    _use_orjson = True
except ImportError:
    _use_orjson = False


def read_json(path: str | Path) -> Any:
    """
    读取 JSON 文件。

    自动选择 orjson（二进制模式）或标准 json（文本模式）。

    Args:
        path: 文件路径

    Returns:
        解析后的 Python 对象
    """
    if _use_orjson:
        with open(path, "rb") as f:
            return orjson.loads(f.read())
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(
    path: str | Path,
    data: Any,
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> None:
    """
    写入 JSON 文件（原子替换）。

    先写入临时文件再 os.replace，防止写入中途崩溃导致文件损坏。

    Args:
        path: 文件路径
        data: 要序列化的 Python 对象
        indent: 缩进级别（仅标准 json 生效，orjson 始终使用 OPT_INDENT_2）
        ensure_ascii: 是否转义非 ASCII 字符（仅标准 json 生效）
    """
    path = str(path)
    temp = path + ".tmp"
    if _use_orjson:
        with open(temp, "wb") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    else:
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
    os.replace(temp, path)


__all__ = ["read_json", "write_json"]
