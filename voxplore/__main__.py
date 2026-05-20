#!/usr/bin/env python3
"""
Voxplore 主入口
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voxplore.cli import main

if __name__ == "__main__":
    sys.exit(main())
