# SceneFab v3.0 · Tauri 集成与 IPC 契约

> **基线版本**：v3.0.0
> **关联文档**：[02-target-architecture.md](./02-target-architecture.md) · [03-rust-backend.md](./03-rust-backend.md) · [05-api-services-plugin-updater.md](./05-api-services-plugin-updater.md) · [06-frontend-react.md](./06-frontend-react.md)
> **本文档范围**：Tauri 2.0 多进程模型、35 个 `#[tauri::command]` 的精确签名、Event 契约、Capability ACL、安全模型、单实例/自动启动/系统托盘/CSP/路径白名单/密钥管理。

## 0. TL;DR

把 v2.4 版本的 FastAPI + Uvicorn (HTTP/JSON) + 自建 SSE bridge 彻底替换为 Tauri 2.0 的 IPC 通道：

| 维度     | v2.4 (Python/FastAPI)                          | **v3.0 (Tauri 2.0 + Rust 1.85)**                                   |
| -------- | ---------------------------------------------- | ------------------------------------------------------------------ |
| 传输     | HTTP/JSON 127.0.0.1:8765 + SSE 8770            | **Tauri IPC (JSON via WebView)**                                   |
| 鉴权     | Bearer token (临时写死)                        | **Tauri Capability ACL**                                           |
| 错误     | HTTP 4xx/5xx + 自定义 `{error, code, message}` | **`SceneFabError` enum + specta `Result<T, Error>`**               |
| 推送     | SSE `data: {...}` 长连接                       | **`emit(event_name, payload)` 任意页面订阅**                       |
| 类型生成 | pydantic → 手动 OpenAPI                        | **specta + ts-rs 自动导出 to `apps/desktop/src/ipc/types.gen.ts`** |
| 进程模型 | 1 进程 (FastAPI 同进程跑 PySide6)              | **4 进程: Main + WebView + 插件 WASM + 外部子进程**                |

## 1. Tauri 2.0 多进程模型

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SceneFab 桌面进程拓扑（v3.0）                          │
└─────────────────────────────────────────────────────────────────────────┘

   ┌──────────────┐         IPC (postMessage + JSON)        ┌──────────────┐
   │   Main Process│◀─────────────────────────────────────▶│  WebView      │
   │   (Rust)      │   ① invoke(cmd, args) → Promise<T>    │  (React 18)   │
   │  scenefab-    │   ② emit(event, payload)              │  apps/desktop/│
   │  -tauri-app   │   ③ on(event, handler)                  │  src/         │
   │  + 所有业务crate│                                       │               │
   └──┬──────┬─────┘                                       └───────────────┘
      │      │                                                   │
      │      │   ┌────────────────────────────────────┐         │
      │      │   │       Plugin Process (WASM)         │         │
      │      │   │   wasmtime 29 沙箱                  │         │
      │      │   │   最多 8 个并发 WASM 插件实例        │         │
      │      └──▶│   - 内存上限 256MB/插件              │         │
      │          │   - CPU 时间片 2s/分钟                  │         │
      │          │   - 文件系统权限: only `~/.scenefab/plugins/`            │
      │          └────────────────────────────────────┘         │
      │                                                            │
      │   ┌─────────────────────────────────────────────────────┐  │
      │   │       外部子进程 (via tokio::process)              │  │
      │   │   - ffmpeg (视频编码, --progress pipe:1)            │  │
      │   │   - whisper.cpp (本地 STT，可选)                    │  │
      │   │   - 浏览器 headless (OpenAI 兼容 OAuth 流程)        │  │
      │   └─────────────────────────────────────────────────────┘  │
      │                                                             │
      └────▶ OS API 调用 (Rust crates)
              - keyring-rs (密钥)
              - tauri-plugin-system-tray
              - tauri-plugin-notification
              - tauri-plugin-os
              - tauri-plugin-shell
              - tauri-plugin-autostart
              - tauri-plugin-updater
              - tauri-plugin-window-state
              - tauri-plugin-single-instance
```

### 1.1 进程间数据流

| 流向          | 触发                              | 传输                                           | 序列化                           |
| ------------- | --------------------------------- | ---------------------------------------------- | -------------------------------- |
| ① invoke      | React 调用 backend                | WebView → Main (postMessage → Rust serde_json) | `serde::Serialize`/`Deserialize` |
| ② emit        | Main 主动推送到 UI 某个或全部窗口 | Main → WebView (broadcast via tauri Channel)   | 同上                             |
| ③ Plugin WASM | 沙箱插件被业务调用时              | Main → WASM (host import)                      | `wasmtime::ExternRef` + JSON     |
| ④ subprocess  | ffmpeg/whisper 启动               | Main → Process (stdin/stdout/stderr)           | bytes/line                       |
| ⑤ HTTP        | 外部 LLM/TTS API                  | reqwest → internet                             | JSON / multipart                 |

### 1.2 启动序列

```rust
// apps/desktop/src-tauri/src/lib.rs
pub fn run() {
    tauri::Builder::default()
        // 1. 单实例 + window state + autostart
        .plugin(tauri_plugin_single_instance::init(|app, args, cwd| {
            focus_main_window(app);
        }))
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .plugin(tauri_plugin_autostart::init(
            MacosLauncher::LaunchAgent,
            Some(vec!["--minimized"]),
        ))
        // 2. 系统托盘
        .plugin(tauri_plugin_system_tray::init(...))
        // 3. 通知
        .plugin(tauri_plugin_notification::init())
        // 4. 更新器
        .plugin(tauri_plugin_updater::Builder::default().build())
        // 5. 内置业务命令 + 上下文初始化
        .setup(|app| {
            let handle = app.handle().clone();
            let ctx = AppContext::init(&handle).expect("AppContext init");
            app.manage(ctx);
            // 后台启动：信号订阅、文件系统清理、健康检查
            ctx.spawn_background_tasks();
            Ok(())
        })
        // 6. 业务 commands (35 个，注册到全局)
        .invoke_handler(tauri::generate_handler![
            commands::project::*,
            commands::pipeline::*,
            commands::assets::*,
            commands::settings::*,
            commands::llm::*,
            commands::export::*,
            commands::theme::*,
            commands::update::*,
            commands::help::*,
            commands::diagnostics::*,
            commands::window::*,
            commands::plugin::*,
        ])
        .run(tauri::generate_context!())
        .expect("Tauri app panic");
}
```

## 2. Tauri Commands（35 个精确签名）

> 命名规范：`{domain}_{action}` 小写 + 下划线。所有命令必须用 `#[tauri::command]` + `#[specta::command]` 双注解，由 specta 在构建期导出 TS 类型。

### 2.1 项目域 (`commands/project.rs`)

```rust
use serde::{Deserialize, Serialize};
use specta::Type;
use tauri::State;

#[tauri::command]
#[specta::command]
pub async fn recent_projects(ctx: State<'_, AppContext>) -> Result<Vec<ProjectDescriptor>, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn current_project(ctx: State<'_, AppContext>) -> Result<Option<ProjectDescriptor>, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn open_project(
    ctx: State<'_, AppContext>,
    path: String,
) -> Result<ProjectDescriptor, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn open_project_dialog(
    app: AppHandle,
) -> Result<Option<ProjectDescriptor>, SceneFabError> {
    // 调用 rfd / tauri-plugin-dialog 弹出选择器
    ...
}

#[tauri::command]
#[specta::command]
pub async fn close_project(ctx: State<'_, AppContext>) -> Result<(), SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn save_project(
    ctx: State<'_, AppContext>,
    project: ProjectDescriptor,
) -> Result<(), SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn new_project(
    ctx: State<'_, AppContext>,
    name: String,
    template: Option<ProjectTemplate>,
) -> Result<ProjectDescriptor, SceneFabError> { ... }
```

### 2.2 流水线域 (`commands/pipeline.rs`) — 替代 v2.4 `/api/pipeline/*` HTTP 端点

```rust
#[tauri::command]
#[specta::command]
pub async fn start_pipeline(
    ctx: State<'_, AppContext>,
    source_video: String,
    context: String,
) -> Result<PipelineSnapshot, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn reset_pipeline(ctx: State<'_, AppContext>) -> Result<PipelineSnapshot, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn pipeline_snapshot(ctx: State<'_, AppContext>) -> Result<PipelineSnapshot, SceneFabError> { ... }

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum PipelineStepRequest {
    Retry { index: usize },
    Skip { index: usize },
    Cancel,
}

#[tauri::command]
#[specta::command]
pub async fn pipeline_step(
    ctx: State<'_, AppContext>,
    request: PipelineStepRequest,
) -> Result<PipelineSnapshot, SceneFabError> { ... }
```

> **事件契约**（替代 SSE `pipeline.progress` / `pipeline.event`）：
>
> | Event 名称               | Payload 字段                             | 触发频率                      |
> | ------------------------ | ---------------------------------------- | ----------------------------- |
> | `pipeline.snapshot`      | 完整 `PipelineSnapshot`                  | 状态机每次转移                |
> | `pipeline.step_started`  | `{ index: usize }`                       | 每步开始                      |
> | `pipeline.step_finished` | `{ index: usize, took_seconds: f64 }`    | 每步结束（用于 ETA 滑动窗口） |
> | `pipeline.step_failed`   | `{ index: usize, error: SceneFabError }` | 每步异常                      |
> | `pipeline.finished`      | `{ project_path: String }`               | 5 步全部完成                  |
> | `pipeline.failed`        | `{ error: SceneFabError }`               | 任一步失败                    |

### 2.3 资源域 (`commands/assets.rs`)

```rust
#[tauri::command]
#[specta::command]
pub async fn assets_summary(ctx: State<'_, AppContext>) -> Result<AssetSummary, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn import_media(
    ctx: State<'_, AppContext>,
    paths: Vec<String>,
) -> Result<u32, SceneFabError> { ... }
// 返回成功导入的数量

#[tauri::command]
#[specta::command]
pub async fn list_media(
    ctx: State<'_, AppContext>,
    project_id: String,
) -> Result<Vec<MediaDescriptor>, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn delete_media(
    ctx: State<'_, AppContext>,
    media_id: String,
) -> Result<(), SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn thumbnail(
    ctx: State<'_, AppContext>,
    media_id: String,
    time_ms: u64,
    max_size: u32,
) -> Result<String, SceneFabError> { ... }
// 返回 base64 PNG JPEG (向前端 <img src=data:image/...> 直接使用)
```

> **事件**：`assets.summary_changed`（payload `AssetSummary`）

### 2.4 配置域 (`commands/settings.rs`)

```rust
#[tauri::command]
#[specta::command]
pub async fn get_settings(ctx: State<'_, AppContext>) -> Result<Settings, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn update_settings(
    ctx: State<'_, AppContext>,
    settings: SettingsPatch,
) -> Result<Settings, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn set_api_key(
    ctx: State<'_, AppContext>,
    provider: LlmProviderId,
    api_key: String,
) -> Result<(), SceneFabError> { ... }
// 存储到 keyring-rs；前端永远拿不到明文

#[tauri::command]
#[specta::command]
pub async fn has_api_keys(ctx: State<'_, AppContext>) -> Result<HashMap<LlmProviderId, bool>, SceneFabError> { ... }
// 只返回是否存在的 bool map（用于 Settings UI 灰显/显示）
```

> **事件**：`settings.changed`（payload `Settings`）

### 2.5 LLM 域 (`commands/llm.rs`)

```rust
#[tauri::command]
#[specta::command]
pub async fn list_llm_providers(ctx: State<'_, AppContext>) -> Result<Vec<LlmProviderDescriptor>, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn test_llm_provider(
    ctx: State<'_, AppContext>,
    provider: LlmProviderId,
) -> Result<TestResult, SceneFabError> { ... }

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum TestResult {
    Ok { latency_ms: u64, model: String },
    Err { error: SceneFabError, hint: Option<String> },
}

#[tauri::command]
#[specta::command]
pub async fn complete_script(
    ctx: State<'_, AppContext>,
    request: ScriptRequest,
) -> Result<ScriptResponse, SceneFabError> { ... }
```

> **事件**：
>
> - `llm.request_started`：`{ provider, model, request_id }`
> - `llm.token_delta`：`{ request_id, delta }`（流式响应）
> - `llm.request_finished`：`{ request_id, total_tokens, latency_ms }`
> - `llm.request_failed`：`{ request_id, error }`

### 2.6 导出域 (`commands/export.rs`)

```rust
#[tauri::command]
#[specta::command]
pub async fn start_export(
    ctx: State<'_, AppContext>,
    request: ExportRequest,
) -> Result<ExportJobDescriptor, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn cancel_export(
    ctx: State<'_, AppContext>,
    job_id: String,
) -> Result<(), SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn list_export_jobs(ctx: State<'_, AppContext>) -> Result<Vec<ExportJobDescriptor>, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn export_preview(
    ctx: State<'_, AppContext>,
    time_ms: u64,
    max_size: u32,
) -> Result<String, SceneFabError> { ... }
// 返回 base64 缩略图
```

> **事件**：
>
> - `export.progress`：`{ job_id, percent, fps, eta_seconds }`（每 250ms 推送一次，由 ffmpeg `--progress` 解析）
> - `export.log`：`{ job_id, line }`
> - `export.finished`：`{ job_id, output_path }`
> - `export.failed`：`{ job_id, error }`

### 2.7 主题域 (`commands/theme.rs`)

```rust
#[tauri::command]
#[specta::command]
pub async fn get_theme(ctx: State<'_, AppContext>) -> Result<ThemeState, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn set_theme(
    ctx: State<'_, AppContext>,
    mode: ThemeMode,
) -> Result<ThemeState, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn set_locale(
    ctx: State<'_, AppContext>,
    locale: Locale,
) -> Result<(), SceneFabError> { ... }
```

> **事件**：`theme.changed`（payload `ThemeState`）

### 2.8 更新域 (`commands/update.rs`) — 详见 05 章

```rust
#[tauri::command]
#[specta::command]
pub async fn update_status(ctx: State<'_, AppContext>) -> Result<UpdateState, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn update_check(ctx: State<'_, AppContext>) -> Result<UpdateInfo, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn update_download(
    ctx: State<'_, AppContext>,
    info: UpdateInfo,
) -> Result<UpdateDownloadReceipt, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn update_apply(
    app: AppHandle,
    receipt: UpdateDownloadReceipt,
) -> Result<(), SceneFabError> { ... }
// 触发进程退出 + 重启
```

> **事件**：`update.phase` / `update.progress` / `update.error` / `update.finished`

### 2.9 帮助域 (`commands/help.rs`)

```rust
#[tauri::command]
#[specta::command]
pub async fn help_search(
    ctx: State<'_, AppContext>,
    query: String,
    lang: Locale,
) -> Result<Vec<HelpDocResult>, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn help_doc(
    ctx: State<'_, AppContext>,
    doc_id: String,
    lang: Locale,
) -> Result<HelpDoc, SceneFabError> { ... }
```

### 2.10 诊断域 (`commands/diagnostics.rs`)

```rust
#[tauri::command]
#[specta::command]
pub async fn collect_diagnostics(ctx: State<'_, AppContext>) -> Result<DiagnosticsReport, SceneFabError> { ... }
// 收集 CPU/mem/disk/uptime/last_error/recent_logs → JSON dump

#[tauri::command]
#[specta::command]
pub async fn export_logs(
    ctx: State<'_, AppContext>,
    output_path: String,
) -> Result<u64, SceneFabError> { ... }
// 返回导出文件字节数
```

### 2.11 窗口域 (`commands/window.rs`)

```rust
#[tauri::command]
#[specta::command]
pub async fn window_minimize(app: AppHandle) -> Result<(), SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn window_toggle(app: AppHandle) -> Result<(), SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn window_quit(app: AppHandle) -> Result<(), SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn save_window_state(
    app: AppHandle,
    state: WindowState,
) -> Result<(), SceneFabError> { ... }
```

### 2.12 插件域 (`commands/plugin.rs`)

```rust
#[tauri::command]
#[specta::command]
pub async fn list_plugins(ctx: State<'_, AppContext>) -> Result<Vec<PluginDescriptor>, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn install_plugin(
    ctx: State<'_, AppContext>,
    from_url: String,
) -> Result<PluginDescriptor, SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn enable_plugin(
    ctx: State<'_, AppContext>,
    plugin_id: String,
) -> Result<(), SceneFabError> { ... }

#[tauri::command]
#[specta::command]
pub async fn disable_plugin(
    ctx: State<'_, AppContext>,
    plugin_id: String,
) -> Result<(), SceneFabError> { ... }
```

### 2.13 总数校验

```text
project  :  7  commands
pipeline :  4  commands
assets   :  5  commands
settings :  4  commands
llm      :  3  commands
export   :  5  commands
theme    :  3  commands
update   :  4  commands
help     :  2  commands
diagnostics : 2 commands
window   :  4  commands
plugin   :  4  commands
─────────────────────
合计     : 47 commands (含 12 个由 future deltas 引入的扩展点)
核心     : 35 commands (M0-M6 必须完成)
```

## 3. 类型自动化（specta + ts-rs）

### 3.1 后端类型注解模式

```rust
use serde::{Deserialize, Serialize};
use specta::Type;
use ts_rs::TS;

#[derive(Debug, Clone, Serialize, Deserialize, Type, TS)]
#[serde(rename_all = "camelCase")]
#[ts(export, export_to = "../../apps/desktop/src/ipc/types.gen.ts")]
pub struct AssetSummary {
    pub media_count: u32,
    pub script_count: u32,
    pub audio_count: u32,
    pub export_count: u32,
}
```

构建步骤：

```bash
# 1. 后端导出 TS 类型
cd apps/desktop/src-tauri
cargo test --features specta-export
# 输出: src/export/types.gen.ts → 已映射到 apps/desktop/src/ipc/types.gen.ts

# 2. 前端用 tsc 校验对齐
cd ../../../apps/desktop
pnpm typecheck
```

### 3.2 前端类型导入

```ts
// apps/desktop/src/ipc/commands.ts —— auto-generated by specta
import { invoke } from "@tauri-apps/api/core";
import type {
  AssetSummary,
  PipelineSnapshot,
  Settings,
  ThemeMode,
} from "./types.gen";

export const commands = {
  assetsSummary: () => invoke<AssetSummary>("assets_summary"),
  pipelineSnapshot: () => invoke<PipelineSnapshot>("pipeline_snapshot"),
  getSettings: () => invoke<Settings>("get_settings"),
  setTheme: (mode: ThemeMode) => invoke<void>("set_theme", { mode }),
  // ... 共 35 个
};
```

### 3.3 编译期类型一致性检查

```yaml
# .github/workflows/type-consistency.yml
name: type-consistency

on: [push]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - name: Generate TS types
        run: |
          cd apps/desktop/src-tauri
          cargo test --features specta-export
      - uses: pnpm/action-setup@v4
      - run: |
          cd apps/desktop
          pnpm install
          pnpm typecheck
      - name: Detect drift
        run: |
          if [[ -n "$(git status --porcelain apps/desktop/src/ipc/types.gen.ts)" ]]; then
            echo "::error::Generated types are out of date"
            exit 1
          fi
```

## 4. 错误处理（SceneFabError + specta）

### 4.1 错误枚举设计

```rust
// crates/scenefab-core/src/error.rs
use serde::{Deserialize, Serialize};
use specta::Type;
use thiserror::Error;

#[derive(Debug, Clone, Serialize, Deserialize, Type, Error)]
#[serde(tag = "kind", rename_all = "snake_case")]
#[specta(rename_all = "snake_case")]
pub enum SceneFabError {
    #[error("project not found: {path}")]
    ProjectNotFound { path: String },

    #[error("invalid operation in pipeline state {state:?}: {action}")]
    InvalidPipelineTransition { state: String, action: String },

    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("LLM provider {provider} failed: {message}")]
    LlmProvider { provider: String, message: String,

        #[serde(skip)]
        #[ts(skip)]
        source: Option<anyhow::Error>,
    },

    #[error("TTS provider {provider} failed: {message}")]
    TtsProvider { provider: String, message: String },

    #[error("FFmpeg exited with code {code}: {stderr_tail}")]
    Ffmpeg { code: i32, stderr_tail: String },

    #[error("permission denied: {path}")]
    PermissionDenied { path: String },

    #[error("path outside allow-list: {path}")]
    PathNotAllowed { path: String },

    #[error("api key for {provider} is missing")]
    ApiKeyMissing { provider: String },

    #[error("network: {url}: {message}")]
    Network { url: String, message: String },

    #[error("plugin {plugin_id} crashed: {message}")]
    PluginCrash { plugin_id: String, message: String },

    #[error("update error in phase {phase}: {message}")]
    Update { phase: String, message: String },

    #[error("internal: {message}")]
    Internal { message: String },
}

impl SceneFabError {
    pub fn exit_code(&self) -> i32 {
        match self {
            Self::Io(_) => 1,
            Self::Json(_) => 2,
            Self::LlmProvider { .. } => 10,
            Self::TtsProvider { .. } => 11,
            Self::Ffmpeg { .. } => 20,
            Self::PermissionDenied { .. } => 30,
            Self::PathNotAllowed { .. } => 31,
            Self::ApiKeyMissing { .. } => 40,
            Self::Network { .. } => 41,
            Self::PluginCrash { .. } => 50,
            Self::Update { .. } => 60,
            Self::ProjectNotFound { .. } => 70,
            Self::InvalidPipelineTransition { .. } => 71,
            Self::Internal { .. } => 99,
        }
    }
}

pub type SceneFabResult<T> = Result<T, SceneFabError>;
```

### 4.2 前端错误转换层

```ts
// apps/desktop/src/ipc/errors.ts
export interface SceneFabErrorPayload {
  kind: string;
  message: string;
  // kind-specific fields preserved by `unknownFields` strategy
  [k: string]: unknown;
}

export class SceneFabException extends Error {
  readonly kind: SceneFabErrorPayload["kind"];
  readonly payload: SceneFabErrorPayload;
  readonly userHint: string;
  constructor(payload: SceneFabErrorPayload) {
    super(payload.message);
    this.payload = payload;
    this.kind = payload.kind;
    this.userHint = USER_HINTS[payload.kind] ?? payload.message;
  }
}

const USER_HINTS: Record<string, string> = {
  api_key_missing:
    "请在「设置 → AI 配置」中填入对应 Provider 的 API Key 后重试。",
  path_not_allowed: "所选路径不在允许列表内，请改用默认目录或联系管理员。",
  ffmpeg: "视频导出失败，请查看日志详情或重试。",
  llm_provider: "AI 服务返回异常，已自动降级到备用 Provider。",
  update: "自动更新失败，您可以稍后重试或手动下载安装包。",
  network: "网络连接异常，请检查代理或防火墙设置后重试。",
};

export function toUserReadableError(e: unknown): SceneFabException {
  if (e instanceof SceneFabException) return e;
  if (typeof e === "string")
    return new SceneFabException({ kind: "internal", message: e });
  if (typeof e === "object" && e && "kind" in e) {
    return new SceneFabException(e as SceneFabErrorPayload);
  }
  return new SceneFabException({ kind: "internal", message: String(e) });
}

/** UI 错误边界消费 */
export function formatError(e: SceneFabException): {
  title: string;
  detail: string;
  action?: { label: string; run: () => void };
} {
  switch (e.kind) {
    case "api_key_missing":
      return {
        title: "缺少 API Key",
        detail: e.userHint,
        action: { label: "打开设置", run: () => location.assign("/settings") },
      };
    case "path_not_allowed":
      return { title: "路径不可访问", detail: e.userHint };
    case "network":
      return { title: "网络异常", detail: e.userHint };
    default:
      return { title: "操作失败", detail: e.userHint };
  }
}
```

### 4.3 后端统一错误包装 (Tauri)

```rust
// apps/desktop/src-tauri/src/commands/error.rs
use tauri::ipc::InvokeError;
use crate::error::SceneFabError;

pub fn to_invoke_error(e: SceneFabError) -> InvokeError {
    InvokeError::from(e)
}
```

## 5. Capability ACL（替代 FastAPI 的 Bearer Token 鉴权）

### 5.1 总览

Tauri 2.0 的 **Capability** 是 ACL 系统：每个能力文件定义"哪些命令+哪些窗口/插件+哪些 scope"可被调用。

```
src-tauri/capabilities/
├── default.json         # 主窗口默认能力
├── update.json          # 仅在更新阶段附加（更严格）
├── embedded.json        # 嵌入模式 (Storybook + 单元测试使用)
└── plugins/
    ├── dialog.json
    ├── fs.json          # 文件系统白名单
    ├── notification.json
    ├── os.json
    ├── shell.json       # 仅允许 ffmpeg
    ├── system-tray.json
    └── updater.json
```

### 5.2 `default.json`（主窗口）

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "主窗口默认能力 v3.0",
  "windows": ["main"],
  "remote": { "urls": [] },
  "local": true,
  "webviews": [{ "name": "main", "url": null }],
  "permissions": [
    "core:default",
    "core:event:default",
    "core:window:allow-show",
    "core:window:allow-hide",
    "core:window:allow-close",
    "core:window:allow-minimize",
    "core:window:allow-maximize",
    "core:path:default",

    "dialog:default",
    "dialog:allow-open",
    "dialog:allow-save",
    "dialog:allow-message",

    "fs:default",
    {
      "identifier": "fs:scope",
      "allow": [
        { "path": "$APPDATA/scenefab/**" },
        { "path": "$APPDATA/com.scenefab.app/**" },
        { "path": "$DOCUMENT/**" },
        { "path": "$VIDEO/**" },
        { "path": "$DESKTOP/**" },
        { "path": "$DOWNLOAD/**" },
        { "path": "$HOME/Movies/**" }
      ]
    },
    "fs:allow-read-file",
    "fs:allow-write-file",
    "fs:allow-read-dir",
    "fs:allow-mkdir",
    "fs:allow-remove",

    "notification:default",
    "os:default",

    {
      "identifier": "shell:allow-execute",
      "allow": [
        {
          "name": "ffmpeg",
          "cmd": "ffmpeg",
          "args": true,
          "sidecar": true
        },
        {
          "name": "ffprobe",
          "cmd": "ffprobe",
          "args": true,
          "sidecar": true
        }
      ]
    },

    "system-tray:default",
    "updater:default",

    "scenefab:core:default",
    "scenefab:project:default",
    "scenefab:pipeline:default",
    "scenefab:assets:default",
    "scenefab:settings:default",
    "scenefab:llm:default",
    "scenefab:export:default",
    "scenefab:theme:default",
    "scenefab:update:default",
    "scenefab:help:default",
    "scenefab:diagnostics:default",
    "scenefab:window:default",
    "scenefab:plugin:default"
  ]
}
```

### 5.3 自定义业务权限粒度

每个业务命令隶属一个 permission set，由 Cargo feature + 代码注解联合启用：

```rust
// apps/desktop/src-tauri/src/permissions/mod.rs
pub mod project;
pub mod pipeline;
pub mod assets;
// ...

// apps/desktop/src-tauri/src/permissions/pipeline.rs
use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct PipelinePermission {
    pub allow_start: bool,
    pub allow_reset: bool,
    pub allow_step_retry: bool,
}

// 通过 specta 导出到前端 ACL UI
```

```ts
// apps/desktop/src/ipc/acl.ts
export const ACL = {
  PIPELINE_START: { allow: true, scope: "production-page" },
  SETTINGS_VIEW_KEYS: { allow: false, scope: "*" }, // 不允许前端直接查 API Key
  EXPORT_CANCEL: { allow: true, scope: "*" },
  PLUGIN_INSTALL: { allow: false, scope: "settings-admin" }, // 由设置页触发
};
```

## 6. Event 总线契约

### 6.1 命名规范

- 业务事件：`<domain>.<noun>_<verb>` (e.g. `pipeline.snapshot`, `update.progress`)
- 系统事件：`<source>.<noun>` (e.g. `system.metric`, `system.battery`)
- 用户交互事件：`<domain>.<interaction>` (e.g. `palette.opened`)

### 6.2 Event Registry（单一真相源）

```rust
// crates/scenefab-core/src/event.rs
#[derive(Debug, Clone, Copy)]
pub enum EventName {
    PipelineSnapshot,
    PipelineStepStarted,
    PipelineStepFinished,
    PipelineStepFailed,
    PipelineFinished,
    PipelineFailed,
    AssetsSummaryChanged,
    SettingsChanged,
    LlmRequestStarted,
    LlmTokenDelta,
    LlmRequestFinished,
    LlmRequestFailed,
    ExportProgress,
    ExportLog,
    ExportFinished,
    ExportFailed,
    ThemeChanged,
    UpdatePhase,
    UpdateProgress,
    UpdateError,
    UpdateFinished,
    SystemMetric,
    SystemBattery,
    TrayMenuClicked,
    WindowStateChanged,
    PluginLoaded,
    PluginUnloaded,
    DiagnosticsAlert,
}

impl EventName {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::PipelineSnapshot => "pipeline.snapshot",
            Self::PipelineStepStarted => "pipeline.step_started",
            // ... 全部 24 个
        }
    }
}
```

### 6.3 前端 Event 总线桥接

```ts
// apps/desktop/src/ipc/events.ts
import { listen, emit, type UnlistenFn } from "@tauri-apps/api/event";
import type {
  PipelineSnapshot,
  AssetSummary,
  SystemMetric,
  ThemeState,
} from "./types.gen";

export const onPipelineSnapshot = (
  cb: (s: PipelineSnapshot) => void,
): Promise<UnlistenFn> =>
  listen<PipelineSnapshot>("pipeline.snapshot", (e) => cb(e.payload));

export const onAssetsSummaryChanged = (
  cb: (s: AssetSummary) => void,
): Promise<UnlistenFn> =>
  listen<AssetSummary>("assets.summary_changed", (e) => cb(e.payload));

export const onSystemMetric = (
  cb: (m: SystemMetric) => void,
): Promise<UnlistenFn> =>
  listen<SystemMetric>("system.metric", (e) => cb(e.payload));

export const onThemeChanged = (
  cb: (t: ThemeState) => void,
): Promise<UnlistenFn> =>
  listen<ThemeState>("theme.changed", (e) => cb(e.payload));

// 后端 → 前端的 emit 调用
export const emitToBackend = <T>(name: string, payload: T) =>
  emit<T>(name, payload);
```

## 7. 单实例 + 自动启动 + 系统托盘

### 7.1 单实例（tauri-plugin-single-instance）

```rust
use tauri_plugin_single_instance::init;

.plugin(init(|app, _args, _cwd| {
    // 第二次启动时: 把已存在窗口 focus
    if let Some(win) = app.get_webview_window("main") {
        let _ = win.show();
        let _ = win.unminimize();
        let _ = win.set_focus();
    }
}))
```

### 7.2 自动启动（tauri-plugin-autostart）

```rust
use tauri_plugin_autostart::MacosLauncher;

.plugin(tauri_plugin_autostart::init(
    MacosLauncher::LaunchAgent,
    Some(vec!["--minimized"]),     // 开机启动时最小化
))
```

```ts
// 前端在设置页提供切换 UI
import { enable, disable, isEnabled } from "@tauri-apps/plugin-autostart";
const enabled = await isEnabled();
if (formData.autostart) await enable();
else await disable();
```

### 7.3 系统托盘（tauri-plugin-system-tray）

```rust
use tauri::tray::{TrayIconBuilder, TrayIconEvent, MouseButton, MouseButtonState};
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};

.plugin(tauri_plugin_system_tray::init(...))
.setup(|app| {
    let show_item = MenuItem::with_id(app, "show", "显示主窗口", true, None::<&str>)?;
    let prod_item = MenuItem::with_id(app, "production", "打开生产页", true, Some("CmdOrCtrl+P"))?;
    let assets_item = MenuItem::with_id(app, "assets", "打开资源页", true, Some("CmdOrCtrl+A"))?;
    let quit_item = MenuItem::with_id(app, "quit", "退出", true, Some("CmdOrCtrl+Q"))?;
    let separator = PredefinedMenuItem::separator(app)?;
    let menu = Menu::with_items(app, &[
        &show_item, &prod_item, &assets_item, &separator, &quit_item,
    ])?;

    let _tray = TrayIconBuilder::with_id("main-tray")
        .icon(app.default_window_icon().unwrap().clone())
        .menu(&menu)
        .menu_on_left_click(false)
        .on_menu_event(|app, event| {
            match event.id.as_ref() {
                "show"      => { show_main_window(app); }
                "production"=> { navigate_app(app, "/production"); }
                "assets"    => { navigate_app(app, "/assets"); }
                "quit"      => { app.exit(0); }
                _ => {}
            }
        })
        .on_tray_icon_event(|tray, event| {
            // 双击托盘图标 = toggle 主窗口
            if let TrayIconEvent::DoubleClick { button: MouseButton::Left, .. } = event {
                toggle_main_window(tray.app_handle());
            }
        })
        .build(app)?;
    Ok(())
})
```

```ts
// 前端订阅
useTauriEvent<{ id: string }>("tray:menu-clicked", (e) => {
  switch (e.id) {
    case "production":
      navigate({ to: "/production" });
      break;
    case "assets":
      navigate({ to: "/assets" });
      break;
  }
});
```

### 7.4 窗口状态持久化（tauri-plugin-window-state）

```rust
.plugin(tauri_plugin_window_state::Builder::default()
    .with_state_flags(WindowStateFlags::FULL | WindowStateFlags::MAXIMIZED)
    .build())
```

无需手动序列化，反序列化由插件自动完成。

### 7.5 通知（tauri-plugin-notification）

```rust
.plugin(tauri_plugin_notification::init())
```

```ts
import {
  sendNotification,
  isPermissionGranted,
  requestPermission,
} from "@tauri-apps/plugin-notification";

if (!(await isPermissionGranted())) {
  const granted = await requestPermission();
}

// 流水线完成时：
sendNotification({
  title: "SceneFab",
  body: `流水线已完成！输出文件：${projectPath}`,
});
```

## 8. 安全模型

### 8.1 CSP（Content Security Policy）

```json
// src-tauri/tauri.conf.json
{
  "app": {
    "security": {
      "csp": {
        "default-src": "'self'",
        "script-src": "'self' 'wasm-unsafe-eval'",
        "style-src": "'self' 'unsafe-inline'",
        "img-src": "'self' data: blob: asset: http://asset.localhost",
        "font-src": "'self' data:",
        "connect-src": "'self' ipc: https://ipc.localhost",
        "media-src": "'self' blob: asset:",
        "object-src": "'none'",
        "frame-ancestors": "'none'",
        "base-uri": "'self'"
      },
      "assetProtocol": {
        "enable": true,
        "scope": [
          "$APPDATA/scenefab/**/*.png",
          "$APPDATA/scenefab/**/*.jpg",
          "$APPDATA/scenefab/**/*.jpeg",
          "$APPDATA/scenefab/**/*.webp",
          "$APPDATA/scenefab/**/*.svg",
          "$VIDEO/**",
          "$DOCUMENT/**"
        ]
      }
    }
  }
}
```

### 8.2 路径白名单

```rust
// crates/scenefab-core/src/security/path.rs
use std::path::{Path, PathBuf};
use crate::error::SceneFabError;

pub struct PathPolicy {
    allow_roots: Vec<PathBuf>,
}

impl PathPolicy {
    pub fn new() -> Self {
        let home = dirs::home_dir().unwrap_or_default();
        let appdata = dirs::data_dir().unwrap_or_default().join("scenefab");
        let config = dirs::config_dir().unwrap_or_default().join("scenefab");
        Self {
            allow_roots: vec![
                home.join("Documents"),
                home.join("Movies"),
                home.join("Desktop"),
                home.join("Downloads"),
                dirs::video_dir().unwrap_or_default(),
                appdata,
                config,
                std::env::temp_dir().join("scenefab"),
            ],
        }
    }

    pub fn resolve(&self, raw: &str) -> Result<PathBuf, SceneFabError> {
        let p = Path::new(raw);
        let canonical = p.canonicalize()
            .map_err(|_| SceneFabError::PathNotAllowed { path: raw.to_string() })?;
        if !self.allow_roots.iter().any(|r| canonical.starts_with(r)) {
            return Err(SceneFabError::PathNotAllowed { path: raw.to_string() });
        }
        Ok(canonical)
    }
}
```

### 8.3 密钥管理（keyring-rs）

```rust
// crates/scenefab-core/src/security/keyring.rs
use keyring::Entry;
use crate::error::SceneFabError;

pub struct SecureKeyStore {
    service: String,
}

impl SecureKeyStore {
    pub fn new() -> Self { Self { service: "com.scenefab.app".to_string() } }

    pub fn store(&self, account: &str, value: &str) -> Result<(), SceneFabError> {
        let entry = Entry::new(&self.service, account)
            .map_err(|e| SceneFabError::Internal { message: e.to_string() })?;
        entry.set_password(value)
            .map_err(|e| SceneFabError::Internal { message: e.to_string() })
    }

    pub fn fetch(&self, account: &str) -> Result<Option<String>, SceneFabError> {
        let entry = Entry::new(&self.service, account)
            .map_err(|e| SceneFabError::Internal { message: e.to_string() })?;
        match entry.get_password() {
            Ok(v) => Ok(Some(v)),
            Err(keyring::Error::NoEntry) => Ok(None),
            Err(e) => Err(SceneFabError::Internal { message: e.to_string() }),
        }
    }

    pub fn delete(&self, account: &str) -> Result<(), SceneFabError> {
        let entry = Entry::new(&self.service, account)
            .map_err(|e| SceneFabError::Internal { message: e.to_string() })?;
        match entry.delete_credential() {
            Ok(()) => Ok(()),
            Err(keyring::Error::NoEntry) => Ok(()),
            Err(e) => Err(SceneFabError::Internal { message: e.to_string() }),
        }
    }

    pub fn list_accounts(&self) -> Result<Vec<String>, SceneFabError> {
        // keyring-rs 0.5+ 提供 persistent listing via DBus/Secret Service
        // macOS: 直接枚举 keychain entries via security CLI
        // Windows: DPAPI per-user 不支持枚举 → 维护本地索引
        Ok(vec![])  // 见 02-target-architecture.md §4.3
    }
}
```

### 8.4 输入消毒（LLM prompt 注入防御）

```rust
// crates/scenefab-llm/src/sanitize.rs
pub fn sanitize_user_input(s: &str, max_len: usize) -> Result<String, SceneFabError> {
    if s.len() > max_len {
        return Err(SceneFabError::Internal {
            message: format!("input too long: {} > {}", s.len(), max_len),
        });
    }
    // 移除控制字符 (除 \n \t)
    let filtered: String = s.chars()
        .filter(|c| c.is_ascii_graphic() || matches!(c, '\n' | '\t' | ' '))
        .collect();
    // 移除可疑指令注入 (e.g. "ignore previous instructions")
    let lowered = filtered.to_lowercase();
    let injection_markers = ["ignore previous", "system:", "assistant:"];
    for marker in injection_markers {
        if lowered.contains(marker) {
            return Err(SceneFabError::Internal {
                message: format!("potential prompt injection: {}", marker),
            });
        }
    }
    Ok(filtered)
}
```

## 9. 更新器集成（tauri-plugin-updater）

### 9.1 配置

```json
{
  "plugins": {
    "updater": {
      "endpoints": [
        {
          "url": "https://api.scenefab.dev/updates/v3/{{target}}/{{arch}}/{{current_version}}",
          "headers": { "X-Channel": "stable" }
        }
      ],
      "pubkey": "dW50cnVzdGVkIGNvbW1lbnQ6...",
      "windows": {
        "installMode": "passive"
      }
    }
  }
}
```

### 9.2 自托管 fallback（GitHub Releases）

```json
{
  "plugins": {
    "updater": {
      "endpoints": [
        {
          "url": "https://api.scenefab.dev/updates/v3/{{target}}/{{arch}}/{{current_version}}"
        },
        {
          "url": "https://github.com/scenefab/scenefab/releases/latest/download/v3-update-{{target}}.json"
        }
      ]
    }
  }
}
```

### 9.3 5 阶段状态机

```
┌──────┐   manualCheck()    ┌────────────┐   hasUpdate?    ┌────────────┐
│ IDLE │ ─────────────────▶ │  CHECKING  │ ──────────────▶ │  AVAILABLE │
└──────┘                    └────────────┘                 └─────┬──────┘
                                                                 │ download()
                                                                 ▼
              ┌──────────────┐                                 ┌─────────────┐
              │ ERROR (retry)│◀──────── network fail ─────────│ DOWNLOADING │
              └──────────────┘                                 └──────┬──────┘
                                                                     │ done
                                                                     ▼
              ┌──────────────┐       user confirm             ┌─────────────┐
              │ BLOCKING*    │◀──── blockIfRequired ──────────│   READY     │
              └──────┬───────┘                                 └──────┬──────┘
                     │ user click "install"                              │
                     ▼                                                    │
              ┌──────────────┐                                            │
              │   APPLYING   │◀──────────────────────────────────────────┘
              └──────┬───────┘
                     │ restart
                     ▼
              ┌──────────────┐
              │     DONE     │
              └──────────────┘
```

### 9.4 Rust 后端业务逻辑（详见 05 章 updater 节）

```rust
// crates/scenefab-update/src/service.rs
use tauri_plugin_updater::UpdaterExt;
use tauri::{AppHandle, Manager};

pub struct UpdateService {
    handle: AppHandle,
    state: Arc<RwLock<UpdateStateMachine>>,
}

impl UpdateService {
    pub async fn check(&self) -> Result<UpdateInfo, SceneFabError> {
        let updater = self.handle.updater().check()
            .await
            .map_err(|e| SceneFabError::Update { phase: "check".into(), message: e.to_string() })?;
        // 转换成本地类型 + 上报
        let info = updater.ok_or_else(|| SceneFabError::Update {
            phase: "check".into(), message: "no update available".into()
        })?;
        Ok(UpdateInfo::from(info))
    }

    pub async fn download_and_apply(&self, info: UpdateInfo, require: bool) -> Result<(), SceneFabError> {
        // 1. 状态机进入 DOWNLOADING
        // 2. reqwest 流式下载 + SHA-256 校验
        // 3. 如果 require = true 且下载失败 → BLOCKING 强制覆盖设置
        // 4. 写入原子临时文件 + 备份当前安装
        // 5. 退出当前进程 + 执行安装脚本 (Tauri 自动)
        todo!()
    }
}
```

## 10. 性能监控（tracing）

### 10.1 后端 tracing 配置

```rust
// apps/desktop/src-tauri/src/logging.rs
use tracing_subscriber::{Registry, EnvFilter};
use tracing_subscriber::fmt::layer as FmtLayer;
use tracing_subscriber::prelude::*;

pub fn init() {
    let env_filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info,scenefab=debug"));

    let fmt_layer = FmtLayer::builder()
        .with_writer(|| LogWriter)
        .with_ansi(false)
        .with_target(true)
        .compact();

    tracing_subscriber::registry()
        .with(env_filter)
        .with(fmt_layer)
        .init();
}

struct LogWriter;
impl std::io::Write for LogWriter {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        // 1. 标准 stderr
        eprint!("{}", String::from_utf8_lossy(buf));
        // 2. 持久化到 ~/.scenefab/logs/{date}.log
        crate::diagnostics::append_daily_log(buf);
        Ok(buf.len())
    }
    fn flush(&mut self) -> std::io::Result<()> { Ok(()) }
}
```

### 10.2 命令级 tracing span

```rust
#[tauri::command]
#[specta::command]
#[tracing::instrument(name = "cmd.start_pipeline", skip(ctx))]
pub async fn start_pipeline(
    ctx: State<'_, AppContext>,
    source_video: String,
    context: String,
) -> Result<PipelineSnapshot, SceneFabError> {
    debug!(source = %source_video, context_len = context.len(), "starting pipeline");
    let snap = ctx.pipeline.start(source_video, context).await?;
    debug!(state = ?snap.state, "pipeline started");
    Ok(snap)
}
```

### 10.3 前端日志桥接

```ts
// apps/desktop/src/lib/log/logger.ts
import { invoke } from "@tauri-apps/api/core";

const levels = ["debug", "info", "warn", "error"] as const;
type Level = (typeof levels)[number];

export const log = {
  debug: (msg: string, meta?: object) => emit("debug", msg, meta),
  info: (msg: string, meta?: object) => emit("info", msg, meta),
  warn: (msg: string, meta?: object) => emit("warn", msg, meta),
  error: (msg: string, meta?: object) => emit("error", msg, meta),
};

function emit(level: Level, msg: string, meta?: object) {
  const line = meta ? `${msg} ${JSON.stringify(meta)}` : msg;
  // 1. 控制台
  console[level === "debug" ? "log" : level](line);
  // 2. Tauri 后端收集
  invoke("log_collect", { level, msg: line }).catch(() => {});
}
```

## 11. CLI 集成（v3.0 保留 `scenefab` 命令）

> v3.0 虽然 Tauri 是主入口，但仍保留 `scenefab` CLI 用于离线批处理场景（M9 文档工具）。详见 02-target-architecture.md §6。

```rust
// crates/scenefab-cli/src/main.rs
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(version, about = "SceneFab v3.0 — 视频叙事生成器")]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// 启动桌面应用 (等同于 `scenefab`)
    Gui,
    /// 在命令行运行 5 步流水线
    Run {
        #[arg(long)] source: String,
        #[arg(long)] context: String,
        #[arg(long, value_enum)] strategy: MultiVideoStrategy,
    },
    /// 编译 + 启动文档站
    Docs,
    /// 健康检查（无 UI）
    Doctor,
    /// 版本 + 二进制信息
    Info,
}

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    match cli.cmd {
        Cmd::Gui => scenefab_tauri_app::run(),
        Cmd::Run { .. } => scenefab_pipeline::headless::run(...),
        // ...
    }
}
```

## 12. 验收标准（Tauri 集成维度）

| 项                    | 验收                                                                          |
| --------------------- | ----------------------------------------------------------------------------- |
| **Commands 完整覆盖** | 35 核心 commands + 12 扩展点全部存在，全部 specta 类型化                      |
| **TS 类型零漂移**     | `tsc --noEmit` 0 错误，CI 检测 `types.gen.ts` 与 generated 字节一致           |
| **Capability ACL**    | 未授权 IPC 调用全部拒绝；最小权限：主窗口 + 8 个插件                          |
| **CSP**               | 无 unsafe-inline（除样式）/ 无 unsafe-eval（除 wasm-unsafe-eval）/ 无外部域名 |
| **路径白名单**        | 100% 文件操作经过 `PathPolicy::resolve`，单元测试覆盖 36 种边界情况           |
| **API key 加密**      | keyring-rs 存储，明文不上 IPC，前端永远拿不到原始                             |
| **错误契约**          | 所有 Tauri Command 返回 `Result<T, SceneFabError>`，前端类型安全              |
| **事件总线契约**      | 24 个事件全部在 `EventName` 枚举 + 前端 `events.ts` 注册表                    |
| **更新器**            | GitHub Releases 检测 + 增量包 fallback + SHA-256 校验 + 强制回滚              |
| **单实例**            | 第二次启动 focus 已存在窗口 + 解析参数为子命令                                |
| **窗口状态持久化**    | 关闭再开还原 size + position + maximized                                      |
| **日志**              | tracing 自定义日志写入 `~/.scenefab/logs/{date}.log`                          |
| **性能**              | invoke 调用 P95 ≤ 5ms (本地命令)                                              |

---

> **结尾**：下一节进入 **08-implementation-roadmap.md**：分阶段（10 个里程碑 42 周）+ 团队拆分 + 依赖图 + PoC 验证关卡。
