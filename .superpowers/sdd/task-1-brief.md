# Task 1: 创建新包目录结构

## 位置
项目根目录: `/Users/zfkc/Desktop/04-AI/scene-fab`

## 任务描述
创建三个新包的目录结构和 `__init__.py` 文件，为后续文件移动做准备。

## 具体步骤

### Step 1: 创建 settings/ 包

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

### Step 2: 创建 project/ 包

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

### Step 3: 创建 pipeline/narration/ 子包

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

### Step 4: 验证目录结构

```bash
ls -la src/scenefab/settings/__init__.py src/scenefab/project/__init__.py src/scenefab/pipeline/narration/__init__.py
```

### Step 5: Commit

```bash
git add -A
git commit -m "refactor: 创建 settings/ project/ pipeline/narration/ 新包结构"
```

## 验证
执行 Step 4 确认三个 `__init__.py` 文件存在。

## 全局约束
- 不做功能变更
- 直接创建，不保留旧文件
- 每个文件内容必须与上方代码块完全一致
