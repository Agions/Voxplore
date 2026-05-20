#!/usr/bin/env python3
"""
Voxplore 主入口 - 支持 `python -m voxplore` 和直接执行
"""
import sys
import os
from pathlib import Path

# 确保 src/ 目录在 path 中（支持直接执行）
_src_dir = Path(__file__).resolve().parent.parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from core.cli import main

if __name__ == "__main__":
    sys.exit(main())
