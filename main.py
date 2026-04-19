#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore - AI Video Editor
入口点：将启动工作委托给 app.main

用法:
    python main.py           # GUI 模式（默认）
    python main.py --cli     # 命令行模式
    python main.py --help    # 帮助信息
"""

import sys
import os

# 确保项目根目录在 Python 路径中
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# 引导到真正的入口
from app.main import main as app_main

if __name__ == "__main__":
    sys.exit(app_main())
