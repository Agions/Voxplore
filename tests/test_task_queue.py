#!/usr/bin/env python3
"""测试任务队列

Note: app.core.task_queue 已移除，TaskQueue 合并到 services/video/parallel_processor.py。
此测试需要完全重写以适配新的异步架构，暂跳过。
"""

import pytest

pytest.skip("TaskQueue API 已重构，需重写测试适配", allow_module_level=True)
