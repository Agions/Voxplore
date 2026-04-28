# Voxplore 重构计划

**日期**: 2026-04-28  
**目标**: 架构重构 + 模块整理 + 代码清理

---

## 一、架构重构

### 问题 1：services.ai ↔ core 循环依赖

```
services.ai → core (via ImportError handling, registry, exceptions)
core.interfaces → services (via CacheConfig, etc.)
```

**方案**：在 `app/services/ai/` 和 `core/` 之间建立单向依赖边界。

- `core/` 为底层框架（配置、缓存、事件、项目管理）
- `services/` 为业务层，依赖 core 但 core 不依赖 services
- 现状：core 某些模块导入了 services（如 `core.interfaces`）
- 修复：core 只通过接口类型（字符串）引用 services，不直接导入

### 问题 2：UI 层过重

UI 模块文件行数过多（763/750/730 行），耦合太紧。

**方案**：MVVM 改造（不做 UI 重写，只拆分逻辑）

### 问题 3：配置分散

`config/` 下多个 yaml 散落，AppConfigManager 统一管理但仍有散落。

---

## 二、模块整理

### 目录重组方案

```
app/services/
├── ai/                 # AI 服务（已有）
│   ├── providers/       # LLM/Vision providers（已有）
│   ├── cache.py        # LLM 缓存（已有）
│   ├── registry.py     # provider 注册（已有）
│   └── __init__.py     # 统一导出
├── video/              # 视频处理（已有）
│   ├── extraction/     # 画面提取
│   ├── tools/         # 视频工具（ffmpeg/subtitle/caption/enhancer/analyzer/maker/voice/script/highlight）
│   └── __init__.py
├── audio/              # 音频处理（已有）
│   └── beat_detector.py
├── export/             # 导出（已有）
│   ├── video_exporter.py
│   ├── direct_video_exporter.py
│   └── jianying_exporter.py
└── orchestration/       # 编排（已有）
```

**实际已有目录已较清晰，不做大改。只补充缺失的 `__init__.py` 导出组织。**

---

## 三、代码清理

### 3.1 文件拆分（TOP 文件）

| 文件 | 行数 | 拆解目标 |
|------|------|----------|
| `projects_page.py` | 763 | 拆分：列表逻辑 → `ProjectListViewModel`、卡片逻辑 → `ProjectCard` 组件 |
| `step_upload.py` | 750 | 拆分：上传逻辑 → `UploadViewModel`、文件选择 → 组件 |
| `step_preview.py` | 730 | 拆分：预览逻辑 → `PreviewViewModel`、播放器 → 组件 |
| `project_manager.py` | 716 | Qt 耦合，保留但移除冗余注释 |
| `script_generator_streaming.py` | 701 | Stream 生成逻辑独立 |
| `monologue_maker.py` | 658 | 拆分：文本分析 / 生成两部分 |
| `scene_analyzer.py` | 658 | 拆分：分析 / 生成两部分 |

### 3.2 代码重复清理

- `app/services/ai/` 下多个 provider 有重复的错误处理模式 → 提取公共基类
- `app/core/` 多个 manager 有类似的 `get_project()` 逻辑 → 提取 `ProjectAccessMixin`

### 3.3 死代码清理

- 无用 import
- 注释掉的代码块（有 git 历史，直接删）
- 空方法（只有 `pass` 或 `...`）

---

## 四、实施步骤

### Phase 1: 架构边界（优先级 1）

1. 梳理 `core` ↔ `services` 真实依赖图
2. 消除 `core` 对 `services` 的直接导入（改为字符串类型引用或延迟导入）
3. 验证：pytest 通过 + lint 通过

### Phase 2: 模块结构整理（优先级 2）

1. 补全 `app/services/` 各 `__init__.py` 导出
2. 建立 `app/services/__init__.py` 统一导出公共类型
3. 移动散落的配置文件到 `config/` 统一管理

### Phase 3: 文件拆分（优先级 3）

1. `projects_page.py` → `ProjectListViewModel` + `ProjectsGrid` 组件
2. `step_preview.py` → `PreviewViewModel` + 播放器组件
3. Stream 生成类 → 独立模块

### Phase 4: 重复代码提取（优先级 4）

1. 提取 Provider 公共基类（错误处理 + 重试 + mock）
2. 提取 `ProjectAccessMixin` 到 `core/mixins.py`

### Phase 5: 死代码清理（优先级 5）

1. 运行 `ruff check app/ --select F401,F811` 找无用导入
2. 清理注释代码块
3. 清理空方法

---

## 五、约束

- 不改变任何功能行为（所有改动后测试必须通过）
- UI 组件只做逻辑拆分，不改 PySide6 实现
- 每个阶段完成后必须 `pytest -x -q` 通过
- Git commit 格式：`refactor: [模块] [改动简述]`

---

_计划创建：2026-04-28_
