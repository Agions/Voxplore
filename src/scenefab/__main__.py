#!/usr/bin/env python3
"""
SceneFab 主入口 - 支持 `python -m scenefab` 和直接执行
"""
import sys
from pathlib import Path

# src/scenefab/ 的 parent 是 src/, grandparent 是项目根目录
_src_dir = Path(__file__).resolve().parent.parent
_root_dir = _src_dir.parent
if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

from scenefab.main import main

if __name__ == "__main__":
    sys.exit(main())
