# Task 7: 删除冗余脚本

## 位置
项目根目录: `/Users/zfkc/Desktop/04-AI/scene-fab`

## 任务描述
删除 3 个冗余脚本/文件，并合并根目录 conftest 的 GUI 跳过逻辑到 tests/conftest.py。

## 执行步骤

### Step 1: 删除冗余脚本

```bash
rm scripts/build.py
rm main.spec
rm conftest.py
```

### Step 2: 更新 tests/conftest.py（合并根目录 conftest 的 GUI 跳过逻辑）

**File:** `tests/conftest.py`

Replace the entire file content with:

```python
"""Shared pytest fixtures and configuration."""

from unittest.mock import patch
import pytest

# ── PySide6 GUI 测试跳过 ──────────────────────────────────────
_PYSIDE6_GUI_TESTS = [
    "tests/test_project_manager.py",
    "tests/test_settings_mgr.py",
    "tests/test_template_mgr.py",
]

try:
    from PySide6 import QtCore  # noqa: F401
except ImportError:
    collect_ignore = _PYSIDE6_GUI_TESTS

# ── FFmpeg mock ───────────────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_ffmpeg_check():
    with patch("scenefab.services.video.ffmpeg_tool.FFmpegTool.check_ffmpeg"):
        yield
```

**Important:** The old file already has the FFmpeg mock fixture. The only addition is the PySide6 GUI test skip logic from the root `conftest.py`. Make sure both sections are present.

### Step 3: 验证

```bash
test ! -f scripts/build.py && echo "OK: build.py deleted"
test ! -f main.spec && echo "OK: main.spec deleted"
test ! -f conftest.py && echo "OK: root conftest.py deleted"

echo "=== tests/conftest.py content ==="
cat tests/conftest.py
```

### Step 4: Commit

```bash
git add -A
git commit -m "chore: 删除冗余脚本 build.py main.spec 和根目录 conftest.py"
```

## 验证
执行 Step 3 确认 3 个文件已删除，tests/conftest.py 包含 GUI 跳过逻辑。

## 全局约束
- 只删除指定文件，不删除其他文件
- tests/conftest.py 必须包含 PySide6 GUI 跳过逻辑和 FFmpeg mock 两个部分
