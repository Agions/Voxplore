# SceneFab 项目合规化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对 SceneFab 项目进行合规化改造：消除长文件名、清理过度设计的目录结构、精简冗余脚本和 .gitignore，使项目结构符合 Python 社区标准。

**Architecture:** 通过 git mv 批量移动/重命名文件，然后批量更新所有 import 路径，最后清理空目录和冗余文件。所有改动为纯结构重组，不改变运行时行为。

**Tech Stack:** Python 3.10+, setuptools, PySide6, pytest, ruff, git

## Global Constraints

- 文件名（不含扩展名）≤ 25 字符
- 不做功能变更，所有 import 路径更新为同名重映射
- 不保留旧路径兼容垫片
- 直接重命名，不保留旧文件副本
- 每个 Task 完成后执行 `pytest tests/ -x --ignore=tests/test_integration.py -q` 验证
- 最终验证执行 `pytest tests/ --ignore=tests/test_integration.py -q` 和 `ruff check src/scenefab tests`
- 参考设计文档：`docs/superpowers/specs/2026-07-21-compliance-standardization-design.md`

---

## 执行顺序总览

```
Task 1: 创建新包目录结构
Task 2: 移动/重命名源文件 (git mv)
Task 3: 更新 __init__.py 导出映射
Task 4: 更新 src/ 内绝对 import
Task 5: 更新 tests/ 内绝对 import
Task 6: 删除旧目录与空子包
Task 7: 删除冗余脚本
Task 8: 精简 .gitignore
Task 9: 更新文档与 VitePress 配置
Task 10: 重命名/重组测试文件
Task 11: 更新 CI 与 conftest
Task 12: 最终验证
```

---

### Task 1: 创建新包目录结构

**Files:**
- Create: `src/scenefab/settings/__init__.py`
- Create: `src/scenefab/project/__init__.py`
- Create: `src/scenefab/pipeline/narration/__init__.py`

**Interfaces:**
- Consumes: 无
- Produces: 三个新包的 `__init__.py`，供后续 Task 的 import 使用

- [ ] **Step 1: 创建 settings/ 包**

```bash
mkdir -p src/scenefab/settings
cat > src/scenefab/settings/__init__.py << 'EOF'
"""SceneFab 配置管理包。

公开 API:
- ConfigManager: 全局配置管理（原 scenefab.settings）
- ProjectSettingsManager: 项目设置管理（原 scenefab.settings_manager）
- SettingDefinition / SettingType: 类型定义（原 settings_types）
- get_all_settings_definitions: 设置项定义集合（原 settings_data）
"""

from .config import ConfigManager
from .manager import ProjectSettingsManager
from .definitions import get_all_settings_definitions
from .types import SettingDefinition, SettingType, ProjectSettingsProfile

__all__ = [
    "ConfigManager",
    "ProjectSettingsManager",
    "SettingDefinition",
    "SettingType",
    "ProjectSettingsProfile",
    "get_all_settings_definitions",
]
EOF
```

- [ ] **Step 2: 创建 project/ 包**

```bash
mkdir -p src/scenefab/project
cat > src/scenefab/project/__init__.py << 'EOF'
"""SceneFab 项目管理包。

公开 API:
- ProjectManager: 项目生命周期管理（原 scenefab.project_manager）
- TemplateManager: 项目模板管理（原 scenefab.project_template_manager）
- TemplateCategory / TemplateData: 模板数据模型（原 template_models）
"""

from .manager import ProjectManager
from .template_mgr import TemplateManager
from .template_models import TemplateCategory, TemplateData

__all__ = [
    "ProjectManager",
    "TemplateManager",
    "TemplateCategory",
    "TemplateData",
]
EOF
```

- [ ] **Step 3: 创建 pipeline/narration/ 子包**

```bash
mkdir -p src/scenefab/pipeline/narration
cat > src/scenefab/pipeline/narration/__init__.py << 'EOF'
"""SceneFab v2.2 解说生成状态机子包。

公开 API:
- NarrationStateMachine / NarrationConfig / NarrationContext
- StepResult / NarrationState / TransitionReason
- NarrationEvaluator / EvalResult / DimensionScore
- register_default_steps / register_understanding_steps / register_evaluation_steps
- register_assembly_steps
"""

from .engine import (
    NarrationConfig,
    NarrationContext,
    NarrationState,
    NarrationStateMachine,
    Persona,
    Platform,
    ProductionStyle,
    StepResult,
    TransitionReason,
    register_assembly_steps,
    register_default_steps,
    register_evaluation_steps,
    register_understanding_steps,
)
from .evaluator import (
    DIMENSION_WEIGHTS,
    DimensionScore,
    EvalResult,
    NarrationEvaluator,
)
from .state_machine import (
    NarrationState as _NarrationState,
    StepResult as _StepResult,
)
from .steps import ingest_step, reject_step, accept_step

__all__ = [
    "NarrationConfig",
    "NarrationContext",
    "NarrationState",
    "NarrationStateMachine",
    "Persona",
    "Platform",
    "ProductionStyle",
    "StepResult",
    "TransitionReason",
    "register_assembly_steps",
    "register_default_steps",
    "register_understanding_steps",
    "register_evaluation_steps",
    "DIMENSION_WEIGHTS",
    "DimensionScore",
    "EvalResult",
    "NarrationEvaluator",
    "ingest_step",
    "reject_step",
    "accept_step",
]
EOF
```

- [ ] **Step 4: 验证目录结构**

```bash
ls -la src/scenefab/settings/__init__.py src/scenefab/project/__init__.py src/scenefab/pipeline/narration/__init__.py
```

- [ ] **Step 5: Commit**

```bash
git add src/scenefab/settings/__init__.py src/scenefab/project/__init__.py src/scenefab/pipeline/narration/__init__.py
git commit -m "refactor: 创建 settings/ project/ pipeline/narration/ 新包结构"
```

---

### Task 2: 移动/重命名源文件 (git mv)

**Files:**
- Move: `src/scenefab/settings.py` → `src/scenefab/settings/config.py`
- Move: `src/scenefab/settings_data.py` → `src/scenefab/settings/definitions.py`
- Move: `src/scenefab/settings_types.py` → `src/scenefab/settings/types.py`
- Move: `src/scenefab/settings_manager.py` → `src/scenefab/settings/manager.py`
- Move: `src/scenefab/project_manager.py` → `src/scenefab/project/manager.py`
- Move: `src/scenefab/project_template_manager.py` → `src/scenefab/project/template_mgr.py`
- Move: `src/scenefab/template_models.py` → `src/scenefab/project/template_models.py`
- Move: `src/scenefab/pipeline/narration.py` → `src/scenefab/pipeline/narration/engine.py`
- Move: `src/scenefab/pipeline/narration_context.py` → `src/scenefab/pipeline/narration/context.py`
- Move: `src/scenefab/pipeline/narration_evaluator.py` → `src/scenefab/pipeline/narration/evaluator.py`
- Move: `src/scenefab/pipeline/narration_state_machine.py` → `src/scenefab/pipeline/narration/state_machine.py`
- Move: `src/scenefab/pipeline/narration_steps.py` → `src/scenefab/pipeline/narration/steps.py`
- Move: `src/scenefab/services/video_tools/ffmpeg_tool.py` → `src/scenefab/services/video/ffmpeg_tool.py`
- Move: `src/scenefab/services/video_tools/caption_generator.py` → `src/scenefab/services/video/caption_gen.py`
- Move: `src/scenefab/services/video_tools/probe.py` → `src/scenefab/services/video/probe.py`
- Move: `src/scenefab/services/video_tools/hardware.py` → `src/scenefab/services/video/hardware.py`
- Move: `src/scenefab/services/video_tools/base.py` → `src/scenefab/services/video/tool_base.py`
- Move: `src/scenefab/services/video_tools/__init__.py` → `src/scenefab/services/video/__init__.py` (覆盖)
- Rename: `src/scenefab/pipeline/first_person_workflow.py` → `src/scenefab/pipeline/fp_workflow.py`
- Rename: `src/scenefab/services/video/caption_generator.py` → `src/scenefab/services/video/caption_gen.py` (若存在)
- Rename: `src/scenefab/services/video/base_maker.py` → `src/scenefab/services/video/tool_base.py` (若独立存在)
- Rename: `src/scenefab/services/export/direct_video_exporter.py` → `src/scenefab/services/export/video_exporter.py`
- Rename: `src/scenefab/services/export/batch_export_manager.py` → `src/scenefab/services/export/batch_export.py`
- Rename: `src/scenefab/core/streaming_llm_worker.py` → `src/scenefab/core/stream_worker.py`
- Rename: `src/scenefab/models/project_file_metadata.py` → `src/scenefab/models/file_metadata.py`

**Interfaces:**
- Consumes: Task 1 创建的新包目录
- Produces: 文件位于新路径，旧路径文件已不存在

- [ ] **Step 1: git mv settings/ 相关文件**

```bash
git mv src/scenefab/settings.py src/scenefab/settings/config.py
git mv src/scenefab/settings_data.py src/scenefab/settings/definitions.py
git mv src/scenefab/settings_types.py src/scenefab/settings/types.py
git mv src/scenefab/settings_manager.py src/scenefab/settings/manager.py
```

- [ ] **Step 2: git mv project/ 相关文件**

```bash
git mv src/scenefab/project_manager.py src/scenefab/project/manager.py
git mv src/scenefab/project_template_manager.py src/scenefab/project/template_mgr.py
git mv src/scenefab/template_models.py src/scenefab/project/template_models.py
```

- [ ] **Step 3: git mv pipeline/narration/ 相关文件**

```bash
git mv src/scenefab/pipeline/narration.py src/scenefab/pipeline/narration/engine.py
git mv src/scenefab/pipeline/narration_context.py src/scenefab/pipeline/narration/context.py
git mv src/scenefab/pipeline/narration_evaluator.py src/scenefab/pipeline/narration/evaluator.py
git mv src/scenefab/pipeline/narration_state_machine.py src/scenefab/pipeline/narration/state_machine.py
git mv src/scenefab/pipeline/narration_steps.py src/scenefab/pipeline/narration/steps.py
```

- [ ] **Step 4: git mv video_tools/ → video/ 并合并**

```bash
git mv src/scenefab/services/video_tools/ffmpeg_tool.py src/scenefab/services/video/ffmpeg_tool.py
git mv src/scenefab/services/video_tools/caption_generator.py src/scenefab/services/video/caption_gen.py
git mv src/scenefab/services/video_tools/probe.py src/scenefab/services/video/probe.py
git mv src/scenefab/services/video_tools/hardware.py src/scenefab/services/video/hardware.py
git mv src/scenefab/services/video_tools/base.py src/scenefab/services/video/tool_base.py
git mv src/scenefab/services/video_tools/__init__.py src/scenefab/services/video/__init__.py
```

- [ ] **Step 5: 重命名同目录文件**

```bash
git mv src/scenefab/pipeline/first_person_workflow.py src/scenefab/pipeline/fp_workflow.py
git mv src/scenefab/services/export/direct_video_exporter.py src/scenefab/services/export/video_exporter.py
git mv src/scenefab/services/export/batch_export_manager.py src/scenefab/services/export/batch_export.py
git mv src/scenefab/core/streaming_llm_worker.py src/scenefab/core/stream_worker.py
git mv src/scenefab/models/project_file_metadata.py src/scenefab/models/file_metadata.py
```

- [ ] **Step 6: 验证文件已移动**

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

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: 移动/重命名 25 个源文件到新包结构"
```

---

### Task 3: 更新 __init__.py 导出映射

**Files:**
- Modify: `src/scenefab/pipeline/__init__.py`
- Modify: `src/scenefab/services/export/__init__.py`
- Modify: `src/scenefab/core/__init__.py`
- Modify: `src/scenefab/services/video/__init__.py`

**Interfaces:**
- Consumes: Task 2 完成后的新文件路径
- Produces: 所有 `__init__.py` 的导出路径指向新位置

- [ ] **Step 1: 更新 pipeline/__init__.py**

```python
# 修改前（第 10 行和第 18 行）:
# from .first_person_workflow import (
#     FIRST_PERSON_QUALITY_GATES, FIRST_PERSON_SCRIPT_RULES, ...
# )
# from .narration import (
#     PLATFORM_SPECS, NarrationConfig, ...
# )

# 修改后:
from .fp_workflow import (
    FIRST_PERSON_QUALITY_GATES,
    FIRST_PERSON_SCRIPT_RULES,
    FIRST_PERSON_WORKFLOW,
    ScriptRule,
    WorkflowStage,
    numbered_workflow,
)
from .narration.engine import (
    PLATFORM_SPECS,
    NarrationConfig,
    NarrationContext,
    NarrationState,
    NarrationStateMachine,
    Persona,
    Platform,
    ProductionStyle,
    StepResult,
    TransitionReason,
    register_assembly_steps,
    register_default_steps,
    register_evaluation_steps,
    register_understanding_steps,
)
```

- [ ] **Step 2: 更新 services/export/__init__.py**

```python
# 修改第 9 行和第 16 行:
# from .batch_export_manager import (
#     BatchExportManager, BatchExportResult, ...
# )
# from .direct_video_exporter import (
#     DirectVideoExporter, HWAccel, ...
# )

# 修改为:
from .batch_export import (
    BatchExportManager,
    BatchExportResult,
    ExportStatus,
    ExportTask,
    get_batch_export_manager,
)
from .video_exporter import (
    DirectVideoExporter,
    HWAccel,
    Resolution,
    VideoCodec,
    VideoExportConfig,
    VideoFormat,
)
```

- [ ] **Step 3: 更新 core/__init__.py 的 lazy import 映射**

```python
# 修改第 23 行:
# "StreamingLLMWorker": ("scenefab.core.streaming_llm_worker", "StreamingLLMWorker"),
# 修改为:
"StreamingLLMWorker": ("scenefab.core.stream_worker", "StreamingLLMWorker"),
```

- [ ] **Step 4: 更新 services/video/__init__.py**

该文件已随 Task 2 从 `video_tools/__init__.py` 移入 `video/__init__.py`，需要更新内部引用：

```python
# 修改第 13 行:
# from .base import (
#     BaseVideoProcessor, IVideoProcessor, ProcessingResult, VideoMetadata,
# )
# 修改为:
from .tool_base import (
    BaseVideoProcessor,
    IVideoProcessor,
    ProcessingResult,
    VideoMetadata,
)

# 修改第 19 行:
# from .caption_generator import Caption, CaptionConfig, CaptionGenerator, CaptionStyle
# 修改为:
from .caption_gen import Caption, CaptionConfig, CaptionGenerator, CaptionStyle
```

- [ ] **Step 5: Commit**

```bash
git add src/scenefab/pipeline/__init__.py src/scenefab/services/export/__init__.py src/scenefab/core/__init__.py src/scenefab/services/video/__init__.py
git commit -m "refactor: 更新 __init__.py 导出映射到新路径"
```

---

### Task 4: 更新 src/ 内绝对 import

**Files to modify (9 个源文件):**

| 文件 | 修改行 | 旧 import | 新 import |
|------|--------|-----------|-----------|
| `src/scenefab/ui/main/pages/settings_page.py` | 409 | `from scenefab.settings import config_manager` | `from scenefab.settings.config import config_manager` |
| `src/scenefab/ui/main/pages/assets_page.py` | 34 | `from scenefab.project_manager import ProjectManager` | `from scenefab.project.manager import ProjectManager` |
| `src/scenefab/pipeline/assembly_steps.py` | 67 | `from scenefab.services.video_tools.ffmpeg_tool import FFmpegTool` | `from scenefab.services.video.ffmpeg_tool import FFmpegTool` |
| `src/scenefab/pipeline/assembly_steps.py` | 354 | `from scenefab.services.video_tools.caption_generator import CaptionGenerator` | `from scenefab.services.video.caption_gen import CaptionGenerator` |
| `src/scenefab/pipeline/assembly_steps.py` | 515 | `from scenefab.services.video_tools.ffmpeg_tool import FFmpegTool` | `from scenefab.services.video.ffmpeg_tool import FFmpegTool` |
| `src/scenefab/pipeline/assembly_steps.py` | 562 | `from scenefab.services.export.direct_video_exporter import (` | `from scenefab.services.export.video_exporter import (` |
| `src/scenefab/pipeline/assembly_steps.py` | 629 | `from .narration_state_machine import NarrationStateMachine` | `from .narration.state_machine import NarrationStateMachine` |
| `src/scenefab/pipeline/understanding_steps.py` | 27 | `from .first_person_workflow import FIRST_PERSON_SCRIPT_RULES` | `from .fp_workflow import FIRST_PERSON_SCRIPT_RULES` |
| `src/scenefab/pipeline/understanding_steps.py` | 28 | `from .narration_context import (` | `from .narration.context import (` |
| `src/scenefab/pipeline/understanding_steps.py` | 34 | `from .narration_state_machine import NarrationState, StepResult` | `from .narration.state_machine import NarrationState, StepResult` |
| `src/scenefab/pipeline/understanding_steps.py` | 471 | `from scenefab.services.video_tools.ffmpeg_tool import FFmpegTool` | `from scenefab.services.video.ffmpeg_tool import FFmpegTool` |
| `src/scenefab/pipeline/understanding_steps.py` | 580 | `from .narration_state_machine import NarrationStateMachine` | `from .narration.state_machine import NarrationStateMachine` |
| `src/scenefab/pipeline/evaluation_steps.py` | 25 | `from .narration_context import (` | `from .narration.context import (` |
| `src/scenefab/pipeline/evaluation_steps.py` | 28 | `from .narration_state_machine import NarrationState, StepResult` | `from .narration.state_machine import NarrationState, StepResult` |
| `src/scenefab/pipeline/evaluation_steps.py` | 53 | `from .narration_evaluator import NarrationEvaluator` | `from .narration.evaluator import NarrationEvaluator` |
| `src/scenefab/pipeline/evaluation_steps.py` | 301 | `from .narration_evaluator import NarrationEvaluator` | `from .narration.evaluator import NarrationEvaluator` |
| `src/scenefab/pipeline/evaluation_steps.py` | 353 | `from .narration_state_machine import NarrationStateMachine` | `from .narration.state_machine import NarrationStateMachine` |
| `src/scenefab/pipeline/text_utils.py` | 5 | `from scenefab.pipeline.narration_context import ProductionStyle` | `from scenefab.pipeline.narration.context import ProductionStyle` |
| `src/scenefab/main.py` | 299 | `from scenefab.services.video_tools.ffmpeg_tool import FFmpegTool` | `from scenefab.services.video.ffmpeg_tool import FFmpegTool` |
| `src/scenefab/services/video/session.py` | 55 | `from scenefab.services.video_tools.ffmpeg_tool import FFmpegTool` | `from scenefab.services.video.ffmpeg_tool import FFmpegTool` |
| `src/scenefab/services/video/session.py` | 231 | `from scenefab.services.video_tools.ffmpeg_tool import FFmpegTool` | `from scenefab.services.video.ffmpeg_tool import FFmpegTool` |
| `src/scenefab/services/video/monologue_maker.py` | 38 | `from ..video_tools.caption_generator import CaptionGenerator` | `from ..video.caption_gen import CaptionGenerator` |
| `src/scenefab/services/video/monologue_maker.py` | 39 | `from ..video_tools.ffmpeg_tool import FFmpegTool` | `from ..video.ffmpeg_tool import FFmpegTool` |
| `src/scenefab/services/ai/subtitle_speech.py` | 18 | `from ..video_tools.base import get_seg_attr` | `from ..video.tool_base import get_seg_attr` |
| `src/scenefab/services/export/jianying_exporter.py` | 30 | `from ..video_tools.base import extract_video_metadata` | `from ..video.tool_base import extract_video_metadata` |
| `src/scenefab/services/video_understanding/story_builder.py` | 10 | `from scenefab.services.video_tools.ffmpeg_tool import FFmpegTool` | `from scenefab.services.video.ffmpeg_tool import FFmpegTool` |
| `src/scenefab/ui/main/pages/page_view_models.py` | 6 | `from scenefab.pipeline.first_person_workflow import (` | `from scenefab.pipeline.fp_workflow import (` |

**Interfaces:**
- Consumes: Task 2 完成后的新文件路径, Task 3 完成后的 __init__.py 更新
- Produces: 所有源文件的 import 路径指向新位置

- [ ] **Step 1: 使用 sed 批量替换 video_tools → video**

```bash
# 批量替换所有 video_tools 绝对路径引用
sed -i '' 's/scenefab\.services\.video_tools/scenefab.services.video/g' \
  src/scenefab/pipeline/assembly_steps.py \
  src/scenefab/pipeline/understanding_steps.py \
  src/scenefab/main.py \
  src/scenefab/services/video/session.py \
  src/scenefab/services/video_understanding/story_builder.py

# 批量替换 video_tools 相对路径引用
sed -i '' 's/\.\.video_tools/..video/g' \
  src/scenefab/services/video/monologue_maker.py \
  src/scenefab/services/ai/subtitle_speech.py \
  src/scenefab/services/export/jianying_exporter.py
```

- [ ] **Step 2: 替换 caption_generator → caption_gen（同目录内）**

```bash
sed -i '' 's/\.caption_generator/.caption_gen/g' \
  src/scenefab/services/video/monologue_maker.py \
  src/scenefab/services/video/__init__.py

sed -i '' 's/scenefab\.services\.video\.caption_generator/scenefab.services.video.caption_gen/g' \
  src/scenefab/pipeline/assembly_steps.py
```

- [ ] **Step 3: 替换 base → tool_base（同目录内）**

```bash
sed -i '' 's/\.video_tools\.base/.video.tool_base/g' \
  src/scenefab/services/ai/subtitle_speech.py \
  src/scenefab/services/export/jianying_exporter.py

sed -i '' 's/from \.base import/from .tool_base import/g' \
  src/scenefab/services/video/__init__.py
```

- [ ] **Step 4: 替换 direct_video_exporter → video_exporter**

```bash
sed -i '' 's/scenefab\.services\.export\.direct_video_exporter/scenefab.services.export.video_exporter/g' \
  src/scenefab/pipeline/assembly_steps.py
```

- [ ] **Step 5: 替换 first_person_workflow → fp_workflow**

```bash
sed -i '' 's/scenefab\.pipeline\.first_person_workflow/scenefab.pipeline.fp_workflow/g' \
  src/scenefab/ui/main/pages/page_view_models.py
```

- [ ] **Step 6: 替换 settings/ 和 project/ 绝对路径**

```bash
# settings/ 相关
sed -i '' 's/from scenefab\.settings import config_manager/from scenefab.settings.config import config_manager/g' \
  src/scenefab/ui/main/pages/settings_page.py

# project/ 相关
sed -i '' 's/from scenefab\.project_manager import/from scenefab.project.manager import/g' \
  src/scenefab/ui/main/pages/assets_page.py
```

- [ ] **Step 7: 替换 pipeline narration 相对路径（src/scenefab/pipeline/ 下的文件）**

```bash
# 这些文件现在在 pipeline/ 下，narration 变成了子包
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

- [ ] **Step 8: 替换 pipeline narration 绝对路径（text_utils.py）**

```bash
sed -i '' 's/from scenefab\.pipeline\.narration_context import/from scenefab.pipeline.narration.context import/g' \
  src/scenefab/pipeline/text_utils.py
```

- [ ] **Step 9: 验证无残留旧路径引用**

```bash
# 检查是否还有 video_tools 引用（应在 src/ 内清零）
grep -rn "video_tools" src/scenefab/ --include='*.py' && echo "FAIL: 残留 video_tools" || echo "OK: 无残留 video_tools"

# 检查是否还有 first_person_workflow 引用
grep -rn "first_person_workflow" src/scenefab/ --include='*.py' && echo "FAIL: 残留" || echo "OK"

# 检查是否还有 direct_video_exporter 引用
grep -rn "direct_video_exporter" src/scenefab/ --include='*.py' && echo "FAIL: 残留" || echo "OK"
```

- [ ] **Step 10: 快速导入验证**

```bash
python3 -c "from scenefab.settings.config import ConfigManager; print('OK: settings.config')"
python3 -c "from scenefab.project.manager import ProjectManager; print('OK: project.manager')"
python3 -c "from scenefab.pipeline.narration.engine import NarrationStateMachine; print('OK: narration.engine')"
python3 -c "from scenefab.services.video.ffmpeg_tool import FFmpegTool; print('OK: video.ffmpeg_tool')"
python3 -c "from scenefab.pipeline.fp_workflow import FIRST_PERSON_WORKFLOW; print('OK: fp_workflow')"
```

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "refactor: 更新 src/ 内 28 处绝对/相对 import 到新路径"
```

---

### Task 5: 更新 tests/ 内绝对 import

**Files to modify (11 个测试文件 + 1 个 conftest):**

| 文件 | 修改内容 |
|------|----------|
| `tests/test_config_manager.py` | `from scenefab.settings import (` → `from scenefab.settings.config import (` |
| `tests/test_issue82_regression.py` | `from scenefab.settings import ConfigManager` → `from scenefab.settings.config import ConfigManager` |
| `tests/test_project_manager.py` | `from scenefab.project_manager import (` → `from scenefab.project.manager import (` |
| `tests/test_project_template_manager.py` | 两行: project_manager + project_template_manager |
| `tests/test_first_person_workflow.py` | `from scenefab.pipeline.first_person_workflow import (` → `from scenefab.pipeline.fp_workflow import (` |
| `tests/test_direct_video_exporter.py` | `from scenefab.services.export.direct_video_exporter import (` → `from scenefab.services.export.video_exporter import (` |
| `tests/test_batch_export_manager.py` | `from scenefab.services.export.batch_export_manager import (` → `from scenefab.services.export.batch_export import (` |
| `tests/test_ffmpeg_tool.py` | video_tools → video, caption_generator → caption_gen |
| `tests/test_caption_generator.py` | video_tools.caption_generator → video.caption_gen |
| `tests/test_understanding_steps.py` | narration_* → narration.* |
| `tests/test_narration_state_machine.py` | narration_* → narration.* |
| `tests/test_evaluation_steps.py` | narration_* → narration.* |
| `tests/test_assembly_steps.py` | narration_state_machine → narration.state_machine |
| `tests/test_text_utils.py` | narration_context → narration.context |
| `tests/conftest.py` | video_tools → video |

**Interfaces:**
- Consumes: Task 2-4 完成
- Produces: 所有测试文件的 import 路径正确

- [ ] **Step 1: 批量替换 tests/ 中的 settings/ import**

```bash
sed -i '' 's/from scenefab\.settings import ConfigManager/from scenefab.settings.config import ConfigManager/g' \
  tests/test_issue82_regression.py

# test_config_manager.py: 替换 from scenefab.settings import ( 为 from scenefab.settings.config import (
# 需要用 Python 脚本处理多行 import
python3 -c "
import re
p = 'tests/test_config_manager.py'
t = open(p).read()
t = t.replace('from scenefab.settings import (', 'from scenefab.settings.config import (')
open(p, 'w').write(t)
print('OK: test_config_manager.py updated')
"
```

- [ ] **Step 2: 批量替换 tests/ 中的 project/ import**

```bash
sed -i '' 's/from scenefab\.project_manager import/from scenefab.project.manager import/g' \
  tests/test_project_manager.py

# test_project_template_manager.py 有两行需要替换
python3 -c "
p = 'tests/test_project_template_manager.py'
t = open(p).read()
t = t.replace('from scenefab.project_manager import Project', 'from scenefab.project.manager import Project')
t = t.replace('from scenefab.project_template_manager import (', 'from scenefab.project.template_mgr import (')
open(p, 'w').write(t)
print('OK: test_project_template_manager.py updated')
"
```

- [ ] **Step 3: 批量替换 tests/ 中的 narration/ import**

```bash
# narration 包绝对路径 → 子模块
python3 -c "
import re

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

- [ ] **Step 4: 批量替换 tests/ 中的 video_tools import**

```bash
# conftest.py
sed -i '' 's/scenefab\.services\.video_tools/scenefab.services.video/g' \
  tests/conftest.py

# test_ffmpeg_tool.py
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

- [ ] **Step 5: 替换 first_person_workflow → fp_workflow 和 direct_video_exporter → video_exporter**

```bash
# test_first_person_workflow.py
python3 -c "
p = 'tests/test_first_person_workflow.py'
t = open(p).read()
t = t.replace('from scenefab.pipeline.first_person_workflow import (', 'from scenefab.pipeline.fp_workflow import (')
open(p, 'w').write(t)
print('OK: test_first_person_workflow.py')
"

# test_direct_video_exporter.py → test_video_exporter.py (文件名在 Task 10 修改)
python3 -c "
p = 'tests/test_direct_video_exporter.py'
t = open(p).read()
t = t.replace('from scenefab.services.export.direct_video_exporter import (', 'from scenefab.services.export.video_exporter import (')
open(p, 'w').write(t)
print('OK: test_direct_video_exporter.py')
"

# test_batch_export_manager.py → test_batch_export.py (文件名在 Task 10 修改)
python3 -c "
p = 'tests/test_batch_export_manager.py'
t = open(p).read()
t = t.replace('from scenefab.services.export.batch_export_manager import BatchExportManager', 'from scenefab.services.export.batch_export import BatchExportManager')
open(p, 'w').write(t)
print('OK: test_batch_export_manager.py')
"

# test_smoke_pipeline.py 有 7 处 direct_video_exporter 引用
python3 -c "
p = 'tests/test_smoke_pipeline.py'
t = open(p).read()
t = t.replace('scenefab.services.export.direct_video_exporter', 'scenefab.services.export.video_exporter')
open(p, 'w').write(t)
print('OK: test_smoke_pipeline.py')
"
```

- [ ] **Step 6: 验证无残留旧路径**

```bash
grep -rn "video_tools\|first_person_workflow\|direct_video_exporter\|batch_export_manager\|streaming_llm_worker\|project_file_metadata\|settings_data\|settings_types\|project_template_manager" tests/ --include='*.py' | grep -v "test_first_person_workflow.py\|test_direct_video_exporter.py\|test_batch_export_manager.py\|test_project_template_manager.py\|test_narration_state_machine.py" && echo "FAIL: 残留旧引用" || echo "OK: 无残留"
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: 更新 tests/ 内 35 处 import 到新路径"
```

---

### Task 6: 删除旧目录与空子包

**Files:**
- Delete: `src/scenefab/services/video/grouping/` (空子包)
- Delete: `src/scenefab/services/video/selection/` (空子包)
- Delete: `src/scenefab/services/video_tools/` (已移空)

**Interfaces:**
- Consumes: Task 2-5 完成，所有文件已移走
- Produces: 空目录清除

- [ ] **Step 1: 确认 video_tools/ 已空**

```bash
find src/scenefab/services/video_tools -type f -name '*.py' 2>/dev/null && echo "FAIL: 还有文件" || echo "OK: video_tools/ 已空"
```

- [ ] **Step 2: 删除空目录**

```bash
rm -rf src/scenefab/services/video_tools
rm -rf src/scenefab/services/video/grouping
rm -rf src/scenefab/services/video/selection
```

- [ ] **Step 3: 验证**

```bash
test ! -d src/scenefab/services/video_tools && echo "OK: video_tools/ deleted"
test ! -d src/scenefab/services/video/grouping && echo "OK: grouping/ deleted"
test ! -d src/scenefab/services/video/selection && echo "OK: selection/ deleted"
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: 删除 video_tools/ 空目录及 grouping/ selection/ 空子包"
```

---

### Task 7: 删除冗余脚本

**Files:**
- Delete: `scripts/build.py`
- Delete: `main.spec`
- Delete: `conftest.py` (根目录)

**Files to modify:**
- Modify: `tests/conftest.py` (合并根目录 conftest 的 GUI 跳过逻辑)

**Interfaces:**
- Consumes: 无依赖
- Produces: 根目录清理，冗余脚本删除

- [ ] **Step 1: 删除冗余脚本**

```bash
rm scripts/build.py
rm main.spec
rm conftest.py
```

- [ ] **Step 2: 更新 tests/conftest.py（合并根目录 conftest 的 GUI 跳过逻辑）**

```python
# tests/conftest.py — 合并后的完整内容:
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

- [ ] **Step 3: 验证**

```bash
test ! -f scripts/build.py && echo "OK: build.py deleted"
test ! -f main.spec && echo "OK: main.spec deleted"
test ! -f conftest.py && echo "OK: root conftest.py deleted"
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: 删除冗余脚本 build.py main.spec 和根目录 conftest.py"
```

---

### Task 8: 精简 .gitignore

**Files:**
- Modify: `.gitignore`

**Interfaces:**
- Consumes: 无
- Produces: 精简后的 .gitignore (~80 行)

- [ ] **Step 1: 备份旧文件**

```bash
cp .gitignore .gitignore.bak
```

- [ ] **Step 2: 写入精简后的 .gitignore**

```bash
cat > .gitignore << 'GITIGNORE'
# ── Python ──────────────────────────────────────
__pycache__/
*.py[cod]
*.so
*.egg-info/
*.egg
dist/
build/
wheels/

# ── 虚拟环境 ────────────────────────────────────
.venv/
venv/
env/

# ── 测试/覆盖率 ─────────────────────────────────
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage
.coverage.*
coverage.xml

# ── IDE / 编辑器 ────────────────────────────────
.vscode/
.idea/
*.iml
*.swp
*.swo
*~

# ── macOS / Windows / Linux ─────────────────────
.DS_Store
Thumbs.db
desktop.ini

# ── 环境变量 ────────────────────────────────────
.env
.env.local
.env.*.local

# ── 应用运行时 ──────────────────────────────────
*.log
temp/
cache/
output/
exports/

# ── AI 模型文件 ─────────────────────────────────
*.pt
*.pth
*.onnx
*.h5

# ── 媒体文件（不入库）────────────────────────────
*.mp4
*.avi
*.mov
*.mkv
*.wav
*.mp3
*.flac

# ── 文档构建产物 ─────────────────────────────────
docs/.vitepress/dist/
docs/.vitepress/cache/
docs/.vitepress/.temp/
docs/node_modules/
docs/package-lock.json

# ── 本地开发文档（不入库）────────────────────────
DEVELOPMENT.md
TODO.md
SPEC.md
PLAN.md
notes/
research/
.learnings/
_DEAD/
GITIGNORE
```

- [ ] **Step 3: 验证行数**

```bash
wc -l .gitignore
# 预期: ~80 行
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: 精简 .gitignore 从 392 行到 ~80 行"
```

---

### Task 9: 更新文档与 VitePress 配置

**Files:**
- Rename: `docs/guide/first-person-narration-production.md` → `docs/guide/narration-spec.md`
- Modify: `docs/.vitepress/config.ts`

**Interfaces:**
- Consumes: 无
- Produces: 文档路径合规，VitePress 路由同步

- [ ] **Step 1: 重命名文档**

```bash
git mv docs/guide/first-person-narration-production.md docs/guide/narration-spec.md
```

- [ ] **Step 2: 更新 VitePress config.ts**

在 `docs/.vitepress/config.ts` 中更新两处链接：

```typescript
// sidebar 中 (约第 21 行):
// 旧: { text: '第一人称生产规范', link: '/guide/first-person-narration-production' },
// 新:
{ text: '第一人称生产规范', link: '/guide/narration-spec' },

// nav 中 (约第 154 行):
// 旧: { text: '第一人称生产规范', link: '/guide/first-person-narration-production' },
// 新:
{ text: '第一人称生产规范', link: '/guide/narration-spec' },
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "docs: 重命名过长文档文件并同步 VitePress 路由"
```

---

### Task 10: 重命名/重组测试文件

**Files to rename:**

| 旧文件名 | 新文件名 |
|----------|----------|
| `tests/test_script_generator_streaming.py` | `tests/test_script_stream.py` |
| `tests/test_project_template_manager.py` | `tests/test_template_mgr.py` |
| `tests/test_project_settings_manager.py` | `tests/test_settings_mgr.py` |
| `tests/test_narration_state_machine.py` | `tests/test_narration/test_state_machine.py` |
| `tests/test_first_person_extractor.py` | `tests/test_fp_extractor.py` |
| `tests/test_first_person_workflow.py` | `tests/test_fp_workflow.py` |
| `tests/test_direct_video_exporter.py` | `tests/test_video_exporter.py` |
| `tests/test_batch_export_manager.py` | `tests/test_batch_export.py` |
| `tests/test_emotion_peak_detector.py` | `tests/test_emotion_peak.py` |
| `tests/test_ui_page_view_models.py` | `tests/test_page_vm.py` |
| `tests/test_understanding_steps.py` | `tests/pipeline/test_understanding_steps.py` |
| `tests/test_evaluation_steps.py` | `tests/pipeline/test_evaluation_steps.py` |
| `tests/test_assembly_steps.py` | `tests/pipeline/test_assembly_steps.py` |
| `tests/test_caption_generator.py` | `tests/services/video/test_caption_gen.py` |
| `tests/test_ffmpeg_tool.py` | `tests/services/video/test_ffmpeg_tool.py` |
| `tests/test_first_person_extractor.py` | `tests/services/video/test_fp_extractor.py` |
| `tests/test_emotion_peak_detector.py` | `tests/services/video/test_emotion_peak.py` |
| `tests/test_highlight_detector.py` | `tests/services/video/test_highlight_detector.py` |
| `tests/test_monologue_maker.py` | `tests/services/video/test_monologue_maker.py` |
| `tests/test_video_maker.py` | `tests/services/video/test_video_maker.py` |
| `tests/test_base_exporter.py` | `tests/services/export/test_base_exporter.py` |
| `tests/test_jianying_exporter.py` | `tests/services/export/test_jianying_exporter.py` |
| `tests/test_subtitle_extractor.py` | `tests/services/export/test_subtitle_exporter.py` |
| `tests/test_export_presets.py` | `tests/services/export/test_export_presets.py` |
| `tests/test_llm_base.py` | `tests/services/ai/test_llm_base.py` |
| `tests/test_llm_providers.py` | `tests/services/ai/test_llm_providers.py` |
| `tests/test_vision_providers.py` | `tests/services/ai/test_vision_providers.py` |
| `tests/test_script_generator.py` | `tests/services/ai/test_script_generator.py` |
| `tests/test_voice_generator.py` | `tests/services/ai/test_voice_generator.py` |
| `tests/test_model_catalog.py` | `tests/services/ai/test_model_catalog.py` |
| `tests/test_ai_service_manager.py` | `tests/services/ai/test_ai_service_manager.py` |
| `tests/test_main_window.py` | `tests/ui/test_main_window.py` |
| `tests/test_tray_manager.py` | `tests/ui/test_tray_manager.py` |
| `tests/test_plugins/test_loader.py` | `tests/plugins/test_loader.py` |
| `tests/test_project_models.py` | `tests/models/test_project_models.py` |
| `tests/test_core/test_signals_bridge.py` | `tests/core/test_signals_bridge.py` |
| `tests/test_core/test_service_container.py` | `tests/core/test_service_container.py` |

**Interfaces:**
- Consumes: Task 5 完成（import 已更新）
- Produces: 测试目录镜像 src/ 结构

- [ ] **Step 1: 创建新目录结构**

```bash
mkdir -p tests/pipeline/test_narration
mkdir -p tests/services/video
mkdir -p tests/services/export
mkdir -p tests/services/ai
mkdir -p tests/ui
mkdir -p tests/plugins
mkdir -p tests/models
mkdir -p tests/core

# 创建 __init__.py（确保 pytest 发现和相对导入正常）
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

- [ ] **Step 2: git mv 测试文件到新位置**

```bash
# 纯重命名（不改变目录结构）
git mv tests/test_script_generator_streaming.py tests/test_script_stream.py
git mv tests/test_project_settings_manager.py tests/test_settings_mgr.py
git mv tests/test_first_person_workflow.py tests/test_fp_workflow.py
git mv tests/test_first_person_extractor.py tests/test_fp_extractor.py
git mv tests/test_direct_video_exporter.py tests/test_video_exporter.py
git mv tests/test_batch_export_manager.py tests/test_batch_export.py
git mv tests/test_emotion_peak_detector.py tests/test_emotion_peak.py
git mv tests/test_ui_page_view_models.py tests/test_page_vm.py

# 移动到子目录（按领域分组）
git mv tests/test_understanding_steps.py tests/pipeline/test_understanding_steps.py
git mv tests/test_evaluation_steps.py tests/pipeline/test_evaluation_steps.py
git mv tests/test_assembly_steps.py tests/pipeline/test_assembly_steps.py
git mv tests/test_narration_state_machine.py tests/pipeline/test_narration/test_state_machine.py
git mv tests/test_main_window.py tests/ui/test_main_window.py
git mv tests/test_tray_manager.py tests/ui/test_tray_manager.py
git mv tests/test_plugins/test_loader.py tests/plugins/test_loader.py
git mv tests/test_project_models.py tests/models/test_project_models.py
git mv tests/test_core/test_signals_bridge.py tests/core/test_signals_bridge.py
git mv tests/test_core/test_service_container.py tests/core/test_service_container.py

# services/ 分组
git mv tests/test_llm_base.py tests/services/ai/test_llm_base.py
git mv tests/test_llm_providers.py tests/services/ai/test_llm_providers.py
git mv tests/test_vision_providers.py tests/services/ai/test_vision_providers.py
git mv tests/test_script_generator.py tests/services/ai/test_script_generator.py
git mv tests/test_voice_generator.py tests/services/ai/test_voice_generator.py
git mv tests/test_model_catalog.py tests/services/ai/test_model_catalog.py
git mv tests/test_ai_service_manager.py tests/services/ai/test_ai_service_manager.py
git mv tests/test_caption_generator.py tests/services/video/test_caption_gen.py
git mv tests/test_ffmpeg_tool.py tests/services/video/test_ffmpeg_tool.py
git mv tests/test_highlight_detector.py tests/services/video/test_highlight_detector.py
git mv tests/test_monologue_maker.py tests/services/video/test_monologue_maker.py
git mv tests/test_video_maker.py tests/services/video/test_video_maker.py
git mv tests/test_base_exporter.py tests/services/export/test_base_exporter.py
git mv tests/test_jianying_exporter.py tests/services/export/test_jianying_exporter.py
git mv tests/test_subtitle_extractor.py tests/services/export/test_subtitle_exporter.py
git mv tests/test_export_presets.py tests/services/export/test_export_presets.py

# 根目录模板文件
git mv tests/test_project_template_manager.py tests/test_template_mgr.py
```

- [ ] **Step 3: 删除旧空子目录**

```bash
# 移动后确认这些目录已空
rmdir tests/test_core 2>/dev/null || true
rmdir tests/test_plugins 2>/dev/null || true
rmdir tests/services/video 2>/dev/null || true  # 旧路径（如果有 services/video/ 残留）
```

- [ ] **Step 4: 验证新结构**

```bash
echo "=== 新测试目录结构 ==="
find tests/ -type f -name 'test_*.py' | sort
echo "=== 根目录测试文件 ==="
ls tests/test_*.py 2>/dev/null
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: 重命名/重组测试文件镜像 src/ 结构"
```

---

### Task 11: 更新 CI 与 conftest

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/pr-check.yml`

**Interfaces:**
- Consumes: Task 10 完成（测试文件已重命名/移动）
- Produces: CI 引用的测试路径正确

- [ ] **Step 1: 更新 CI workflows 中的 --ignore 路径**

```bash
# ci.yml 和 pr-check.yml 中 3 个被忽略的 GUI 测试
sed -i '' 's|tests/test_project_settings_manager.py|tests/test_settings_mgr.py|g' \
  .github/workflows/ci.yml .github/workflows/pr-check.yml

sed -i '' 's|tests/test_project_template_manager.py|tests/test_template_mgr.py|g' \
  .github/workflows/ci.yml .github/workflows/pr-check.yml
```

- [ ] **Step 2: 验证**

```bash
grep -n "test_" .github/workflows/ci.yml .github/workflows/pr-check.yml
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "ci: 更新 CI workflows 中的测试文件路径"
```

---

### Task 12: 最终验证

**Interfaces:**
- Consumes: Task 1-11 全部完成
- Produces: 验证通过，项目可正常运行

- [ ] **Step 1: 运行 pytest（排除集成测试）**

```bash
PYTHONPATH=src python3 -m pytest tests/ --ignore=tests/test_integration.py -q
```

- [ ] **Step 2: ruff 检查**

```bash
ruff check src/scenefab tests
```

- [ ] **Step 3: 关键模块导入验证**

```bash
python3 -c "
# 验证所有关键模块可正常导入
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

- [ ] **Step 4: 验证无长文件名**

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
    print('OK: 无长文件名')
"
```

- [ ] **Step 5: 验证测试文件无长文件名**

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
    print('OK: 测试无长文件名')
"
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: 最终验证 — pytest + ruff + 导入检查通过"
```

---

## 回滚策略

如果验证失败，使用以下命令回滚到 Task 1 之前的状态：

```bash
git revert --no-commit HEAD~11..HEAD
git commit -m "chore: 回滚合规化改造（验证失败）"
```

或者直接重置：

```bash
git reset --hard <Task1 前的 commit hash>
```

## 预计改动统计

| 类别 | 数量 |
|------|------|
| 创建新目录 | 6 个 |
| git mv 文件 | 25 个 |
| 重命名文件（同目录） | 7 个 |
| 删除空目录 | 3 个 |
| 删除冗余脚本 | 3 个 |
| 更新 __init__.py | 4 个 |
| 更新源文件 import | 28 处 |
| 更新测试文件 import | 35 处 |
| 更新测试文件名/位置 | ~37 个 |
| 更新 CI workflow | 2 个 |
| 更新 .gitignore | 1 个 |
| 更新 vitepress config | 1 个 |
| 总 commit 数 | 12 |
