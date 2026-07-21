# SceneFab 项目合规化设计规范

> 对标 Python 社区标准（PEP 8 / PEP 257 + 社区最佳实践）
> 目标：消除长文件名、过度设计、结构混乱，提升可读性和二次开发友好度

---

## 1. 命名规范

### 规则

- 所有文件名字符数 ≤ 25（不含扩展名）
- Python 模块使用 `snake_case`
- 文档使用 `kebab-case`

### 重命名映射

#### 源码文件

| 原文件名 | 新文件名 | 说明 |
|----------|----------|------|
| `project_template_manager.py` | `template_mgr.py` | 归入 `project/` 包后上下文已明确 |
| `narration_state_machine.py` | `state_machine.py` | 归入 `pipeline/narration/` 包 |
| `direct_video_exporter.py` | `video_exporter.py` | "direct" 由包上下文隐含 |
| `first_person_workflow.py` | `fp_workflow.py` | fp = first-person，项目内通用缩写 |
| `project_file_metadata.py` | `file_metadata.py` | 归入 `models/` 上下文已明确 |
| `batch_export_manager.py` | `batch_export.py` | 去掉冗余 `_manager` |
| `streaming_llm_worker.py` | `stream_worker.py` | 简化 |
| `caption_generator.py` | `caption_gen.py` | 归入 `video/` 后上下文已明确 |
| `video_tools/base.py` | `tool_base.py` | 归入 `video/` 后避免语义冲突 |

#### 测试文件

| 原文件名 | 新文件名 |
|----------|----------|
| `test_script_generator_streaming.py` | `test_script_stream.py` |
| `test_project_template_manager.py` | `test_template_mgr.py` |
| `test_project_settings_manager.py` | `test_settings_mgr.py` |
| `test_narration_state_machine.py` | `test_state_machine.py` |
| `test_first_person_extractor.py` | `test_fp_extractor.py` |
| `test_first_person_workflow.py` | `test_fp_workflow.py` |
| `test_direct_video_exporter.py` | `test_video_exporter.py` |
| `test_batch_export_manager.py` | `test_batch_export.py` |
| `test_emotion_peak_detector.py` | `test_emotion_peak.py` |
| `test_ui_page_view_models.py` | `test_page_vm.py` |

#### 文档

| 原文件名 | 新文件名 | 操作 |
|----------|----------|------|
| `first-person-narration-production.md` | `narration-spec.md` | 重命名 |

同步更新 `docs/.vitepress/config.ts` 中的路由链接：

```ts
// sidebar 和 nav 中的第一人称生产规范条目
link: '/guide/narration-spec'
```

---

## 2. 源码包结构

### 2.1 顶层归包

将 `src/scenefab/` 顶层散落的 7 个领域文件归入两个新包：

```
scenefab/
├── settings/                # 新包（全局配置 + 项目设置）
│   ├── __init__.py          # 导出 ConfigManager, ProjectSettingsManager
│   ├── config.py            # ← settings.py
│   ├── definitions.py       # ← settings_data.py
│   ├── types.py             # ← settings_types.py
│   └── manager.py           # ← settings_manager.py
├── project/                 # 新包（项目生命周期 + 模板）
│   ├── __init__.py          # 导出 ProjectManager, TemplateManager
│   ├── manager.py           # ← project_manager.py
│   ├── template_mgr.py      # ← project_template_manager.py
│   └── template_models.py   # ← template_models.py
├── application.py           # 保留
├── exceptions.py            # 保留
├── main.py                  # 保留
├── secure_key_manager.py    # 保留
├── signals_bridge.py        # 保留
```

### 2.2 服务层合并：`video_tools/` → `video/`

将 `services/video_tools/` 的 4 个模块并入 `services/video/`，删除 `video_tools/` 包：

```
services/video/
├── ffmpeg_tool.py           # ← video_tools/ffmpeg_tool.py
├── caption_gen.py           # ← video_tools/caption_generator.py
├── probe.py                 # ← video_tools/probe.py
├── hardware.py              # ← video_tools/hardware.py
├── tool_base.py             # ← video_tools/base.py
├── analyzer.py              # 原有
├── ...                      # 其余原有文件不变
```

所有 `from scenefab.services.video_tools.xxx` 更新为 `from scenefab.services.video.xxx`（约 8 处 import）。

### 2.3 空包扁平化

删除 `services/video/` 下两个仅含空 `__init__.py` 的子包：
- `grouping/` — 0 个实际模块
- `selection/` — 0 个实际模块

`cache/`、`models/`、`extraction/` 有实际内容，保留。

### 2.4 Pipeline narration 子包

将 5 个 `narration_*.py` 文件归入 `pipeline/narration/` 子包：

```
pipeline/
├── narration/               # 新子包
│   ├── __init__.py          # 导出核心 API
│   ├── engine.py            # ← narration.py
│   ├── context.py           # ← narration_context.py
│   ├── evaluator.py         # ← narration_evaluator.py
│   ├── state_machine.py     # ← narration_state_machine.py
│   └── steps.py             # ← narration_steps.py
├── assembly_steps.py
├── evaluation_steps.py
├── understanding_steps.py
├── fp_workflow.py           # ← first_person_workflow.py
├── short_drama.py
└── text_utils.py
```

### 2.5 不动的部分

以下结构已合规，不做变更：
- `core/` — 职责明确
- `models/` — `project_file_metadata.py` 仅重命名为 `file_metadata.py`
- `services/ai/` — 文件多但各司其职
- `services/export/` — 结构清晰
- `services/video_understanding/` — 独立职责
- `services/orchestration/` — 仅 2 文件但语义独立
- `ui/`、`plugins/`、`api/`、`utils/`、`update/`

---

## 3. 脚本清理

### 删除

| 文件 | 理由 |
|------|------|
| `scripts/build.py` | 与 Makefile + 平台 shell 脚本功能完全重复；内部 `publish_pypi` 调用不存在的 `pip upload` 命令（应为 `twine upload`），属于死代码 |
| `main.spec` | 无任何脚本/CI 引用它；三个平台构建脚本均使用 `pyinstaller main.py` + CLI 参数 |
| 根目录 `conftest.py` | 与 `tests/conftest.py` 职责重叠，合并后删除 |

### 合并

根目录 `conftest.py` 的 PySide6 跳过逻辑合并入 `tests/conftest.py`：

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

### 保留

| 文件 | 理由 |
|------|------|
| `main.py`（根目录） | PyInstaller 入口点，三个构建脚本均引用 |
| `Makefile` | 唯一构建入口 |
| `scripts/common.sh` | 被 build_macos.sh / build_linux.sh source 引用 |
| `scripts/build_macos.sh` | Makefile 调用 |
| `scripts/build_linux.sh` | Makefile 调用 |
| `scripts/build_windows.ps1` | Makefile 调用 |
| `scripts/resource_assets.py` | 图标生成，功能唯一 |
| `MANIFEST.in` | setuptools sdist 必需 |

---

## 4. .gitignore 瘦身

从 392 行精简至 ~80 行，删除 Django/Flask/Scrapy/Celery/SageMath/Jupyter 等无关条目及重复段落。

完整目标内容见下方 §4.1。

### 4.1 目标 .gitignore

```gitignore
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
```

---

## 5. 文档合规

### 文件重命名

| 原文件 | 新文件 | 操作 |
|--------|--------|------|
| `docs/guide/first-person-narration-production.md` | `docs/guide/narration-spec.md` | 重命名 |

### VitePress 配置同步

`docs/.vitepress/config.ts` 中两处引用更新为 `/guide/narration-spec`。

### ADR

ADR 源文件本就不存在于仓库（仅 vitepress dist 本地构建产物中有残留），且 sidebar/nav 未引用 ADR 页面。无需操作。

---

## 6. 测试目录对齐

统一为镜像 `src/scenefab/` 的目录结构：

```
tests/
├── conftest.py
├── __init__.py
├── core/
│   ├── test_signals_bridge.py
│   └── test_service_container.py
├── pipeline/
│   ├── test_narration/          # 跟随 §2.4
│   │   ├── test_state_machine.py
│   │   └── ...
│   ├── test_assembly_steps.py
│   ├── test_evaluation_steps.py
│   ├── test_understanding_steps.py
│   ├── test_fp_workflow.py
│   └── test_short_drama.py
├── services/
│   ├── ai/
│   │   ├── test_llm_base.py
│   │   ├── test_llm_providers.py
│   │   ├── test_vision_providers.py
│   │   ├── test_script_generator.py
│   │   ├── test_script_stream.py
│   │   ├── test_subtitle_extractor.py
│   │   ├── test_voice_generator.py
│   │   ├── test_model_catalog.py
│   │   └── test_ai_service_manager.py
│   ├── video/
│   │   ├── test_emotion_peak.py
│   │   ├── test_fp_extractor.py
│   │   ├── test_highlight_detector.py
│   │   ├── test_monologue_maker.py
│   │   ├── test_video_maker.py
│   │   ├── test_caption_gen.py
│   │   └── test_ffmpeg_tool.py
│   └── export/
│       ├── test_base_exporter.py
│       ├── test_jianying_exporter.py
│       ├── test_video_exporter.py
│       ├── test_batch_export.py
│       ├── test_export_presets.py
│       └── test_subtitle_exporter.py
├── ui/
│   ├── test_main_window.py
│   ├── test_page_vm.py
│   └── test_tray_manager.py
├── plugins/
│   └── test_loader.py
├── models/
│   ├── test_project_models.py
│   └── ...
├── test_config_manager.py
├── test_exceptions.py
├── test_resources.py
├── test_version.py
├── test_text_utils.py
├── test_benchmark.py
├── test_integration.py
├── test_smoke_pipeline.py
└── test_secure_key_manager.py
```

---

## 7. 实施约束

- **不做代码重构**：不拆分 >600 行的大文件（如 `main_window/__init__.py`），超出合规化范围
- **不做功能变更**：所有 import 路径更新仅为同名重映射，不改变运行时行为
- **直接重命名**：不保留旧路径兼容垫片
- **不动的部分**：`services/orchestration/`、`core/`、`services/ai/script_generator/` 等已合规结构保持不变

---

*设计完成，等待用户审阅后转入实施计划。*
