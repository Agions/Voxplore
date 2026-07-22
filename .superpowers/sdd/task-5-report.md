# Task 5 Report: 更新 tests/ 内 import 到新路径

## 完成状态
DONE

## Commit
- **Hash:** `da51fdbbf6ecfd25d6cbf80003fce8834774efcf`
- **Message:** `refactor: 更新 tests/ 内 35 处 import 到新路径`
- **Files changed:** 19 files changed, 160 insertions(+), 37 deletions(-)

## 执行的 7 个步骤

### Step 1: 替换 settings/ import
- `tests/test_issue82_regression.py`: `scenefab.settings import ConfigManager` → `scenefab.settings.config import ConfigManager`
- `tests/test_config_manager.py`: `from scenefab.settings import (` → `from scenefab.settings.config import (`

### Step 2: 替换 project/ import
- `tests/test_project_manager.py`: `scenefab.project_manager import` → `scenefab.project.manager import`
- `tests/test_project_template_manager.py`: `scenefab.project_manager import Project` → `scenefab.project.manager import Project`
- `tests/test_project_template_manager.py`: `scenefab.project_template_manager import (` → `scenefab.project.template_mgr import (`

### Step 3: 替换 narration/ import (5 files)
- `tests/test_understanding_steps.py`: narration → narration.engine
- `tests/test_narration_state_machine.py`: narration → narration.engine, narration_steps → narration.steps
- `tests/test_evaluation_steps.py`: narration → narration.engine, narration_evaluator → narration.evaluator, narration_state_machine → narration.state_machine
- `tests/test_assembly_steps.py`: narration → narration.engine
- `tests/test_text_utils.py`: narration_context → narration.context

### Step 4: 替换 video_tools import (3 files)
- `tests/conftest.py`: `scenefab.services.video_tools` → `scenefab.services.video`
- `tests/test_ffmpeg_tool.py`: 4 处 video_tools → video
- `tests/test_caption_generator.py`: video_tools.caption_generator → video.caption_gen

### Step 5: 替换 first_person_workflow 和 direct_video_exporter (4 files)
- `tests/test_first_person_workflow.py`: first_person_workflow → fp_workflow
- `tests/test_direct_video_exporter.py`: direct_video_exporter → video_exporter
- `tests/test_batch_export_manager.py`: batch_export_manager → batch_export
- `tests/test_smoke_pipeline.py`: direct_video_exporter → video_exporter

### Step 6: 验证结果
```
=== video_tools ===
OK
=== first_person_workflow ===
/Users/zfkc/Desktop/04-AI/scene-fab/tests/test_understanding_steps.py:212:    def test_first_person_workflow_rules_add_to_topic(
FAIL
=== direct_video_exporter ===
OK
=== batch_export_manager ===
OK
```

## 注意事项 (Concerns)

**Grep 验证存在误报：**  
`first_person_workflow` 的 grep 在 `tests/test_understanding_steps.py` 第 212 行命中了一个测试方法名：
```python
def test_first_person_workflow_rules_add_to_topic(
```

这不是一个旧模块路径引用，而是一个测试方法的名称，描述的是"第一人称工作流"的业务功能。修改此方法名会破坏测试语义，且与任务目标（更新 import 路径）无关。所有真正的 import 路径引用均已正确更新。

- `video_tools`：无残留 ✓
- `direct_video_exporter`：无残留 ✓
- `batch_export_manager`：无残留 ✓
- `first_person_workflow`：除测试方法名外无 import 残留（误报）
