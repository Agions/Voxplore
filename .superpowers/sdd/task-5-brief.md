# Task 5: 更新 tests/ 内绝对 import

## 位置
项目根目录: `/Users/zfkc/Desktop/04-AI/scene-fab`

## 任务描述
更新 `tests/` 内所有引用旧模块路径的 import 语句，共涉及 15 个测试文件 + 1 个 conftest，约 35 处 import。

## 执行步骤

### Step 1: 替换 tests/ 中的 settings/ import

**Files:**
- `tests/test_config_manager.py` (line 4)
- `tests/test_issue82_regression.py` (line 39)

```bash
sed -i '' 's/from scenefab\.settings import ConfigManager/from scenefab.settings.config import ConfigManager/g' \
  tests/test_issue82_regression.py

python3 -c "
p = 'tests/test_config_manager.py'
t = open(p).read()
t = t.replace('from scenefab.settings import (', 'from scenefab.settings.config import (')
open(p, 'w').write(t)
print('OK: test_config_manager.py')
"
```

### Step 2: 替换 tests/ 中的 project/ import

**Files:**
- `tests/test_project_manager.py` (line 4)
- `tests/test_project_template_manager.py` (lines 10-11)

```bash
sed -i '' 's/from scenefab\.project_manager import/from scenefab.project.manager import/g' \
  tests/test_project_manager.py

python3 -c "
p = 'tests/test_project_template_manager.py'
t = open(p).read()
t = t.replace('from scenefab.project_manager import Project', 'from scenefab.project.manager import Project')
t = t.replace('from scenefab.project_template_manager import (', 'from scenefab.project.template_mgr import (')
open(p, 'w').write(t)
print('OK: test_project_template_manager.py')
"
```

### Step 3: 替换 tests/ 中的 narration/ import

**Files:** test_understanding_steps.py, test_narration_state_machine.py, test_evaluation_steps.py, test_assembly_steps.py, test_text_utils.py

```bash
python3 -c "
files = {
    'tests/test_understanding_steps.py': [
        ('from scenefab.pipeline.narration import (', 'from scenefab.pipeline.narration.engine import ('),
        ('from scenefab.pipeline.narration import HistorySegment', 'from scenefab.pipeline.narration.engine import HistorySegment'),
    ],
    'tests/test_narration_state_machine.py': [
        ('from scenefab.pipeline.narration import (', 'from scenefab.pipeline.narration.engine import ('),
        ('from scenefab.pipeline.narration import HistorySegment', 'from scenefab.pipeline.narration.engine import HistorySegment'),
        ('from scenefab.pipeline.narration import NarrationContext', 'from scenefab.pipeline.narration.engine import NarrationContext'),
        ('from scenefab.pipeline.narration_steps import ingest_step', 'from scenefab.pipeline.narration.steps import ingest_step'),
        ('from scenefab.pipeline.narration_steps import reject_step', 'from scenefab.pipeline.narration.steps import reject_step'),
    ],
    'tests/test_evaluation_steps.py': [
        ('from scenefab.pipeline.narration import (', 'from scenefab.pipeline.narration.engine import ('),
        ('from scenefab.pipeline.narration_evaluator import DIMENSION_WEIGHTS', 'from scenefab.pipeline.narration.evaluator import DIMENSION_WEIGHTS'),
        ('\"scenefab.pipeline.narration_evaluator.NarrationEvaluator.evaluate\"', '\"scenefab.pipeline.narration.evaluator.NarrationEvaluator.evaluate\"'),
        ('from scenefab.pipeline.narration_state_machine import (', 'from scenefab.pipeline.narration.state_machine import ('),
    ],
    'tests/test_assembly_steps.py': [
        ('from scenefab.pipeline.narration import (', 'from scenefab.pipeline.narration.engine import ('),
    ],
    'tests/test_text_utils.py': [
        ('from scenefab.pipeline.narration_context import ProductionStyle', 'from scenefab.pipeline.narration.context import ProductionStyle'),
    ],
}
for fpath, replacements in files.items():
    t = open(fpath).read()
    for old, new in replacements:
        t = t.replace(old, new)
    open(fpath, 'w').write(t)
    print(f'OK: {fpath}')
"
```

### Step 4: 替换 tests/ 中的 video_tools import

**Files:** tests/conftest.py, test_ffmpeg_tool.py, test_caption_generator.py

```bash
# conftest.py
sed -i '' 's/scenefab\.services\.video_tools/scenefab.services.video/g' \
  tests/conftest.py

# test_ffmpeg_tool.py (4 处)
python3 -c "
p = 'tests/test_ffmpeg_tool.py'
t = open(p).read()
t = t.replace('from scenefab.services.video_tools.ffmpeg_tool import FFmpegTool', 'from scenefab.services.video.ffmpeg_tool import FFmpegTool')
t = t.replace('from scenefab.services.video_tools import hardware', 'from scenefab.services.video import hardware')
t = t.replace('from scenefab.services.video_tools.ffmpeg_tool import HWAccelType', 'from scenefab.services.video.ffmpeg_tool import HWAccelType')
t = t.replace('from scenefab.services.video_tools import probe', 'from scenefab.services.video import probe')
open(p, 'w').write(t)
print('OK: test_ffmpeg_tool.py')
"

# test_caption_generator.py
python3 -c "
p = 'tests/test_caption_generator.py'
t = open(p).read()
t = t.replace('from scenefab.services.video_tools.caption_generator import (', 'from scenefab.services.video.caption_gen import (')
open(p, 'w').write(t)
print('OK: test_caption_generator.py')
"
```

### Step 5: 替换 first_person_workflow 和 direct_video_exporter

**Files:** test_first_person_workflow.py, test_direct_video_exporter.py, test_batch_export_manager.py, test_smoke_pipeline.py

```bash
# test_first_person_workflow.py
python3 -c "
p = 'tests/test_first_person_workflow.py'
t = open(p).read()
t = t.replace('from scenefab.pipeline.first_person_workflow import (', 'from scenefab.pipeline.fp_workflow import (')
open(p, 'w').write(t)
print('OK: test_first_person_workflow.py')
"

# test_direct_video_exporter.py
python3 -c "
p = 'tests/test_direct_video_exporter.py'
t = open(p).read()
t = t.replace('from scenefab.services.export.direct_video_exporter import (', 'from scenefab.services.export.video_exporter import (')
open(p, 'w').write(t)
print('OK: test_direct_video_exporter.py')
"

# test_batch_export_manager.py
python3 -c "
p = 'tests/test_batch_export_manager.py'
t = open(p).read()
t = t.replace('from scenefab.services.export.batch_export_manager import BatchExportManager', 'from scenefab.services.export.batch_export import BatchExportManager')
open(p, 'w').write(t)
print('OK: test_batch_export_manager.py')
"

# test_smoke_pipeline.py (7 处)
python3 -c "
p = 'tests/test_smoke_pipeline.py'
t = open(p).read()
t = t.replace('scenefab.services.export.direct_video_exporter', 'scenefab.services.export.video_exporter')
open(p, 'w').write(t)
print('OK: test_smoke_pipeline.py')
"
```

### Step 6: 验证无残留旧路径引用

```bash
echo "=== video_tools ==="
grep -rn "video_tools" tests/ --include='*.py' | grep -v "test_first_person_workflow.py" | grep -v "test_direct_video_exporter.py" && echo "FAIL" || echo "OK"
echo "=== first_person_workflow ==="
grep -rn "first_person_workflow" tests/ --include='*.py' | grep -v "test_first_person_workflow.py" && echo "FAIL" || echo "OK"
echo "=== direct_video_exporter ==="
grep -rn "direct_video_exporter" tests/ --include='*.py' | grep -v "test_direct_video_exporter.py" | grep -v "test_smoke_pipeline.py" && echo "FAIL" || echo "OK"
echo "=== batch_export_manager ==="
grep -rn "batch_export_manager" tests/ --include='*.py' | grep -v "test_batch_export_manager.py" && echo "FAIL" || echo "OK"
```

All greps should return "OK" (no matches).

### Step 7: Commit

```bash
git add -A
git commit -m "refactor: 更新 tests/ 内 35 处 import 到新路径"
```

## 验证
执行 Step 6 确认无残留旧路径引用。

## 全局约束
- 只修改 import 路径，不改变导入的符号名
- 不做功能变更
- 所有 grep 验证必须通过才能 commit
