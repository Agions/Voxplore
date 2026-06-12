# ADR-006: v2.1 架构升级 — 单源真相 + 类型化事件 + DI 现代化

- **状态**: ✅ 已接受
- **日期**: 2026-06-04
- **作者**: 架构团队

## 背景

v2.0 解决了"性能 + 业务能力"（DAG 流水线、短剧特化、FFmpeg 安全加固、审计日志）。但 v2.0 后项目存在**架构债**：

1. **两个 EventBus 实现并存**：`scenefab.core.EventBus` 和 `scenefab.event_bus.EventBus` 各自维护独立 handler 列表 → 同名事件不能跨模块共享
2. **TaskManager 与 PipelineEngine 无事件桥接**：状态变更靠 Qt Signal，无法跨 CLI/API/Web 共享
3. **FastAPI router 用私货 `_tasks: dict = {}`**：CLI 跑的任务 Web 看不到
4. **ServiceContainer 自研**（v1.x 247 行）：缺作用域、缺钩子
5. **配置分散**（`settings.py` dataclass + `settings_manager.py` JSON）：缺类型安全、缺动态重载

## 决策

v2.1 目标：**用"单源真相 + 类型化事件 + 依赖注入"三大支柱统一运行时骨架**，且 **零破坏**（v1.x 公开 API 100% 兼容）。

### 支柱 1：UnifiedEventBus 单源真相

- 单一权威实现 `scenefab.core.unified_event_bus.UnifiedEventBus`
- v1.x 两个 EventBus 全部委托到此（薄包装，公开 API 不变）
- 全局单例：函数级 `_global_bus` + 类级 `_default_instance` **双轨制**，由 `set_event_bus()` 同步两者
- 支持：
  - 字符串事件（v1.x 兼容）
  - `DomainEvent` 类型化事件（v2.1 强类型）
  - sync / async handler 混合
  - `EventLog` 内存重放
  - `stats()` 可观测

### 支柱 2：DomainEvent 强类型

8 个预定义事件 + 任意自定义：
- Pipeline: `PipelineStarted / StepStarted / StepCompleted / PipelineCompleted`
- Task: `TaskCreated / TaskProgressUpdated / TaskStatusChanged`
- 业务: `LLMTokenGenerated / FFmpegExecuted`

`TaskManager.create_task / set_status / update_progress` 和 `PipelineEngine.run / _execute_step` 在关键节点发布事件 → 任何订阅者（CLI / FastAPI / WS / 审计）都可观察。

### 支柱 3：DI 容器 + 任务存储 + 事件存储 三件套

- `DIContainer`：v1.x 兼容 + SCOPED 作用域 + 解析钩子 + 全局 `get_app_container()` 自动注入 event_bus
- `TaskStore`：3 后端 (InMemory / SQLite / Redis) + TTL + 全局共享，FastAPI router 私货 `_tasks: dict` 替换为 `get_task_store()`
- `EventStore`：3 后端 (InMemory / SQLite / Redis) + 按 event_name / correlation_id 查询 + `install_event_store_into_bus()` 自动双写

### 附加

- `SettingsV2` (pydantic-settings)：7 个子配置组，env 自动映射，JSON Schema 生成
- `WSHub`：WebSocket 实时推送，从 UnifiedEventBus 订阅事件分发到连接

## 不决策的

- **不替换 v1.x ServiceContainer**：v2.1 新增 DIContainer 并列存在，旧代码继续工作
- **不替换 v1.x Task dataclass**：仍可用，新增 UnifiedTask 作为更现代的替代
- **不破坏 v1.x pipeline.py**：保留 `PipelineConfig / SceneFabPipeline` 公开 API

> **🟡 状态更新 (2026-06-12)**: 上方 v1.x pipeline 公开 API 在 [ADR-008](./008-dead-code-cleanup.md) 中已清理.
> SceneFabPipeline / PipelineConfig / EmotionPeakDetector / FirstPersonExtractor / pipeline.script_generator
> / pipeline.tts_generator / cli.py / cli/ 包共 2263 行死代码已删除, 由 v2.2 NarrationStateMachine
> ([ADR-007](./007-narration-state-machine.md)) 完全接管解说生成核心流程. 此处历史决策保留作为 v2.1 当时事实记录.

## 后果

- ✅ 33/33 v2.0 测试 + 43/43 v2.1 测试全过（76/76 零回归）
- ✅ v1.x 公开 API 完全兼容（`scenefab.core.EventBus / scenefab.event_bus.EventBus / ApplicationState / ErrorInfo` 等）
- ✅ 新增 ~3000 行（7 个新 core 模块 + 测试套件）
- ⚠️ 引入 pydantic-settings 依赖（已有 requirements.txt，零新增）
- ⚠️ FastAPI router 行为完全等价（接口不变，后端换了）

## 参考

- 5 篇前作 ADR（001-005）保持不变
- 测试：`tests/test_arch_v21.py`（43 tests, 8 test classes）
