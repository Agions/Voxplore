# Task 10: 重命名/重组测试文件

## 位置
项目根目录: `/Users/zfkc/Desktop/04-AI/scene-fab`

## 任务描述
将测试文件重命名（长文件名缩短）并按领域分组到子目录，镜像 `src/scenefab/` 的包结构。

## 执行步骤

### Step 1: 创建新目录结构和 __init__.py

```bash
mkdir -p tests/pipeline/test_narration
mkdir -p tests/services/video
mkdir -p tests/services/export
mkdir -p tests/services/ai
mkdir -p tests/ui
mkdir -p tests/plugins
mkdir -p tests/models
mkdir -p tests/core

touch tests/pipeline/__init__.py
touch tests/pipeline/test_narration/__init__.py
touch tests/services/__init__.py
touch tests/services/video/__init__.py
touch tests/services/export/__init__.py
touch tests/services/ai/__init__.py
touch tests/ui/__init__.py
touch tests/plugins/__init__.py
touch tests/models/__init__.py
touch tests/core/__init__.py
```

### Step 2: git mv 测试文件到新位置

**纯重命名（不改变目录结构）:**

```bash
git mv tests/test_script_generator_streaming.py tests/test_script_stream.py
git mv tests/test_project_settings_manager.py tests/test_settings_mgr.py
git mv tests/test_first_person_workflow.py tests/test_fp_workflow.py
git mv tests/test_first_person_extractor.py tests/test_fp_extractor.py
git mv tests/test_direct_video_exporter.py tests/test_video_exporter.py
git mv tests/test_batch_export_manager.py tests/test_batch_export.py
git mv tests/test_emotion_peak_detector.py tests/test_emotion_peak.py
git mv tests/test_ui_page_view_models.py tests/test_page_vm.py
```

**移动到子目录（按领域分组）:**

```bash
# pipeline/
git mv tests/test_understanding_steps.py tests/pipeline/test_understanding_steps.py
git mv tests/test_evaluation_steps.py tests/pipeline/test_evaluation_steps.py
git mv tests/test_assembly_steps.py tests/pipeline/test_assembly_steps.py
git mv tests/test_narration_state_machine.py tests/pipeline/test_narration/test_state_machine.py

# services/ai/
git mv tests/test_llm_base.py tests/services/ai/test_llm_base.py
git mv tests/test_llm_providers.py tests/services/ai/test_llm_providers.py
git mv tests/test_vision_providers.py tests/services/ai/test_vision_providers.py
git mv tests/test_script_generator.py tests/services/ai/test_script_generator.py
git mv tests/test_voice_generator.py tests/services/ai/test_voice_generator.py
git mv tests/test_model_catalog.py tests/services/ai/test_model_catalog.py
git mv tests/test_ai_service_manager.py tests/services/ai/test_ai_service_manager.py

# services/video/
git mv tests/test_caption_generator.py tests/services/video/test_caption_gen.py
git mv tests/test_ffmpeg_tool.py tests/services/video/test_ffmpeg_tool.py
git mv tests/test_highlight_detector.py tests/services/video/test_highlight_detector.py
git mv tests/test_monologue_maker.py tests/services/video/test_monologue_maker.py
git mv tests/test_video_maker.py tests/services/video/test_video_maker.py

# services/export/
git mv tests/test_base_exporter.py tests/services/export/test_base_exporter.py
git mv tests/test_jianying_exporter.py tests/services/export/test_jianying_exporter.py
git mv tests/test_subtitle_extractor.py tests/services/export/test_subtitle_exporter.py
git mv tests/test_export_presets.py tests/services/export/test_export_presets.py

# ui/
git mv tests/test_main_window.py tests/ui/test_main_window.py
git mv tests/test_tray_manager.py tests/ui/test_tray_manager.py

# plugins/
git mv tests/test_plugins/test_loader.py tests/plugins/test_loader.py

# models/
git mv tests/test_project_models.py tests/models/test_project_models.py

# core (flatten from test_core/)
git mv tests/test_core/test_signals_bridge.py tests/core/test_signals_bridge.py
git mv tests/test_core/test_service_container.py tests/core/test_service_container.py

# 模板相关
git mv tests/test_project_template_manager.py tests/test_template_mgr.py
```

### Step 3: 删除旧空子目录

```bash
rmdir tests/test_core 2>/dev/null || true
rmdir tests/test_plugins 2>/dev/null || true
rmdir tests/services 2>/dev/null || true
```

### Step 4: 验证新结构

```bash
echo "=== 新测试目录结构 ==="
find tests/ -type f -name 'test_*.py' | sort

echo "=== 根目录测试文件 ==="
ls tests/test_*.py 2>/dev/null
```

Expected: root-level test files should only be: test_script_stream.py, test_settings_mgr.py, test_fp_workflow.py, test_fp_extractor.py, test_video_exporter.py, test_batch_export.py, test_emotion_peak.py, test_page_vm.py, test_template_mgr.py, plus any domain-independent tests (test_config_manager.py, test_exceptions.py, etc.)

### Step 5: 验证无长文件名

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
    print('FAIL: 长文件名残留:')
    for f in long_files:
        print(f'  {f}')
else:
    print('OK: 测试无长文件名')
"
```

### Step 6: Commit

```bash
git add -A
git commit -m "refactor: 重命名/重组测试文件镜像 src/ 结构"
```

## 验证
执行 Step 4-5 确认新结构正确且无长文件名。

## 全局约束
- 必须使用 `git mv` 移动/重命名文件
- 测试文件命名必须 ≤ 25 字符（不含 .py）
- 目录结构必须镜像 src/scenefab/ 的包结构
