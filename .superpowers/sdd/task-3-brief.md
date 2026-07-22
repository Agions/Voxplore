# Task 3: 更新 __init__.py 导出映射

## 位置
项目根目录: `/Users/zfkc/Desktop/04-AI/scene-fab`

## 任务描述
更新 4 个 `__init__.py` 文件的导出映射，使它们引用新的文件路径。

## 执行步骤

### Step 1: 更新 pipeline/__init__.py

**File:** `src/scenefab/pipeline/__init__.py`

**Changes:**
- Line 10: `from .first_person_workflow import (` → `from .fp_workflow import (`
- Line 18: `from .narration import (` → `from .narration.engine import (`

Keep all the imported names identical. Only change the source module paths.

### Step 2: 更新 services/export/__init__.py

**File:** `src/scenefab/services/export/__init__.py`

**Changes:**
- Line 9: `from .batch_export_manager import (` → `from .batch_export import (`
- Line 16: `from .direct_video_exporter import (` → `from .video_exporter import (`

Keep all the imported names identical.

### Step 3: 更新 core/__init__.py lazy import 映射

**File:** `src/scenefab/core/__init__.py`

**Change:**
- Line 23: `"StreamingLLMWorker": ("scenefab.core.streaming_llm_worker", "StreamingLLMWorker")` → `"StreamingLLMWorker": ("scenefab.core.stream_worker", "StreamingLLMWorker")`

Only change the module path string. Keep the attribute name `"StreamingLLMWorker"` unchanged.

### Step 4: 更新 services/video/__init__.py

**File:** `src/scenefab/services/video/__init__.py`

**Changes:**
- Line 13: `from .base import (` → `from .tool_base import (`
- Line 19: `from .caption_generator import (` → `from .caption_gen import (`

Keep all the imported names identical.

### Step 5: 验证所有 __init__.py 无旧路径残留

```bash
echo "=== pipeline/__init__.py ==="
grep -n "first_person_workflow\|from \.narration\b" src/scenefab/pipeline/__init__.py || echo "OK"
echo "=== services/export/__init__.py ==="
grep -n "batch_export_manager\|direct_video_exporter" src/scenefab/services/export/__init__.py || echo "OK"
echo "=== core/__init__.py ==="
grep -n "streaming_llm_worker" src/scenefab/core/__init__.py || echo "OK"
echo "=== services/video/__init__.py ==="
grep -n "from \.base import\|from \.caption_generator import" src/scenefab/services/video/__init__.py || echo "OK"
```

Each grep should return nothing (no matches), confirming old paths are gone.

### Step 6: Commit

```bash
git add -A
git commit -m "refactor: 更新 __init__.py 导出映射到新路径"
```

## 验证
执行 Step 5 确认 4 个 __init__.py 中无旧路径引用。

## 全局约束
- 只修改 import 路径，不改变导入的符号名
- 不做功能变更
