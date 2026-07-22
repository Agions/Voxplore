# Task 2: 移动/重命名源文件 (git mv)

## 位置
项目根目录: `/Users/zfkc/Desktop/04-AI/scene-fab`

## 任务描述
使用 `git mv` 将 25 个源文件移动到新包结构，同时重命名 7 个超长文件名。

## 执行步骤

### Step 1: git mv settings/ 相关文件

```bash
git mv src/scenefab/settings.py src/scenefab/settings/config.py
git mv src/scenefab/settings_data.py src/scenefab/settings/definitions.py
git mv src/scenefab/settings_types.py src/scenefab/settings/types.py
git mv src/scenefab/settings_manager.py src/scenefab/settings/manager.py
```

### Step 2: git mv project/ 相关文件

```bash
git mv src/scenefab/project_manager.py src/scenefab/project/manager.py
git mv src/scenefab/project_template_manager.py src/scenefab/project/template_mgr.py
git mv src/scenefab/template_models.py src/scenefab/project/template_models.py
```

### Step 3: git mv pipeline/narration/ 相关文件

```bash
git mv src/scenefab/pipeline/narration.py src/scenefab/pipeline/narration/engine.py
git mv src/scenefab/pipeline/narration_context.py src/scenefab/pipeline/narration/context.py
git mv src/scenefab/pipeline/narration_evaluator.py src/scenefab/pipeline/narration/evaluator.py
git mv src/scenefab/pipeline/narration_state_machine.py src/scenefab/pipeline/narration/state_machine.py
git mv src/scenefab/pipeline/narration_steps.py src/scenefab/pipeline/narration/steps.py
```

### Step 4: git mv video_tools/ → video/ 并合并

```bash
git mv src/scenefab/services/video_tools/ffmpeg_tool.py src/scenefab/services/video/ffmpeg_tool.py
git mv src/scenefab/services/video_tools/caption_generator.py src/scenefab/services/video/caption_gen.py
git mv src/scenefab/services/video_tools/probe.py src/scenefab/services/video/probe.py
git mv src/scenefab/services/video_tools/hardware.py src/scenefab/services/video/hardware.py
git mv src/scenefab/services/video_tools/base.py src/scenefab/services/video/tool_base.py
git mv src/scenefab/services/video_tools/__init__.py src/scenefab/services/video/__init__.py
```

### Step 5: 重命名同目录文件

```bash
git mv src/scenefab/pipeline/first_person_workflow.py src/scenefab/pipeline/fp_workflow.py
git mv src/scenefab/services/export/direct_video_exporter.py src/scenefab/services/export/video_exporter.py
git mv src/scenefab/services/export/batch_export_manager.py src/scenefab/services/export/batch_export.py
git mv src/scenefab/core/streaming_llm_worker.py src/scenefab/core/stream_worker.py
git mv src/scenefab/models/project_file_metadata.py src/scenefab/models/file_metadata.py
```

### Step 6: 验证文件已移动

```bash
echo "=== 旧路径应不存在 ==="
test ! -f src/scenefab/settings.py && echo "OK: settings.py gone"
test ! -f src/scenefab/project_manager.py && echo "OK: project_manager.py gone"
test ! -d src/scenefab/services/video_tools && echo "OK: video_tools/ gone"
test ! -f src/scenefab/pipeline/first_person_workflow.py && echo "OK: first_person_workflow.py gone"

echo "=== 新路径应存在 ==="
test -f src/scenefab/settings/config.py && echo "OK: settings/config.py exists"
test -f src/scenefab/project/manager.py && echo "OK: project/manager.py exists"
test -f src/scenefab/pipeline/narration/engine.py && echo "OK: pipeline/narration/engine.py exists"
test -f src/scenefab/services/video/ffmpeg_tool.py && echo "OK: services/video/ffmpeg_tool.py exists"
test -f src/scenefab/services/video/tool_base.py && echo "OK: services/video/tool_base.py exists"
```

### Step 7: Commit

```bash
git add -A
git commit -m "refactor: 移动/重命名 25 个源文件到新包结构"
```

## 验证
执行 Step 6 确认所有旧路径已消失、新路径已存在。

## 全局约束
- 必须使用 `git mv`（不要用普通 mv + git add）
- 不做功能变更，仅移动/重命名
- 所有 25 个文件必须全部移动成功才能 commit
