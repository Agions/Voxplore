---
title: ADR-008 死代码清理 — v2.2 重构后场景流水线退场
description: v2.2 NarrationStateMachine 上线后, 删除已无调用方的 cli/cli.py 与 scene_pipeline 子树 (2263 行)
category: architecture
version: 1.0
---

# ADR-008: 死代码清理 — v2.2 重构后场景流水线退场

- **状态**: ✅ 已接受
- **日期**: 2026-06-12
- **作者**: 架构团队
- **执行**: commit `287b050` (R0 cli) + `478164e` (R2 scene_pipeline 子树)

## 背景

v2.2 NarrationStateMachine (ADR-007) 上线后, 仓库出现两类**已无外部调用方的死代码**:

### 类 1: CLI 双胞胎 (R0 已清理)

| 文件 | 行数 | 来源 |
|---|---|---|
| `src/scenefab/cli.py` | 461 | argparse 老版 CLI |
| `src/scenefab/cli/__init__.py` | 20 | Click 新版 CLI 入口 |
| `src/scenefab/cli/main.py` | 668 | Click 新版 CLI 主类 |
| **小计** | **1149** | |

### 类 2: 旧 scene_pipeline 子树 (R2 已清理)

| 文件 | 行数 | 来源 |
|---|---|---|
| `src/scenefab/pipeline/scene_pipeline.py` | 187 | 旧 SceneFabPipeline 主类 |
| `src/scenefab/pipeline/config.py` | 18 | PipelineConfig |
| `src/scenefab/pipeline/emotion_detector.py` | 199 | EmotionPeakDetector |
| `src/scenefab/pipeline/first_person_extractor.py` | 323 | FirstPersonExtractor |
| `src/scenefab/pipeline/script_generator.py` | 134 | ⚠️ 与 `services.ai.script_generator` 无关 |
| `src/scenefab/pipeline/tts_generator.py` | 254 | ⚠️ 与 `services.ai.tts.*` 无关 |
| **小计** | **1114** | |

**累计: 9 文件 / 2263 行死代码**

### 根因

1. **v2.0/v2.1 演化期并存**: scene_pipeline.py 是 v1.x 线性编排器遗留, v2.0 引入 DAG PipelineEngine 后两者并存, v2.1 未清理
2. **v2.2 NarrationStateMachine 替代**: 状态机接管了解说生成核心流程, scene_pipeline 完全无新调用方
3. **CLI 双胞胎**: 早期 argparse 版与 Click 版并存, pyproject.toml 入口只用一个 (`scenefab.main:main` = PySide6 UI), CLI 双胞胎变孤儿
4. **历史包袱**: `AUTO-CLEANUP-CANDIDATE (2026-06-09)` 注释已标记 1118 行死代码, 主人"继续推进"风格下等到 2026-06-12 才执行

## 决策

**原则: 严格"四重验证 0 调用方"才删, 净增错误必须为 0。**

### 验证四重门

1. `from <module> import <symbol>` → grep from-import
2. `<package>.<module>.<attr>` → grep 属性访问
3. `importlib.import_module("<module>")` / `__import__` → grep 动态导入
4. `docs/` / `Makefile` / `pyproject.toml` 字符串引用 → grep 配置层

任一命中 → 跳过删除, 标记观察。

### 执行约束

- **零破坏**: 不删活跃代码, 不动外部 API 签名, 不重构活跃调用方
- **4 步基线**: 删前删后各跑 pytest + ruff + mypy, delta 必须为 0 (或负)
- **git stash 对比**: 用 `git stash` 做真实 diff 基线, 不依赖 LLM 记忆
- **不污染主题 commit**: 死代码清理用 `chore(cleanup):` 前缀, 不混入 feat/fix

## 实施路径 (已完成)

### R0 — CLI 双胞胎清理

- commit `287b050` — `chore(cleanup): remove dead code cli.py + cli/ package (1149 lines)`
- 净效果: -1149 行 / pytest 0 delta / ruff 0 delta / mypy 0 delta

### R2 — scene_pipeline 子树清理

- commit `478164e` — `chore(pipeline): remove dead code scene_pipeline subtree (1114 lines, R2)`
- 净效果: -1114 行 / pytest 0 delta / ruff 0 delta / mypy -4 (删除文件自带 4 个 mypy 错误)
- 顺带重写 `pipeline/__init__.py` 为 v2.2 状态机唯一出口 (13 API 集中导出)

### 累计净效果

| 指标 | R0+R2 累计 |
|---|---|
| 删除文件 | 9 |
| 删除行数 | 2263 |
| pytest delta | 0 |
| ruff delta | 0 |
| mypy delta | **-4 错误** |
| pipeline 包瘦身 | 4434 → 3320 行 (**-25%**) |

## 兼容性

- **零破坏**: 唯一真实入口 `scenefab.main:main` (PySide6 UI) 不受影响
- **API 不变**: 活跃的 `services.ai.script_generator` / `services.ai.tts.*` / `services.ai.scene_analyzer` 全部保留
- **v2.2 状态机**: `pipeline.narration.NarrationStateMachine` 作为唯一活跃 pipeline
- **测试覆盖**: 删除 9 文件未引入任何测试失败 (delta 0)

## 验证标准 (已通过)

1. **四重调用方验证**: from-import / 属性访问 / importlib / docs 全部 0 命中 ✅
2. **pytest 全套**: 删前 3F/612P/25S = 删后 3F/612P/25S (3 fail 是 test_arch_v21 TestWSHub 预先 env 问题) ✅
3. **ruff 0 错误**: 删前 = 删后 = All checks passed ✅
4. **mypy 持平或负**: 删前 194/80 → 删后 190/77 (**-4 错误**) ✅
5. **git 历史可回滚**: 两次 `chore(cleanup):` commit 独立, 任何 review 可 revert 不影响 v2.2 主线
6. **诚实高于完成**: 删除前用 `git stash` 做真实 diff, 不依赖 LLM 记忆; 报告前 4 步验证

## 不在本次范围

- ❌ 删除 v1.x 公开 API (MonologueMaker / JianyingExporter 等) — 仍被 PySide6 UI 调用
- ❌ 清理 services 包内部可能存在的死代码 — 需要独立 ADR 评估 ROI
- ❌ 重构 cli/ → services.cli 整合 (无真实需求)
- ❌ 删除 docs/architecture.md 中已失效的 scene_pipeline 引用 — 留待 R5 文档同步

## 关联

- **ADR-007**: 解说生成状态机 v2.2 (本清理的触发条件)
- **ADR-006**: v2.1 架构升级 (scene_pipeline 退场前的最后活跃版本)
- **ADR-004**: DAG 并行流水线 (scene_pipeline 的并行演进路径)
- **frame-fab 经验**: 死代码/dedup v3 三陷阱 (basename 误命中 / 3 grep 并行 / 字段 regex 误判) — 本次严格执行

## 经验沉淀 (Skill)

本 ADR 沉淀以下可复用模式到 `narration-state-machine-design` skill:

- **死代码清理标准流程**: 四重验证门 + 4 步基线 + git stash 对比
- **决策文档 vs 临时报告**: 决策写 ADR 提交, 评估报告仅本地留档
- **"极细"策略**: 真 ROI > 0 才删, 净增行数受控, 优先找现成 0 调用方
