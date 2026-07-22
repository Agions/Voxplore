# Task 4: 更新 src/ 内绝对 import

## 位置
项目根目录: `/Users/zffc/Desktop/04-AI/scene-fab`

## 任务描述
更新 `src/scenefab/` 内所有引用旧模块路径的 import 语句，共涉及 9 个源文件、28 处 import。

## 执行步骤

### Step 1: 批量替换 video_tools → video（绝对路径）

```bash
sed -i '' 's/scenefab\.services\.video_tools/scenefab.services.video/g' \
  src/scenefab/pipeline/assembly_steps.py \
  src/scenefab/pipeline/understanding_steps.py \
  src/scenefab/main.py \
  src/scenefab/services/video/session.py \
  src/scenefab/services/video_understanding/story_builder.py
```

### Step 2: 批量替换 video_tools → video（相对路径）

```bash
sed -i '' 's/\.\.video_tools/..video/g' \
  src/scenefab/services/video/monologue_maker.py \
  src/scenefab/services/ai/subtitle_speech.py \
  src/scenefab/services/export/jianying_exporter.py
```

### Step 3: 替换 caption_generator → caption_gen（同目录内）

```bash
# monologue_maker.py 和 video/__init__.py 中的相对引用
sed -i '' 's/\.caption_generator/.caption_gen/g' \
  src/scenefab/services/video/monologue_maker.py \
  src/scenefab/services/video/__init__.py

# assembly_steps.py 中的绝对引用
sed -i '' 's/scenefab\.services\.video\.caption_generator/scenefab.services.video.caption_gen/g' \
  src/scenefab/pipeline/assembly_steps.py
```

### Step 4: 替换 video_tools.base → video.tool_base（相对路径）

```bash
sed -i '' 's/\.video_tools\.base/.video.tool_base/g' \
  src/scenefab/services/ai/subtitle_speech.py \
  src/scenefab/services/export/jianying_exporter.py

sed -i '' 's/from \.base import/from .tool_base import/g' \
  src/scenefab/services/video/__init__.py
```

### Step 5: 替换 direct_video_exporter → video_exporter

```bash
sed -i '' 's/scenefab\.services\.export\.direct_video_exporter/scenefab.services.export.video_exporter/g' \
  src/scenefab/pipeline/assembly_steps.py
```

### Step 6: 替换 first_person_workflow → fp_workflow（绝对路径）

```bash
sed -i '' 's/scenefab\.pipeline\.first_person_workflow/scenefab.pipeline.fp_workflow/g' \
  src/scenefab/ui/main/pages/page_view_models.py
```

### Step 7: 替换 settings/ 绝对路径

```bash
sed -i '' 's/from scenefab\.settings import config_manager/from scenefab.settings.config import config_manager/g' \
  src/scenefab/ui/main/pages/settings_page.py
```

### Step 8: 替换 project/ 绝对路径

```bash
sed -i '' 's/from scenefab\.project_manager import/from scenefab.project.manager import/g' \
  src/scenefab/ui/main/pages/assets_page.py
```

### Step 9: 替换 pipeline narration 相对路径（src/scenefab/pipeline/ 下的文件）

```bash
sed -i '' 's/from \.narration_context import/from .narration.context import/g' \
  src/scenefab/pipeline/assembly_steps.py \
  src/scenefab/pipeline/evaluation_steps.py

sed -i '' 's/from \.narration_state_machine import/from .narration.state_machine import/g' \
  src/scenefab/pipeline/assembly_steps.py \
  src/scenefab/pipeline/understanding_steps.py \
  src/scenefab/pipeline/evaluation_steps.py

sed -i '' 's/from \.narration_evaluator import/from .narration.evaluator import/g' \
  src/scenefab/pipeline/evaluation_steps.py

sed -i '' 's/from \.narration_steps import/from .narration.steps import/g' \
  src/scenefab/pipeline/understanding_steps.py
```

### Step 10: 替换 pipeline narration 绝对路径（text_utils.py）

```bash
sed -i '' 's/from scenefab\.pipeline\.narration_context import/from scenefab.pipeline.narration.context import/g' \
  src/scenefab/pipeline/text_utils.py
```

### Step 11: 验证无残留旧路径引用

```bash
echo "=== video_tools ==="
grep -rn "video_tools" src/scenefab/ --include='*.py' && echo "FAIL" || echo "OK"

echo "=== first_person_workflow ==="
grep -rn "first_person_workflow" src/scenefab/ --include='*.py' && echo "FAIL" || echo "OK"

echo "=== direct_video_exporter ==="
grep -rn "direct_video_exporter" src/scenefab/ --include='*.py' && echo "FAIL" || echo "OK"

echo "=== batch_export_manager ==="
grep -rn "batch_export_manager" src/scenefab/ --include='*.py' && echo "FAIL" || echo "OK"

echo "=== streaming_llm_worker ==="
grep -rn "streaming_llm_worker" src/scenefab/ --include='*.py' && echo "FAIL" || echo "OK"

echo "=== caption_generator (in video/) ==="
grep -rn "caption_generator" src/scenefab/services/video/ --include='*.py' && echo "FAIL" || echo "OK"

echo "=== base (in video/ as .base import) ==="
grep -rn "from \.base import" src/scenefab/services/video/ --include='*.py' && echo "FAIL" || echo "OK"
```

All greps should return "OK" (no matches for old paths).

### Step 12: 快速导入验证

```bash
python3 -c "from scenefab.settings.config import ConfigManager; print('OK')"
python3 -c "from scenefab.project.manager import ProjectManager; print('OK')"
python3 -c "from scenefab.pipeline.narration.engine import NarrationStateMachine; print('OK')"
python3 -c "from scenefab.services.video.ffmpeg_tool import FFmpegTool; print('OK')"
python3 -c "from scenefab.pipeline.fp_workflow import FIRST_PERSON_WORKFLOW; print('OK')"
```

### Step 13: Commit

```bash
git add -A
git commit -m "refactor: 更新 src/ 内 28 处绝对/相对 import 到新路径"
```

## 验证
执行 Step 11-12 确认无残留旧路径引用且关键模块可正常导入。

## 全局约束
- 只修改 import 路径，不改变导入的符号名
- 不做功能变更
- 所有 grep 验证必须通过才能 commit
