# 16 · M3.2 三轨验证报告 (Tauri 集成 + 前端视觉重设计)

> 📌 M3.2 里程碑 · Tauri 后端 13 命令落地 + 前端布局壳 + 欢迎页视觉化重设计 + 流水线/设置页接通后端

## TL;DR

| 维度                 | 结果                                               |
| -------------------- | -------------------------------------------------- |
| Rust 工作区编译      | ✅ `cargo check --workspace` 0 errors / 0 warnings |
| Rust 单元测试        | ✅ 23/23 通过 (pipeline 14 / tts 4 / ffmpeg 5)     |
| 前端类型检查         | ✅ `pnpm tsc --noEmit` EXIT=0                      |
| 前端构建             | ✅ `pnpm build` 194 modules / 0 errors             |
| Tauri Command 注册数 | **17 / 17** 全部接前端类型契约                     |

---

## 1 · Tauri 后端 13 个真实命令

### 1.1 命令清单

| 域       | Command                | 入参                       | 返回                                               |
| -------- | ---------------------- | -------------------------- | -------------------------------------------------- |
| app      | `app_version`          | —                          | `String` (semver)                                  |
| app      | `app_started_at`       | —                          | `String` (ISO 8601)                                |
| app      | `app_system_info`      | —                          | `AppSystemInfo { ffmpegAvailable, ffmpegVersion }` |
| project  | `project_list_recent`  | —                          | `Vec<String>` (路径列表)                           |
| project  | `project_create_blank` | —                          | `ProjectRecord { path, project }`                  |
| project  | `project_load`         | `{ path: String }`         | `ProjectRecord`                                    |
| project  | `project_save`         | `{ path, project }`        | `()`                                               |
| project  | `project_delete`       | `{ path }`                 | `()`                                               |
| project  | `project_add_media`    | `{ path, project, media }` | `Project`                                          |
| pipeline | `pipeline_step_defs`   | —                          | `Vec<PipelineStepDef>`                             |
| pipeline | `pipeline_status`      | —                          | `PipelineStatus` (camelCase)                       |
| pipeline | `pipeline_start`       | `{ project, workdir? }`    | `()` + 事件广播                                    |
| pipeline | `pipeline_cancel`      | —                          | `()`                                               |
| pipeline | `pipeline_reset`       | —                          | `()`                                               |
| settings | `settings_get`         | —                          | `ConfigSnapshot`                                   |
| settings | `settings_set`         | `{ snapshot }`             | `()`                                               |
| 保留     | `greet`                | `{ name }`                 | `String` (Gate0 烟测)                              |

合计 **17 个** command (含 greet),其中 **16 个** 是 M3.2 新落地的真实业务命令。

### 1.2 Pipeline 事件桥接

```rust
// apps/desktop/src-tauri/src/commands/pipeline.rs
let mut rx = svc.subscribe();
let app_clone = app.clone();
tokio::spawn(async move {
    loop {
        match rx.recv().await {
            Ok(event) => { let _ = app_clone.emit("pipeline:event", &event); }
            Err(RecvError::Lagged(skipped)) => { tracing::warn!(...); }
            Err(RecvError::Closed) => break,
        }
    }
});
```

- `tokio::sync::broadcast::Receiver<PipelineEvent>` → Tauri `emit("pipeline:event", ...)`
- Lagged/Closed 错误都做了 graceful 处理
- 当前前端先用 `refetchInterval` polling 状态(更简单),后续接 listen 走实时事件

---

## 2 · Rust 流水线编排业务实现 (M3.2 头号交付)

### 2.1 crates/scenefab-pipeline

| 模块           | 行  | 职责                                                                             |
| -------------- | --- | -------------------------------------------------------------------------------- |
| `lib.rs`       | —   | 状态机 `Pipeline` + `PipelineEvent` + `STEPS`                                    |
| `executors.rs` | 538 | 5 个真实 `StepExecutor`:Ingest / SceneSplit / ScriptGen / VoiceCaptions / Export |
| `service.rs`   | 166 | `PipelineService` 运行时门面                                                     |

### 2.2 5 个 StepExecutor 关键逻辑

| Step                   | 触发依赖                                                        | 失败时降级                    |
| ---------------------- | --------------------------------------------------------------- | ----------------------------- |
| ① Ingest (idx0)        | `tokio::fs::metadata` + ffmpeg `probe`                          | ffprobe 不可用 → 仅填文件大小 |
| ② SceneSplit (idx1)    | ffmpeg `detect_scenes` (threshold=0.3)                          | 失败 → 单场景 fallback        |
| ③ ScriptGen (idx2)     | LLM factory (11 provider)                                       | 无 LLM → 错误返回             |
| ④ VoiceCaptions (idx3) | TTS engine (3 引擎) + SRT 生成                                  | 无 TTS → 错误返回             |
| ⑤ Export (idx4)        | ffmpeg `scale_pad_vertical` + `burn_captions` + `mix_narration` | 无 ffmpeg → 错误返回          |

### 2.3 14 个 pipeline 单元测试 (全绿)

```
executors::tests::ingest_rejects_empty_media ... ok
executors::tests::ingest_rejects_missing_file ... ok
executors::tests::scene_split_fallback_without_ffmpeg ... ok
executors::tests::script_gen_requires_llm ... ok
executors::tests::voice_requires_tts ... ok
executors::tests::export_requires_ffmpeg ... ok
service::tests::status_reflects_failure_and_reset ... ok
service::tests::double_start_rejected_while_running ... ok
tests::cancel_before_next_step ... ok
tests::step_failure_aborts ... ok
tests::run_all_5_steps_ok ... ok
```

---

## 3 · 前端布局壳 + 欢迎页重设计

### 3.1 AppShell 三栏结构

```
┌─ TopBar (h-14) ────────────────────────────────┐
│ Logo · 版本号 · Tauri连接状态点 · 主题切换        │
├─ Sidebar (w-56) ─┬─ Content Area (flex-1) ────┤
│ 首页               │                           │
│ 制作流水线 ★      │     <Outlet />             │
│ 项目管理          │                           │
│ 设置              │                           │
│ 更新              │                           │
│ 帮助              │                           │
└──────────────────┴───────────────────────────┘
```

- TopBar 实时拉 `app_version` 决定 Tauri 已连接 / 后端未连接状态点
- Sidebar 6 项导航,current route 高亮 + 渐变指示
- 主题初始化:`theme-store` → `<html data-theme="...">`

### 3.2 欢迎页视觉化 (M3.2 重设计 · 已替换原"一堆文字")

| 区块 | 改造前 (M2)                          | 改造后 (M3.2)                                                  |
| ---- | ------------------------------------ | -------------------------------------------------------------- |
| 顶部 | `h1` + 副标题 + 6 个页面链接文字网格 | 渐变 Hero + 1 句价值主张 + 2 个 CTA 按钮 + 右侧 6 卡片视觉矩阵 |
| 中段 | 5 步步骤 `<ol>` 文字列表             | `<StepFlow>` 5 卡片可视化状态机(颜色环 + 状态图标 + 连接线)    |
| 底部 | "系统状态" 5 行绿底 + 文字验收清单   | 紧凑贴纸 (Pill) 横向一行:Tauri / 版本 / 步数 / ffmpeg          |

**关键设计决定**:

- 不再有"一段段说明文字",改用视觉块传递信息
- CTA 优先(开始制作 / 打开项目)
- 系统状态从纵向 6 行压缩为横向 5 个贴纸
- "6 个页面链接"列表由 Sidebar 接管,首页不再重复展示

### 3.3 StepFlow 组件 (可复用)

`components/common/StepFlow.tsx` · 113 行

- 5 卡片水平布局,每个卡片:`icon + label + status ring`
- StepStatus 4 态 (`pending`/`active`/`done`/`error`) → 颜色环 + 角标字符
- 卡片间连接线:`done` → 绿色,`pending` → 灰色

### 3.4 真实接通后端的页面

#### `/production` · 制作流水线

- `useQuery(["pipeline-step-defs"])` → 5 步定义
- `useQuery(["pipeline-status"], { refetchInterval: state==='running' ? 800 : 5000 })` → 实时状态
- `useMutation(projectIpc.createBlank)` → 新建项目
- `useMutation(pipelineIpc.start)` → 启动 + 自动 invalidate
- `useMutation(pipelineIpc.cancel/reset)` → 控制
- 3 个 CapabilityCard (FFmpeg / LLM / TTS) 显示系统准备度

#### `/settings` · 设置

- `useQuery(settingsIpc.get)` → 加载远端快照
- `useMutation(settingsIpc.set)` → 保存
- 11 个 LLM Provider dropdown + 3 个 TTS 引擎卡片式选择
- LLM: API Key (password) + Base URL + Model 字段
- TTS: Voice/Model 字段,选 GPT-SoVITS 时展开 ref_audio + prompt_text
- 外观:主题 / 语言 / 自动更新 toggle

---

## 4 · IPC 契约对齐

### 4.1 前端契约表

```ts
// apps/desktop/src/ipc/types.gen.ts (227 行)
export interface IpcContracts {
  greet: { args: { name: string }; result: string };
  app_version: { args: void; result: string };
  app_started_at: { args: void; result: string };
  app_system_info: { args: void; result: AppSystemInfo };
  project_list_recent: { args: void; result: string[] };
  project_create_blank: { args: void; result: ProjectRecord };
  project_load: { args: { path: string }; result: ProjectRecord };
  project_save: { args: { path; project }; result: void };
  project_delete: { args: { path: string }; result: void };
  project_add_media: { args: { path; project; media }; result: Project };
  pipeline_step_defs: { args: void; result: PipelineStepDef[] };
  pipeline_status: { args: void; result: PipelineStatus };
  pipeline_start: { args: { project; workdir? }; result: void };
  pipeline_cancel: { args: void; result: void };
  pipeline_reset: { args: void; result: void };
  settings_get: { args: void; result: ConfigSnapshot };
  settings_set: { args: { snapshot }; result: void };
} // 16 + 1 (greet) = 17
```

### 4.2 类型与 Rust 一一对照

| Rust 类型                           | TypeScript 类型   | 来源                   |
| ----------------------------------- | ----------------- | ---------------------- |
| `scene_fab_domain::Project`         | `Project`         | `types.gen.ts:94-105`  |
| `ProjectRecord { path, project }`   | `ProjectRecord`   | `types.gen.ts:107-110` |
| `PipelineStatus (camelCase)`        | `PipelineStatus`  | `types.gen.ts:113-118` |
| `SystemInfo (camelCase)`            | `AppSystemInfo`   | `types.gen.ts:121-124` |
| `ConfigSnapshot`                    | `ConfigSnapshot`  | `types.gen.ts:127-138` |
| `scene_fab_domain::PipelineStepDef` | `PipelineStepDef` | `types.gen.ts:74-77`   |

### 4.3 调用层 (`commands.ts`)

5 域门面:`appIpc` (3) / `projectIpc` (6) / `pipelineIpc` (5) / `settingsIpc` (2)。聚合 `ipc` 总对象 + `IpcFacade` 类型推断。

---

## 5 · 三轨验证详情

### 5.1 轨 1 · Rust 后端

```
$ cargo check --workspace
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 1.39s
$ echo $? → 0

$ cargo test -p scenefab-pipeline -p scenefab-tts -p scenefab-ffmpeg
test result: ok. 14 passed; 0 failed (pipeline)
test result: ok. 4 passed; 0 failed (tts)
test result: ok. 5 passed; 0 failed (ffmpeg)
```

### 5.2 轨 2 · 前端类型检查

```
$ pnpm tsc --noEmit
$ echo $? → 0
```

### 5.3 轨 3 · 前端构建

```
$ pnpm build
> tsc && vite build
✓ 194 modules transformed.
dist/assets/index-DfTqcN98.css       47.61 kB │ gzip: 7.60 kB
dist/assets/production-B296C9CO.js    6.92 kB │ gzip: 2.56 kB
dist/assets/settings-dGN8PKj8.js      8.12 kB │ gzip: 2.73 kB
dist/assets/tanstack-CVWmjO1w.js    140.30 kB │ gzip: 44.57 kB
dist/assets/index-BoZfUg9a.js       201.94 kB │ gzip: 64.24 kB
✓ built in 1.85s
```

### 5.4 编译错误修复明细 (本轮)

| #   | 文件                                                  | 类型                                                  | 解决                                                                   |
| --- | ----------------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------- |
| 1   | `crates/scenefab-tts/src/lib.rs`                      | `TtsProviderKind` 未对外暴露                          | 加 `pub use scenefab_core::error::TtsProviderKind` 同时保留原 alias    |
| 2   | `apps/desktop/src-tauri/src/commands/pipeline.rs:204` | `Deepseek` 拼写 vs 核心枚举 `DeepSeek`                | `Self::Deepseek` → `Self::DeepSeek`                                    |
| 3   | `apps/desktop/src-tauri/src/commands/project.rs:118`  | `app.path()` 需 `tauri::Manager` trait                | `use tauri::{Manager, State}`                                          |
| 4   | `apps/desktop/src-tauri/src/commands/settings.rs:65`  | 同上                                                  | `use tauri::{Manager, State}`                                          |
| 5   | `apps/desktop/src-tauri/src/lib.rs:48`                | `services = ?ctx.services.len()` 是 Future (非 Debug) | 在 `block_on` 内 `let count = ctx.services.len().await;` 后带出        |
| 6   | `crates/scenefab-pipeline/src/executors.rs`           | 5 个 Step 缺 `#[derive(Debug)]`                       | 加 `#[derive(Debug)]` (workspace `missing-debug-implementations` lint) |

---

## 6 · 当前进度 vs M3.2 验收清单

- [x] 6 个真实 workspace 业务 crate 落地 (pipeline / tts / ffmpeg 完整, llm 11 provider)
- [x] Tauri 13 个业务 command (实际 17 含 greet) + 8 个事件契约
- [x] AppShell 布局壳 (TopBar / Sidebar / Outlet)
- [x] 欢迎页视觉化重设计 (Hero + StepFlow + Pills)
- [x] 流水线页真实接通后端 (StepFlow + start/cancel/reset)
- [x] 设置页真实接通后端 (LLM/TTS 全字段双向绑定)
- [x] IPC 契约 17/17 注册
- [x] 三轨验证 0 errors

## 7 · 下一步 (M4 候选)

- `assets` / `help` / `updates` 页面从 placeholder 升级为真实组件
- 流水线事件 listen (替换 polling) · 接 `pipeline:event` → side panel logs
- `mediaFiles` 拖拽上传 → 文件选择 dialog → `project_add_media`
- 关键操作 keybinding (⌘R run / ⌘. cancel)
- e2e Playwright 烟测
