#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 应用启动器 ⚠️ 已废弃

此文件已废弃，不应直接使用。

请使用以下入口之一:
    - python main.py           # 推荐
    - python app/main.py        # 直接入口

此文件将在未来版本中移除。
"""

import warnings
warnings.warn(
    "application_launcher.py is deprecated. Use main.py or app/main.py instead.",
    DeprecationWarning,
    stacklevel=2
)

# 转发到真正的入口
from app.main import main as app_main

if __name__ == "__main__":
    import sys
    sys.exit(app_main())
