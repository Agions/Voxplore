# Task 12: 最终验证

## 位置
项目根目录: `/Users/zfkc/Desktop/04-AI/scene-fab`

## 任务描述
运行 pytest、ruff 检查、导入验证和长文件名检查，确认所有改造完成且项目正常运行。

## 执行步骤

### Step 1: 运行 pytest（排除集成测试）

```bash
PYTHONPATH=src python3 -m pytest tests/ --ignore=tests/test_integration.py -q
```

Expected: Tests pass (or only known pre-existing failures). Report the actual result.

### Step 2: ruff 检查

```bash
ruff check src/scenefab tests
```

Expected: No errors (or only pre-existing ones). Report the actual result.

### Step 3: 关键模块导入验证

```bash
python3 -c "
from scenefab.settings.config import ConfigManager
from scenefab.settings.manager import ProjectSettingsManager
from scenefab.project.manager import ProjectManager
from scenefab.project.template_mgr import TemplateManager
from scenefab.pipeline.narration.engine import NarrationStateMachine
from scenefab.pipeline.fp_workflow import FIRST_PERSON_WORKFLOW
from scenefab.services.video.ffmpeg_tool import FFmpegTool
from scenefab.services.video.caption_gen import CaptionGenerator
from scenefab.services.export.video_exporter import DirectVideoExporter
from scenefab.services.export.batch_export import BatchExportManager
from scenefab.core.stream_worker import StreamingLLMWorker
from scenefab.models.file_metadata import ProjectFileMetadata
print('All imports OK')
"
```

Expected: `All imports OK` printed without errors.

### Step 4: 验证无长文件名（src/）

```bash
python3 -c "
import os
long_files = []
for root, dirs, files in os.walk('src/scenefab'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if f.endswith('.py') and len(f.replace('.py', '')) > 25:
            long_files.append(os.path.join(root, f))
if long_files:
    print('FAIL: 长文件名残留:')
    for f in long_files:
        print(f'  {f}')
else:
    print('OK: src/ 无长文件名')
"
```

Expected: `OK: src/ 无长文件名`

### Step 5: 验证无长文件名（tests/）

```bash
python3 -c "
import os
long_files = []
for root, dirs, files in os.walk('tests'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if f.endswith('.py') and len(f.replace('.py', '')) > 25:
            long_files.append(os.path.join(root, f))
if long_files:
    print('FAIL: 测试长文件名残留:')
    for f in long_files:
        print(f'  {f}')
else:
    print('OK: tests/ 无长文件名')
"
```

Expected: `OK: tests/ 无长文件名`

### Step 6: 验证旧文件不存在

```bash
echo "=== 关键旧路径 ==="
test ! -f src/scenefab/settings.py && echo "OK: settings.py gone" || echo "FAIL"
test ! -f src/scenefab/project_manager.py && echo "OK: project_manager.py gone" || echo "FAIL"
test ! -d src/scenefab/services/video_tools && echo "OK: video_tools/ gone" || echo "FAIL"
test ! -f src/scenefab/pipeline/first_person_workflow.py && echo "OK: first_person_workflow.py gone" || echo "FAIL"
test ! -f scripts/build.py && echo "OK: build.py gone" || echo "FAIL"
test ! -f main.spec && echo "OK: main.spec gone" || echo "FAIL"
test ! -f conftest.py && echo "OK: root conftest.py gone" || echo "FAIL"
test ! -f docs/guide/first-person-narration-production.md && echo "OK: old doc gone" || echo "FAIL"
```

All should print "OK".

### Step 7: Commit

```bash
git add -A
git commit -m "chore: 最终验证 — pytest + ruff + 导入检查通过"
```

## 验证
执行 Step 1-6 并报告所有结果。如果有任何 FAIL，详细说明。

## 全局约束
- 必须所有验证通过才能标记项目合规化完成
- 如果 pytest 有失败，需要区分是预存在的还是本次引入的
