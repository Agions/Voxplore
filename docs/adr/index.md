---
title: 架构决策记录 (ADR)
description: SceneFab 关键架构决策的背景、权衡与结论汇总。
---

# 架构决策记录 (ADR)

ADR（Architecture Decision Record）记录 SceneFab 在演进过程中做出的关键架构决策：**为什么这样选、权衡了什么、结论是否仍然成立**。每条 ADR 都是一次性写定的历史记录，便于新成员理解系统现状的由来。

| 编号 | 决策 | 状态 |
| --- | --- | --- |
| [ADR-001](./001-pyside6-vs-electron) | PySide6 vs Electron 作为桌面端 GUI 框架 | ✅ Accepted |
| [ADR-002](./002-local-processing-vs-cloud-rendering) | 全量本地处理 vs 云端渲染 | ✅ Accepted |
| [ADR-003](./003-event-driven-ioc-architecture) | 事件驱动 + IoC 容器架构 | ✅ Accepted |
| [ADR-004](./004-dag-parallel-pipeline) | DAG 并行流水线 vs 串行流水线 | ✅ Accepted (v2.0) |
| [ADR-005](./005-f5-tts-vs-cloud-tts) | F5-TTS 本地零样本 vs 云端 TTS | ✅ Accepted |
| [ADR-006](./006-v21-architecture-upgrade) | v2.1 架构升级：单源真相 + 类型化事件 + DI 现代化 | ✅ Accepted |
| [ADR-007](./007-narration-state-machine) | 解说生成状态机：上下文工程 + 状态机流水线 | ✅ Accepted |

## 阅读建议

- 想了解**整体形态**：先读 ADR-001 / ADR-002（桌面端 + 本地优先的两条产品基线）。
- 想了解**运行时架构**：ADR-003 / ADR-006（事件总线 + DI 容器）与 ADR-004（并行流水线）。
- 想了解**解说生成核心**：ADR-007（状态机 + 四类上下文），并对照[架构概览](../architecture)。

> 这些决策的当前落地形态见[架构概览](../architecture)；面向开发者的弃用与迁移计划见仓库内 `docs/deprecations.md`（不在本站导航）。
