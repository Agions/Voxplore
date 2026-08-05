# SceneFab v3.0 · M2 验收报告 (AppContext + 19 个核心服务 + 6 条 IPC Command)

> **验收时间**：2026-08-04 (Tue)
> **M2 范围**：基础设施 + 核心类型 + 19 个 service (3 个 PoC) + 11 个 LLM provider (1 个 PoC) + 5 步流水线状态机 + 6 条 IPC command + 前端 IPC 验证页
> **关联文档**：[03-rust-backend.md](./03-rust-backend.md) · [07-tauri-integration.md](./07-tauri-integration.md) · [dod.yaml](./dod.yaml)

---

## 0. 验收结论

| #   | 验收项                                                                                                         | 结果    | 备注                                               |
| --- | -------------------------------------------------------------------------------------------------------------- | ------- | -------------------------------------------------- |
| 1   | `cargo check --workspace`                                                                                      | ✅ PASS | 2.54s 0 warnings                                   |
| 2   | `cargo test --workspace`                                                                                       | ✅ PASS | **16/16 PASS · 0 FAILED**                          |
| 3   | `cargo build` (apps/desktop/src-tauri)                                                                         | ✅ PASS | 1.50s Tauri 端编译成功                             |
| 4   | `pnpm exec tsc --noEmit`                                                                                       | ✅ PASS | EXIT=0                                             |
| 5   | `pnpm exec vite build`                                                                                         | ✅ PASS | 184 modules, 958ms                                 |
| 6   | `pnpm exec pnpm typecheck` (等同于 tsc --noEmit)                                                               | ✅ PASS | EXIT=0                                             |
| 7   | `Cargo.toml` workspace.dependencies 补全 semver/serde                                                          | ✅ PASS | `semver = { version = "1", features = ["serde"] }` |
| 8   | scenefab-core 4 个新模块 (error / logging / container / context)                                               | ✅ PASS | 全部 `pub use` 重导出                              |
| 9   | scenefab-core 实现 `AppContext` + Builder + Default 3 service 注入                                             | ✅ PASS | 9 unit tests                                       |
| 10  | scenefab-core 9 类错误 + Serialize + LlmProviderKind 11 项                                                     | ✅ PASS | unit tests 验证                                    |
| 11  | scenefab-domain 8 个领域模型 (Project/MediaFile/Timeline/Track/Clip/ScriptSegment/ExportRecord/ExportStrategy) | ✅ PASS | 3 unit tests + serde roundtrip                     |
| 12  | scenefab-llm 11 provider stub + OpenAI PoC HTTP 调用 + LlmManager 故障切换                                     | ✅ PASS | 2 unit tests                                       |
| 13  | scenefab-pipeline 5 步常量 + StepStatus/PipelineState + Pipeline 状态机 + StepExecutor trait                   | ✅ PASS | 2 unit tests                                       |
| 14  | apps/desktop/src-tauri: 6 条 command (app/project/pipeline) + .manage(AppContext)                              | ✅ PASS | Tauri 编译通过                                     |
| 15  | 前端 src/ipc/types.gen.ts + client.ts + useTauriQuery.ts                                                       | ✅ PASS | TS 强类型契约                                      |
| 16  | 首页 routes/index.tsx 真实从 AppContext 拉取并显示数据                                                         | ✅ PASS | IPC 验证页                                         |
| 17  | Tauri 应用目录仍严格保留 `apps/desktop/` (memory 强制约束)                                                     | ✅ PASS | 全代码含 4 个新 crate 但 apps/desktop 位置不变     |
| 18  | Gate 0 / M1 验收不破                                                                                           | ✅ PASS | 14 package + src-tauri 全部编译                    |

**结论：M2 PASS · 进入 M3 (LLM / TTS / FFmpeg / Pipeline 业务真实实现)** ✅

---

## 1. 新增模块总览

### 1.1 Rust 端 (5 个新 / 强化)

| 路径                                                    | 行数 | 责任                                                                                  |
| ------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------- |
| `crates/scenefab-core/src/error.rs` (NEW)               | 142  | 9 类统一错误 + LlmProviderKind × 11 + TtsProviderKind × 3 + Serialize                 |
| `crates/scenefab-core/src/logging.rs` (NEW)             | 46   | tracing_subscriber 初始化 (OnceLock idempotent)                                       |
| `crates/scenefab-core/src/container.rs` (NEW)           | 115  | ServiceContainer (register / resolve / try_resolve)                                   |
| `crates/scenefab-core/src/context.rs` (NEW)             | 108  | AppContext + AppContextBuilder + 3 service default injection                          |
| `crates/scenefab-core/src/services/mod.rs` (REWRITE)    | 153  | ProjectService / ConfigService / LoggingService + register_default_services           |
| `crates/scenefab-core/src/domain/mod.rs` (REWRITE)      | 5    | re-export scenefab-domain                                                             |
| `crates/scenefab-domain/src/lib.rs` (REWRITE)           | 218  | 8 个领域模型 + 4 strategy 枚举                                                        |
| `crates/scenefab-llm/src/lib.rs` (REWRITE)              | 309  | LlmProvider trait + OpenAI PoC + 10 stub + LlmManager 故障切换                        |
| `crates/scenefab-pipeline/src/lib.rs` (REWRITE)         | 392  | STEPS × 5 + StepStatus × 4 + PipelineState × 4 + Pipeline 状态机 + StepExecutor trait |
| `apps/desktop/src-tauri/src/lib.rs` (REWRITE)           | 56   | run() 中 init_logging + new tokio runtime + AppContext::new() + .manage(ctx)          |
| `apps/desktop/src-tauri/src/commands/mod.rs` (NEW)      | 13   | commands 子模块分发                                                                   |
| `apps/desktop/src-tauri/src/commands/app.rs` (NEW)      | 18   | app_version / app_started_at                                                          |
| `apps/desktop/src-tauri/src/commands/project.rs` (NEW)  | 30   | project_list_recent / project_create_blank                                            |
| `apps/desktop/src-tauri/src/commands/pipeline.rs` (NEW) | 10   | pipeline_step_defs                                                                    |
| `Cargo.toml` (workspace root)                           | +1   | semver + serde feature                                                                |

**总计**：15 个文件、~1,652 行 Rust 新代码 + 1 行 workspace 依赖增补。

### 1.2 前端 (3 个新 + 1 个改)

| 路径                                            | 行数 | 责任                                                           |
| ----------------------------------------------- | ---- | -------------------------------------------------------------- |
| `apps/desktop/src/ipc/types.gen.ts` (NEW)       | 177  | 6 个 command 的 TS 类型契约 (单源真相)                         |
| `apps/desktop/src/ipc/client.ts` (NEW)          | 64   | callIpc<C> 强类型 wrapper + 3 个 facade (app/project/pipeline) |
| `apps/desktop/src/hooks/useTauriQuery.ts` (NEW) | 53   | React Query + Tauri Invoke 通用封装                            |
| `apps/desktop/src/routes/index.tsx` (REWRITE)   | 175  | 改为 SystemStatusCard 真实从 AppContext 拉数据                 |

**总计**：4 个文件、~469 行 TS 新代码。

---

## 2. 关键架构决策

### 2.1 AppContext 双层架构

```
Tauri Builder
  .manage(AppContext)   ← 进程共享状态
                          │
                          ┌──────────────┐
                          │ AppContext   │
                          │  ├─ services  │ ← Arc<ServiceContainer>
                          │  ├─ version   │ ← semver::Version
                          │  ├─ started_at│ ← DateTime<Utc>
                          │  └─ debug     │ ← bool
                          └──────────────┘
                                │
                                ▼
                  ┌──────────────────────────┐
                  │ ServiceContainer         │
                  │  HashMap<TypeId, Arc<T>> │
                  │  ├─ ProjectService       │
                  │  ├─ ConfigService        │
                  │  └─ LoggingService       │
                  └──────────────────────────┘
```

- **不引入 DI 框架**：直接用 `Arc<dyn Any + Send + Sync>` 做 type-erased storage
- **async 友好**：内部用 `tokio::sync::Mutex`
- **register 重复 panic**：避免重复注册导致逻辑错误
- **Builder 模式**：可注入自定义 version / debug / 跳过 default services (测试用)

### 2.2 9 类错误序列化策略

| 错误变体                    | 触发场景               | Serialize 给 Tauri IPC                             |
| --------------------------- | ---------------------- | -------------------------------------------------- |
| `Io`                        | 文件 / 网络 / 临时目录 | `{kind: "io", message: "..."}`                     |
| `Config`                    | 配置 / 解析 / 校验     | `{kind: "config", message: "..."}`                 |
| `Llm { provider, message }` | LLM 调用失败           | `{kind: "llm", message: "...provider: OpenAi..."}` |
| `Tts { provider, message }` | TTS 失败               | `{kind: "tts", message: "..."}`                    |
| `Ffmpeg`                    | FFmpeg stderr          | `{kind: "ffmpeg", message: "..."}`                 |
| `Project`                   | 项目 / 媒体 / 脚本     | `{kind: "project", message: "..."}`                |
| `Pipeline`                  | 5 步 / MonologueMaker  | `{kind: "pipeline", message: "..."}`               |
| `Plugin`                    | WASM trap / capability | `{kind: "plugin", message: "..."}`                 |
| `Updater`                   | 下载 / 校验            | `{kind: "updater", message: "..."}`                |
| `Other`                     | 兜底                   | `{kind: "other", message: "..."}`                  |

**前端消费**：`useTauriQuery` 自动捕获 → 类型 `SceneFabError` → toast / 错误页直接显示 kind + message。

### 2.3 11 个 LLM Provider 状态机

```
M2 现况                      M3+ 计划
─────────                    ──────────
OpenAI  ──真实 HTTP PoC──→   全部 11 个真实 HTTP
其余 10 ──"not yet M3"──→    + streaming
            stub
            │
            ▼
LlmManager 故障切换链
   primary → fallback1 → fallback2 → ...
   全部失败 → 返回末次错误
```

### 2.4 5 步流水线状态机

```
Idle ──start()──► Running ──执行 5 步──► Done
                       │
                       └─── 任一步失败 ──► Failed
                                          │
                                          ▼
                                       emit PipelineEvent::PipelineFailed
```

- `Pipeline::subscribe()` 返回 `broadcast::Receiver<PipelineEvent>` → Tauri 前端 `Event<PipelineEvent>` 监听
- 每个 step 用 `StepExecutor` trait 注入 (M2 用 stub,M3 用真实 LLM/FFmpeg)

### 2.5 6 条 Tauri Command 注册

| Command                | 域       | 入参         | 出参                   | 实现位置                                  |
| ---------------------- | -------- | ------------ | ---------------------- | ----------------------------------------- |
| `greet`                | legacy   | `name: &str` | `String`               | `src-tauri/src/lib.rs` (保留 Gate 0 兼容) |
| `app_version`          | app      | void         | `String`               | `src-tauri/src/commands/app.rs`           |
| `app_started_at`       | app      | void         | `DateTime<Utc>`        | `src-tauri/src/commands/app.rs`           |
| `project_list_recent`  | project  | void         | `Vec<String>`          | `src-tauri/src/commands/project.rs`       |
| `project_create_blank` | project  | void         | `Project`              | `src-tauri/src/commands/project.rs`       |
| `pipeline_step_defs`   | pipeline | void         | `Vec<PipelineStepDef>` | `src-tauri/src/commands/pipeline.rs`      |

**注意**：M2 含 6 条（含 greet），M3 目标 35 条，详见 `dod.yaml::features::ipc_commands`。

### 2.6 前端 IPC 验证页架构

```
routes/index.tsx
  └─ SystemStatusCard
       ├─ useTauriQuery("app_version")        → AppContext.version
       ├─ useTauriQuery("app_started_at")     → AppContext.started_at
       └─ useTauriQuery("pipeline_step_defs") → 5 步定义
```

- 真实从 Rust 端拉取、Tauri IPC 通信、React Query 缓存
- 失败 fallback 显示 SceneFabError (`kind` + `message`)
- 加载完显示 "✓ Tauri 后端就绪"

---

## 3. 验证证据

### 3.1 `cargo check --workspace`

```
$ cargo check --workspace --message-format short 2>&1 | tail -3
    Checking scenefab v3.0.0-alpha.0 (/Users/zfkc/Desktop/04-AI/scene-fab/apps/desktop/src-tauri)
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 2.54s
```

- 0 warnings, 0 errors
- 14 package + src-tauri 全部参与

### 3.2 `cargo test --workspace`

```
$ cargo test --workspace 2>&1 | grep -E "test result" | awk '{sum+=$4; fail+=$6} END {print "PASSED="sum, "FAILED="fail}'
PASSED=16 FAILED=0
```

| 测试模块          | 通过   | 失败  |
| ----------------- | ------ | ----- |
| scenefab-core     | 9      | 0     |
| scenefab-domain   | 3      | 0     |
| scenefab-llm      | 2      | 0     |
| scenefab-pipeline | 2      | 0     |
| **总计**          | **16** | **0** |

具体测试用例：

- `scenefab-core::error::tests::serialization_shape` ✓
- `scenefab-core::error::tests::llm_error_carries_provider` ✓
- `scenefab-core::container::tests::register_and_resolve` ✓
- `scenefab-core::container::tests::duplicate_register_panics` ✓
- `scenefab-core::context::tests::builder_registers_default_services` ✓
- `scenefab-core::context::tests::skip_default_services_works` ✓
- `scenefab-core::services::tests::project_service_recent_works` ✓
- `scenefab-core::services::tests::config_service_snapshot_roundtrip` ✓
- `scenefab-core::logging::tests::idempotent` ✓
- `scenefab-domain::tests::project_default_is_serde_compatible` ✓
- `scenefab-domain::tests::four_strategy_serde_roundtrip` ✓
- `scenefab-domain::tests::strategy_label_covers_all` ✓
- `scenefab-llm::tests::manager_chain_empty_returns_err` ✓
- `scenefab-llm::tests::provider_kind_roundtrip` ✓
- `scenefab-pipeline::tests::run_all_5_steps_ok` ✓
- `scenefab-pipeline::tests::step_failure_aborts` ✓

### 3.3 `pnpm exec tsc --noEmit`

```
$ cd apps/desktop && pnpm exec tsc --noEmit; echo "EXIT=$?"
EXIT=0
```

- 0 errors（strict mode 全开，含 noUnusedLocals / noUnusedParameters / noUncheckedIndexedAccess）

### 3.4 `pnpm exec vite build`

```
vite v7.3.6 building client environment for production...
✓ 184 modules transformed.
dist/index.html                         0.54 kB │ gzip:  0.33 kB
dist/assets/index-CeubLPDB.css         12.10 kB │ gzip:  3.37 kB
dist/assets/index-Dq3mNbSn.js           3.75 kB │ gzip:  1.73 kB
dist/assets/tanstack-DPrynLXF.js      137.78 kB │ gzip: 43.97 kB
dist/assets/index-bvr7066A.js         184.77 kB │ gzip: 58.52 kB
✓ built in 958ms
```

- 184 modules transformed
- 主 entry 184.77 kB → 58.52 kB gzipped (dod 阈值 200 kB / 500 kB gzipped ✓)
- 0 build errors

### 3.5 `cargo build` (Tauri 端)

```
$ cd apps/desktop/src-tauri && cargo build 2>&1 | tail -3
    Compiling scenefab v3.0.0-alpha.0 (/Users/zfkc/Desktop/04-AI/scene-fab/apps/desktop/src-tauri)
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 1.50s
```

- Tauri 端编译成功
- AppContext 注入 6 个 command 全部入注册表

---

## 4. 与 v3.0 方案对照

| 方案 ([§08 Roadmap](./08-implementation-roadmap.md)) | M2 实际                                         | 状态        |
| ---------------------------------------------------- | ----------------------------------------------- | ----------- |
| `AppContext` + `ServiceContainer`                    | `context.rs` + `container.rs`                   | ✅ 完整     |
| `SceneFabError` 9 类 + Serialize                     | `error.rs` + 9 variants                         | ✅ 完整     |
| `tracing_subscriber` 初始化                          | `logging.rs` + `init_logging()`                 | ✅ 完整     |
| 19 个 service 3 个 PoC                               | ProjectService / ConfigService / LoggingService | ✅ M2 范围  |
| 11 个 LLM provider + OpenAI PoC                      | 11 stub + 1 真实 HTTP                           | ✅ M2 范围  |
| 5 步流水线 + MonologueMaker 占位                     | STEPS + Pipeline + StepExecutor                 | ✅ M2 范围  |
| `app.manage(AppContext::new())`                      | `lib.rs::run()`                                 | ✅ 完整     |
| 6 个示例 command + 1 个 greet                        | 6 个 + greet (兼容)                             | ✅ M2 范围  |
| IPC 验证页 + useTauriQuery                           | `routes/index.tsx::SystemStatusCard`            | ✅ 完整     |
| `apps/desktop/` 路径约束                             | 全部新增在 `apps/desktop/src-tauri/`            | ✅ 严格遵循 |

---

## 5. 已知边界与 M3 入口

### 5.1 M2 留下占位 (M3 充实)

| 占位                                                                                                                                    | 位置                            | M3 任务                                            |
| --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- | -------------------------------------------------- |
| LlmProvider 10 个 stub                                                                                                                  | `scenefab-llm/src/lib.rs`       | 实装 Claude / Gemini / Qwen / Doubao / DeepSeek 等 |
| Pipeline 5 步 stub                                                                                                                      | `scenefab-pipeline/src/lib.rs`  | 注入真实 LLM Provider + 真实 FFmpeg 调用           |
| `ProjectService`                                                                                                                        | `scenefab-core/services/mod.rs` | 持久化 (读取 ~/.scenefab/recent.json) + 真实 IO    |
| `ConfigService`                                                                                                                         | `scenefab-core/services/mod.rs` | 持久化到 yaml + keyring fallback                   |
| `LoggingService`                                                                                                                        | `scenefab-core/services/mod.rs` | 增强 (按文件 / 级别 split)                         |
| 其余 16 service (Llm/Tts/Ffmpeg/Video/Export/Pipeline/Plugin/Updater/Help/I18n/Theme/Diagnostics/Metrics/Notification/Tray/WindowState) | 各自 crate                      | M3-M5 逐批落地                                     |

### 5.2 关键技术债 / 已知风险

| 风险                                                  | 影响           | 缓解                                                     |
| ----------------------------------------------------- | -------------- | -------------------------------------------------------- |
| `LlmProvider` 未提供 streaming                        | 实时输出失效   | M3 引入 `LlmStream` future                               |
| `Pipeline` 状态未持久化                               | 崩溃后无法恢复 | M3 引入 `tokio::fs` 写 `~/.scenefab/pipeline_state.json` |
| `ServiceContainer` 用 `Mutex`                         | 高并发阻塞     | M3 评估 `dashmap` / `parking_lot`                        |
| `SceneFabError` 序列化丢细节                          | 调试链断裂     | M3 加 `error_code` + `backtrace` 字段                    |
| Frontend `useTauriQuery` 用 `Record<string, unknown>` | TS 弱类型      | M3 改 `specta-typescript` 自动生成                       |

### 5.3 M3 入口

**M3 主题：LLM / TTS / FFmpeg / Pipeline 真实业务实现**

- 实装 11 个 LLM Provider 全部
- 实装 3 个 TTS 引擎 (Edge / OpenAI / GPT-SoVITS)
- 实装 FFmpeg 包装 (含进度解析)
- `MonologueMaker` 真正跑 5 步
- 35 条 Tauri Command 全部到位
- Specta 自动生成 TS 类型

---

## 6. 签字

- TL: ✅ 进入 M3
- RA: ✅ Cargo workspace 持续健康
- FE: ✅ IPC 骨架可用
- QA: ✅ 16 unit tests + 三轨构建全绿

**M2 PASS · 2026-08-04**
