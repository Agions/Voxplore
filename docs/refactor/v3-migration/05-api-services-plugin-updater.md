# 05 · API + Service + Plugin + Updater 详细重写方案

> 📌 本章聚焦四大子系统（API、Service、Plugin、Updater）的具体重写细节，含接口设计、错误处理、性能优化、测试方案。

## 1. API 层：HTTP → Tauri Command

### 1.1 架构变化

```
┌────────────────────────────────────────────────────────┐
│  v2.4.3 (Python)                                        │
│  ┌──────────────┐                                       │
│  │  React UI    │ ──── HTTP/JSON ───► FastAPI (uvicorn) │
│  │  (将来)      │ ◄── 401/200 ────  │                   │
│  └──────────────┘                    │ Auth Middleware   │
│                                       │ RateLimit         │
│                                       │ Exception         │
│                                       └─────────────────► │
│                                                          │
│  进程边界: 1 个 QApplication 进程 + N 个 Uvicorn worker   │
│  网络栈:  TCP/IP + HTTP + CORS + Auth                   │
└────────────────────────────────────────────────────────┘

                           ▼ 重写 ▼

┌────────────────────────────────────────────────────────┐
│  v3.0 (Tauri + Rust)                                    │
│  ┌──────────────┐                                       │
│  │  React UI    │ ──── JSON-RPC (FFI) ───► Tauri Main  │
│  │  (WebView)   │ ◄── typed Result ────  │               │
│  └──────────────┘                        │               │
│  ↑ 沙箱（无 Node.js）                    │               │
│  ↑ Specta 自动生成 TS 类型               │               │
│  ↑ Capability ACL                        │               │
│                                          └──────────────► │
│                                                          │
│  进程边界: 1 个 Rust Main + 1 个 WebView + N 个 WASM     │
│  通信栈:  FFI + 共享内存（无 TCP/IP）                    │
└────────────────────────────────────────────────────────┘
```

### 1.2 Tauri Command 设计模式

**统一签名**：

```rust
#[tauri::command]
pub async fn <domain>_<action>(
    app: tauri::AppHandle,                    // Tauri AppHandle（用于 emit 事件）
    request: <RequestDto>,                    // 入参（specta::Type）
) -> Result<<ResponseDto>, SceneFabError>     // 出参（强类型错误）
```

**完整示例**（project_create）：

```rust
// apps/desktop/src-tauri/src/commands/project.rs

use specta::Type;
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager};
use uuid::Uuid;

use scenefab_core::{Result, SceneFabError};
use scenefab_domain::project::{Project, ProjectMetadata, ProjectType};

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct ProjectCreateRequest {
    pub name: String,
    pub description: Option<String>,
    pub project_type: Option<ProjectType>,
    pub template_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct ProjectDto {
    pub id: Uuid,
    pub name: String,
    pub path: String,
    pub metadata: ProjectMetadata,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub modified_at: chrono::DateTime<chrono::Utc>,
}

impl From<Project> for ProjectDto {
    fn from(p: Project) -> Self {
        Self {
            id: p.id,
            name: p.metadata.name.clone(),
            path: p.path.to_string_lossy().to_string(),
            metadata: p.metadata,
            created_at: p.metadata.created_at,
            modified_at: p.metadata.modified_at,
        }
    }
}

#[tauri::command]
pub async fn project_create(
    app: AppHandle,
    request: ProjectCreateRequest,
) -> Result<ProjectDto> {
    // 1. 限流（防止用户误点）
    let rate_limiter = app.state::<Arc<RateLimiter>>();
    rate_limiter.check("project_create", 5, Duration::from_secs(60))?;

    // 2. 参数校验
    if request.name.is_empty() || request.name.len() > 100 {
        return Err(SceneFabError::Validation(
            "项目名称长度必须在 1-100 之间".into()
        ));
    }

    // 3. 调用服务
    let ctx = app.state::<AppContext>();
    let project_manager = ctx.get_named::<dyn ProjectManager>("project_manager")
        .ok_or_else(|| SceneFabError::ServiceNotFound("project_manager".into()))?;

    let project = project_manager.create_project(
        request.name,
        request.description.unwrap_or_default(),
        request.project_type.unwrap_or(ProjectType::VideoEditing),
        request.template_id,
    ).await?;

    // 4. 发布事件
    let event_bus = ctx.event_bus();
    event_bus.publish("project.created", ProjectCreatedEvent {
        project_id: project.id,
        name: project.metadata.name.clone(),
    }).await;

    Ok(project.into())
}
```

### 1.3 错误处理与 HTTP 兼容

**SceneFabError → Tauri 错误**：

```rust
// apps/desktop/src-tauri/src/error.rs

impl serde::Serialize for SceneFabError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        use serde::ser::SerializeStruct;

        let mut s = serializer.serialize_struct("SceneFabError", 3)?;
        s.serialize_field("error", &self.error_code())?;
        s.serialize_field("message", &self.to_string())?;
        s.serialize_field("details", &self.error_details())?;
        s.end()
    }
}

impl specta::Type for SceneFabError {
    fn inline(_: &mut specta::TypeMap, _: specta::Generics) -> specta::DataType {
        specta::DataType::Struct(specta::Struct {
            name: "SceneFabError".to_string(),
            fields: specta::Fields::Named(vec![
                ("error".to_string(), specta::DataType::String),
                ("message".to_string(), specta::DataType::String),
                ("details".to_string(), specta::DataType::Any),
            ]),
            generics: vec![],
            category: None,
            docs: None,
            inline: true,
        })
    }
}

impl SceneFabError {
    pub fn error_code(&self) -> &'static str {
        match self {
            Self::Config(_) => "CONFIG_ERROR",
            Self::Io(_) => "IO_ERROR",
            Self::Llm(_) => "LLM_ERROR",
            Self::Tts(_) => "TTS_ERROR",
            Self::Ffmpeg(_) => "FFMPEG_ERROR",
            Self::InvalidPath(_) => "INVALID_PATH",
            Self::Plugin(_) => "PLUGIN_ERROR",
            Self::Update(_) => "UPDATE_ERROR",
            Self::ServiceNotFound(_) => "SERVICE_NOT_FOUND",
            Self::PermissionDenied(_) => "PERMISSION_DENIED",
            Self::AlreadyExists(_) => "ALREADY_EXISTS",
            Self::NotFound(_) => "NOT_FOUND",
            Self::Cancelled => "CANCELLED",
            Self::Timeout => "TIMEOUT",
            Self::Other(_) => "INTERNAL_ERROR",
            // ...
        }
    }
}
```

**前端统一错误处理**：

```typescript
// apps/desktop/src/lib/api.ts

export class SceneFabError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "SceneFabError";
  }
}

export async function invokeCommand<T>(
  cmd: string,
  args?: Record<string, unknown>,
): Promise<T> {
  try {
    return await invoke<T>(cmd, args);
  } catch (err) {
    if (isSceneFabError(err)) {
      throw new SceneFabError(err.error, err.message, err.details);
    }
    throw new SceneFabError("UNKNOWN_ERROR", String(err));
  }
}

function isSceneFabError(
  err: unknown,
): err is { error: string; message: string; details?: unknown } {
  return (
    typeof err === "object" &&
    err !== null &&
    "error" in err &&
    "message" in err
  );
}

// TanStack Query 包装
export function useTauriQuery<TData, TArgs = void>(
  command: string,
  args?: TArgs,
  options?: UseQueryOptions<TData, SceneFabError>,
) {
  return useQuery<TData, SceneFabError>({
    queryKey: [command, args],
    queryFn: () =>
      invokeCommand<TData>(command, args as Record<string, unknown>),
    ...options,
  });
}
```

### 1.4 完整 Command 清单（35 个）

| 类别       | Command 名                | 入参                        | 出参                     |
| ---------- | ------------------------- | --------------------------- | ------------------------ |
| **健康**   | `health_get`              | -                           | `HealthDto`              |
|            | `health_ready`            | -                           | `HealthDto`              |
|            | `health_live`             | -                           | `HealthDto`              |
| **项目**   | `project_list`            | -                           | `Vec<ProjectDto>`        |
|            | `project_get`             | `project_id: Uuid`          | `ProjectDto`             |
|            | `project_create`          | `ProjectCreateRequest`      | `ProjectDto`             |
|            | `project_delete`          | `project_id: Uuid`          | `()`                     |
|            | `project_save`            | `project_id: Uuid`          | `()`                     |
|            | `project_close`           | `project_id: Uuid`          | `()`                     |
|            | `project_export`          | `ProjectExportRequest`      | `PathBuf`                |
|            | `project_import`          | `ProjectImportRequest`      | `ProjectDto`             |
|            | `project_recent_list`     | -                           | `Vec<String>`            |
| **模板**   | `template_list`           | -                           | `Vec<TemplateDto>`       |
|            | `template_apply`          | `TemplateApplyRequest`      | `ProjectDto`             |
| **流水线** | `pipeline_start`          | `PipelineStartRequest`      | `PipelineTaskDto`        |
|            | `pipeline_get_status`     | `task_id: Uuid`             | `PipelineStatusDto`      |
|            | `pipeline_cancel`         | `task_id: Uuid`             | `()`                     |
|            | `pipeline_list`           | `PipelineListQuery`         | `Vec<PipelineTaskDto>`   |
| **导出**   | `export_start`            | `ExportRequest`             | `ExportTaskDto`          |
|            | `export_get_status`       | `task_id: Uuid`             | `ExportStatusDto`        |
|            | `export_list`             | `ExportListQuery`           | `Vec<ExportTaskDto>`     |
|            | `export_get_presets`      | -                           | `Vec<ExportPresetDto>`   |
| **配置**   | `config_get_all`          | -                           | `HashMap<String, Value>` |
|            | `config_get`              | `key: String`               | `Value`                  |
|            | `config_set`              | `key: String, value: Value` | `()`                     |
|            | `config_reset`            | -                           | `()`                     |
|            | `config_list_profiles`    | -                           | `Vec<ProfileDto>`        |
|            | `config_apply_profile`    | `profile_name: String`      | `()`                     |
| **插件**   | `plugin_list`             | -                           | `Vec<PluginDto>`         |
|            | `plugin_enable`           | `plugin_id: String`         | `()`                     |
|            | `plugin_disable`          | `plugin_id: String`         | `()`                     |
|            | `plugin_install`          | `PluginInstallRequest`      | `PluginDto`              |
|            | `plugin_uninstall`        | `plugin_id: String`         | `()`                     |
| **更新**   | `update_check`            | -                           | `UpdateManifestDto`      |
|            | `update_download_install` | -                           | `()`                     |
|            | `update_rollback`         | `version: String`           | `()`                     |
| **系统**   | `system_get_metrics`      | -                           | `SystemMetricsDto`       |
|            | `system_get_version`      | -                           | `VersionInfoDto`         |
| **帮助**   | `help_list_topics`        | -                           | `Vec<HelpTopicDto>`      |
|            | `help_get_topic`          | `topic_id: String`          | `HelpContentDto`         |

### 1.5 Capability 声明

**每个 Command 必须在 capability 中声明**：

```json
// apps/desktop/src-tauri/capabilities/default.json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Default permissions for SceneFab",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "core:event:default",
    "core:window:default",
    "core:webview:default",
    "core:app:default",
    "core:path:default",

    "fs:default",
    "fs:allow-read-file",
    "fs:allow-write-file",
    "fs:allow-read-text-file",
    "fs:allow-write-text-file",
    "fs:allow-exists",
    "fs:allow-mkdir",
    "fs:allow-remove",
    {
      "identifier": "fs:scope",
      "allow": [
        { "path": "$HOME/SceneFab/**" },
        { "path": "$HOME/.scenefab/**" },
        { "path": "$HOME/.cache/scenefab/**" },
        { "path": "$HOME/Documents/SceneFab/**" },
        { "path": "$DESKTOP/**" },
        { "path": "$DOWNLOAD/**" },
        { "path": "$VIDEO/**" }
      ]
    },

    "dialog:default",
    "dialog:allow-open",
    "dialog:allow-save",
    "dialog:allow-message",
    "dialog:allow-ask",
    "dialog:allow-confirm",

    "shell:default",
    {
      "identifier": "shell:allow-execute",
      "allow": [
        { "name": "ffmpeg", "args": true, "sidecar": true },
        { "name": "ffprobe", "args": true, "sidecar": true },
        { "name": "edge-tts", "args": true }
      ]
    },

    "updater:default",
    "store:default",
    "os:default",
    "notification:default",
    "process:default",
    "window-state:default",
    "deep-link:default",
    "log:default",
    "single-instance:default"
  ]
}
```

## 2. Service 层：核心业务重写

### 2.1 LLM 子系统（最复杂）

#### 2.1.1 抽象 Trait

```rust
// crates/scenefab-llm/src/provider.rs

use async_trait::async_trait;
use futures::Stream;
use std::pin::Pin;
use std::sync::Arc;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Type)]
#[serde(rename_all = "snake_case")]
pub enum ProviderType {
    Qwen,
    Qwen37,
    Kimi,
    Glm5,
    Claude,
    Gemini,
    DeepSeek,
    Doubao,
    Hunyuan,
    Local,
    OpenAiCompat,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct LlmMessage {
    pub role: LlmRole,
    pub content: String,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, Type)]
#[serde(rename_all = "lowercase")]
pub enum LlmRole {
    System,
    User,
    Assistant,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct LlmRequest {
    pub model: String,
    pub messages: Vec<LlmMessage>,
    pub temperature: Option<f32>,
    pub max_tokens: Option<u32>,
    pub top_p: Option<f32>,
    pub stop: Option<Vec<String>>,
    pub user: Option<String>,
    pub stream: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct LlmResponse {
    pub id: String,
    pub model: String,
    pub content: String,
    pub usage: TokenUsage,
    pub finish_reason: FinishReason,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct LlmChunk {
    pub id: String,
    pub delta: String,
    pub finish_reason: Option<FinishReason>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct TokenUsage {
    pub prompt_tokens: u32,
    pub completion_tokens: u32,
    pub total_tokens: u32,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, Type)]
#[serde(rename_all = "snake_case")]
pub enum FinishReason {
    Stop,
    Length,
    ContentFilter,
    ToolCalls,
    Error,
}

#[async_trait]
pub trait LlmProvider: Send + Sync {
    fn provider_type(&self) -> ProviderType;
    fn name(&self) -> &'static str;
    fn default_model(&self) -> &'static str;
    fn supported_models(&self) -> &'static [&'static str];
    fn max_context_tokens(&self) -> usize;

    /// 非流式调用
    async fn complete(&self, request: LlmRequest) -> Result<LlmResponse, LlmError>;

    /// 流式调用
    async fn stream(
        &self,
        request: LlmRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<LlmChunk, LlmError>> + Send>>, LlmError>;

    /// 健康检查
    async fn health_check(&self) -> Result<(), LlmError>;
}
```

#### 2.1.2 OpenAI 兼容 Provider（最常用，作为模板）

```rust
// crates/scenefab-llm/src/providers/openai_compat.rs

use super::*;

pub struct OpenAiCompatProvider {
    config: OpenAiCompatConfig,
    client: reqwest::Client,
}

#[derive(Debug, Clone)]
pub struct OpenAiCompatConfig {
    pub provider_type: ProviderType,
    pub display_name: String,
    pub base_url: String,
    pub api_key: String,  // 从 Keyring 加载
    pub default_model: String,
    pub supported_models: Vec<String>,
    pub max_context_tokens: usize,
    pub request_timeout: Duration,
}

impl OpenAiCompatProvider {
    pub fn new(config: OpenAiCompatConfig) -> Self {
        let client = reqwest::Client::builder()
            .timeout(config.request_timeout)
            .pool_max_idle_per_host(10)
            .build()
            .expect("Failed to build HTTP client");
        Self { config, client }
    }
}

#[async_trait]
impl LlmProvider for OpenAiCompatProvider {
    fn provider_type(&self) -> ProviderType { self.config.provider_type }
    fn name(&self) -> &'static str { "OpenAI Compatible" }
    fn default_model(&self) -> &'static str { Box::leak(self.config.default_model.clone().into_boxed_str()) }
    fn supported_models(&self) -> &'static [&'static str] {
        Box::leak(self.config.supported_models.iter().map(|s| s.as_str()).collect::<Vec<_>>().into_boxed_slice())
    }
    fn max_context_tokens(&self) -> usize { self.config.max_context_tokens }

    async fn complete(&self, request: LlmRequest) -> Result<LlmResponse, LlmError> {
        let url = format!("{}/chat/completions", self.config.base_url);
        let body = serde_json::json!({
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature.unwrap_or(0.7),
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "stop": request.stop,
            "user": request.user,
            "stream": false,
        });

        let response = self.client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.config.api_key))
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await
            .map_err(|e| LlmError::Network(e.to_string()))?;

        if !response.status().is_success() {
            let status = response.status();
            let text = response.text().await.unwrap_or_default();
            return Err(LlmError::Api { status: status.as_u16(), message: text });
        }

        let resp: OpenAiResponse = response.json().await
            .map_err(|e| LlmError::Parse(e.to_string()))?;

        Ok(LlmResponse {
            id: resp.id,
            model: resp.model,
            content: resp.choices.first()
                .and_then(|c| c.message.content.clone())
                .unwrap_or_default(),
            usage: TokenUsage {
                prompt_tokens: resp.usage.prompt_tokens,
                completion_tokens: resp.usage.completion_tokens,
                total_tokens: resp.usage.total_tokens,
            },
            finish_reason: parse_finish_reason(&resp.choices.first().map(|c| &c.finish_reason)),
            created_at: chrono::Utc::now(),
        })
    }

    async fn stream(
        &self,
        request: LlmRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<LlmChunk, LlmError>> + Send>>, LlmError> {
        let url = format!("{}/chat/completions", self.config.base_url);
        let mut body = serde_json::json!({
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature.unwrap_or(0.7),
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "stop": request.stop,
            "stream": true,
        });
        body["stream"] = serde_json::Value::Bool(true);

        let response = self.client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.config.api_key))
            .header("Content-Type", "application/json")
            .header("Accept", "text/event-stream")
            .json(&body)
            .send()
            .await
            .map_err(|e| LlmError::Network(e.to_string()))?;

        if !response.status().is_success() {
            let status = response.status();
            let text = response.text().await.unwrap_or_default();
            return Err(LlmError::Api { status: status.as_u16(), message: text });
        }

        // 解析 SSE 流
        let stream = response.bytes_stream()
            .map_err(|e| LlmError::Network(e.to_string()))
            .and_then(|chunk| async move {
                // 解析 SSE 格式
                let text = std::str::from_utf8(&chunk)
                    .map_err(|e| LlmError::Parse(e.to_string()))?;

                // 每行: "data: {...}\n\n"
                let mut chunks = Vec::new();
                for line in text.lines() {
                    if let Some(data) = line.strip_prefix("data: ") {
                        if data == "[DONE]" {
                            break;
                        }
                        if let Ok(parsed) = serde_json::from_str::<OpenAiStreamChunk>(data) {
                            if let Some(choice) = parsed.choices.first() {
                                chunks.push(Ok(LlmChunk {
                                    id: parsed.id,
                                    delta: choice.delta.content.clone().unwrap_or_default(),
                                    finish_reason: choice.finish_reason.as_ref()
                                        .and_then(|r| parse_finish_reason_opt(r)),
                                }));
                            }
                        }
                    }
                }
                Ok(chunks)
            })
            .map(|r| futures::stream::iter(r.into_iter().flatten()))
            .try_flatten();

        Ok(Box::pin(stream))
    }

    async fn health_check(&self) -> Result<(), LlmError> {
        let url = format!("{}/models", self.config.base_url);
        let response = self.client
            .get(&url)
            .header("Authorization", format!("Bearer {}", self.config.api_key))
            .send()
            .await
            .map_err(|e| LlmError::Network(e.to_string()))?;
        if response.status().is_success() {
            Ok(())
        } else {
            Err(LlmError::Api { status: response.status().as_u16(), message: "Health check failed".into() })
        }
    }
}
```

#### 2.1.3 11 个 Provider 实现要点

| Provider     | 关键差异点                                                                 | 实现策略                                                                                     |
| ------------ | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **Qwen**     | 阿里 DashScope API，OpenAI 兼容                                            | 用 `OpenAiCompatProvider`，base_url 设为 `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| **Qwen3.7**  | 同上，更新模型列表                                                         | 同上                                                                                         |
| **Kimi**     | Moonshot API，OpenAI 兼容                                                  | 同上                                                                                         |
| **GLM-5**    | 智谱 API，自定义协议                                                       | 单独实现 `Glm5Provider`                                                                      |
| **Claude**   | Anthropic 协议（非 OpenAI），需要 `x-api-key` + `anthropic-version` header | 单独实现 `ClaudeProvider`                                                                    |
| **Gemini**   | Google Gemini 协议（完全不同）                                             | 单独实现 `GeminiProvider`                                                                    |
| **DeepSeek** | DeepSeek API，OpenAI 兼容                                                  | 用 `OpenAiCompatProvider`                                                                    |
| **Doubao**   | 字节火山方舟，OpenAI 兼容                                                  | 用 `OpenAiCompatProvider`                                                                    |
| **Hunyuan**  | 腾讯混元，自定义协议（TC3-HMAC-SHA256 签名）                               | 单独实现 `HunyuanProvider`                                                                   |
| **Local**    | Ollama，OpenAI 兼容（`/v1` 路径）                                          | 用 `OpenAiCompatProvider`                                                                    |
| **OpenAI**   | 标准 OpenAI                                                                | 用 `OpenAiCompatProvider`                                                                    |

#### 2.1.4 LlmManager（路由 + 失败切换）

```rust
// crates/scenefab-llm/src/manager.rs

pub struct LlmManager {
    providers: HashMap<ProviderType, Arc<dyn LlmProvider>>,
    default_provider: ProviderType,
    fallback_chain: Vec<ProviderType>,
    event_bus: Arc<EventBus>,
    rate_limiter: Arc<RateLimiter>,
    retry_policy: RetryPolicy,
}

impl LlmManager {
    pub async fn new(config: LlmConfig, keyring: &Keyring, event_bus: Arc<EventBus>) -> Result<Self, LlmError> {
        let mut providers: HashMap<ProviderType, Arc<dyn LlmProvider>> = HashMap::new();

        for (ptype, pconfig) in &config.providers {
            if !pconfig.enabled { continue; }
            let api_key = keyring.get_api_key(&format!("llm.{}", ptype))
                .map_err(|e| LlmError::Config(format!("Missing API key for {}: {}", ptype, e)))?;
            let provider: Arc<dyn LlmProvider> = match ptype {
                ProviderType::Qwen | ProviderType::Qwen37 | ProviderType::Kimi
                | ProviderType::DeepSeek | ProviderType::Doubao | ProviderType::Local => {
                    Arc::new(OpenAiCompatProvider::new(OpenAiCompatConfig {
                        provider_type: *ptype,
                        display_name: pconfig.display_name.clone(),
                        base_url: pconfig.base_url.clone(),
                        api_key,
                        default_model: pconfig.default_model.clone(),
                        supported_models: pconfig.supported_models.clone(),
                        max_context_tokens: pconfig.max_context_tokens,
                        request_timeout: Duration::from_secs(pconfig.timeout_seconds),
                    }))
                },
                ProviderType::Claude => Arc::new(ClaudeProvider::new(api_key, pconfig.default_model.clone())),
                ProviderType::Gemini => Arc::new(GeminiProvider::new(api_key, pconfig.default_model.clone())),
                ProviderType::Glm5 => Arc::new(Glm5Provider::new(api_key, pconfig.default_model.clone())),
                ProviderType::Hunyuan => Arc::new(HunyuanProvider::new(api_key, pconfig.default_model.clone())),
                ProviderType::OpenAiCompat => Arc::new(OpenAiCompatProvider::new(OpenAiCompatConfig {
                    provider_type: ProviderType::OpenAiCompat,
                    display_name: pconfig.display_name.clone(),
                    base_url: pconfig.base_url.clone(),
                    api_key,
                    default_model: pconfig.default_model.clone(),
                    supported_models: pconfig.supported_models.clone(),
                    max_context_tokens: pconfig.max_context_tokens,
                    request_timeout: Duration::from_secs(pconfig.timeout_seconds),
                })),
            };
            providers.insert(*ptype, provider);
        }

        Ok(Self {
            providers,
            default_provider: config.default_provider,
            fallback_chain: config.fallback_chain,
            event_bus,
            rate_limiter: Arc::new(RateLimiter::new(config.rate_limit)),
            retry_policy: RetryPolicy::exponential(Duration::from_secs(2), 3),
        })
    }

    /// 调用 LLM（带失败切换）
    pub async fn complete(
        &self,
        preferred: Option<ProviderType>,
        request: LlmRequest,
    ) -> Result<LlmResponse, LlmError> {
        let chain = self.build_call_chain(preferred);
        let mut last_err: Option<LlmError> = None;

        for provider_type in chain {
            self.rate_limiter.check(&provider_type.to_string())?;
            let provider = match self.providers.get(&provider_type) {
                Some(p) => p,
                None => continue,
            };

            match self.retry_policy.execute(|| provider.complete(request.clone())).await {
                Ok(response) => {
                    self.event_bus.publish("llm.completed", json!({
                        "provider": provider_type,
                        "model": response.model,
                        "tokens": response.usage.total_tokens,
                    })).await;
                    return Ok(response);
                }
                Err(e) => {
                    tracing::warn!(provider = ?provider_type, error = %e, "LLM call failed, trying fallback");
                    self.event_bus.publish("llm.error", json!({
                        "provider": provider_type,
                        "error": e.to_string(),
                    })).await;
                    last_err = Some(e);
                }
            }
        }

        Err(last_err.unwrap_or_else(|| LlmError::NoProvider))
    }

    /// 流式调用
    pub async fn stream(
        &self,
        preferred: Option<ProviderType>,
        request: LlmRequest,
        on_chunk: impl Fn(LlmChunk) + Send + 'static,
    ) -> Result<LlmResponse, LlmError> {
        // 类似 complete，但用 stream + 累积 chunks
    }
}
```

### 2.2 Video 子系统（MonologueMaker）

#### 2.2.1 5 步流程实现

```rust
// crates/scenefab-video/src/monologue_maker.rs

pub struct MonologueMaker {
    ffmpeg: Arc<Ffmpeg>,
    llm_manager: Arc<LlmManager>,
    tts_manager: Arc<TtsManager>,
    caption_generator: Arc<CaptionGenerator>,
    perspective_mapper: Arc<PerspectiveMapper>,
    video_interleaver: Arc<VideoInterleaver>,
    scene_converter: Arc<SceneConverter>,
    event_bus: Arc<EventBus>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct MonologueMakerConfig {
    pub strategy: MultiVideoStrategy,
    pub emotion: EmotionType,
    pub style: NarrationStyle,
    pub voice_id: Option<String>,
    pub caption_style: CaptionStyle,
    pub interleave_mode: Option<InterleaveMode>,
    pub include_interleave: bool,
}

impl MonologueMaker {
    /// 完整流水线（5 步）
    pub async fn run_full_pipeline(
        &self,
        project: &mut MonologueProject,
        config: MonologueMakerConfig,
    ) -> Result<InterleaveTimeline, SceneFabError> {
        // 步骤 1: 分析场景
        self.publish_progress(project.task_id, "analyzing", 10.0, "正在分析视频场景").await;
        self.analyze_scenes(project).await?;
        project.scene_info = Some(self.extract_scene_info(project)?);

        // 步骤 2: 生成脚本
        self.publish_progress(project.task_id, "script", 30.0, "正在生成解说脚本").await;
        self.generate_script_with_style(project, config.style, config.emotion).await?;

        // 步骤 3: 生成配音
        self.publish_progress(project.task_id, "voice", 55.0, "正在合成配音").await;
        self.generate_voice(project, config.voice_id.clone()).await?;

        // 步骤 4: 生成字幕
        self.publish_progress(project.task_id, "caption", 75.0, "正在生成字幕").await;
        self.generate_captions(project, config.caption_style).await?;

        // 步骤 5（可选）: 视角映射 + 穿插
        let mut timeline: Option<InterleaveTimeline> = None;
        if config.include_interleave {
            self.publish_progress(project.task_id, "interleaving", 85.0, "正在处理视频穿插").await;
            let perspective_shots = self.perspective_mapper
                .map_perspective(project, &config.emotion)
                .await?;
            let tl = self.video_interleaver
                .interleave(project, &perspective_shots, config.interleave_mode.unwrap_or(InterleaveMode::Cinematic))
                .await?;
            self.apply_interleave_to_project(project, &tl).await?;
            timeline = Some(tl);
        }

        // 步骤 6: 导出
        self.publish_progress(project.task_id, "exporting", 95.0, "正在生成最终视频").await;
        let output_dir = project.output_dir.clone();
        self.export_to_jianying(project, &output_dir).await?;

        self.publish_progress(project.task_id, "completed", 100.0, "处理完成").await;

        timeline.ok_or_else(|| SceneFabError::Other("Timeline not generated".into()))
    }

    async fn analyze_scenes(&self, project: &mut MonologueProject) -> Result<(), SceneFabError> {
        for source in &project.sources {
            let probe = self.ffmpeg.probe(&source.path).await?;
            let scenes = self.scene_converter.detect_scenes(&source.path).await?;
            source.probe = Some(probe);
            source.scenes = scenes;
        }
        Ok(())
    }

    async fn generate_script_with_style(
        &self,
        project: &mut MonologueProject,
        style: NarrationStyle,
        emotion: EmotionType,
    ) -> Result<(), SceneFabError> {
        let style_prompt = style_prompts::get_prompt(style, emotion);
        let context = build_context(project);

        let script = self.llm_manager
            .stream(
                None,  // 用默认 provider
                LlmRequest {
                    model: "gpt-4o".to_string(),  // TODO: 从配置读
                    messages: vec![
                        LlmMessage { role: LlmRole::System, content: style_prompt },
                        LlmMessage { role: LlmRole::User, content: context },
                    ],
                    temperature: Some(0.8),
                    max_tokens: Some(4000),
                    top_p: None,
                    stop: None,
                    user: None,
                    stream: true,
                },
                |chunk| {
                    // 实时回调（前端可订阅）
                    project.script_partial.push_str(&chunk.delta);
                },
            )
            .await?;

        project.script = script;
        Ok(())
    }

    async fn generate_voice(
        &self,
        project: &mut MonologueProject,
        voice_id: Option<String>,
    ) -> Result<(), SceneFabError> {
        let audio = self.tts_manager
            .synthesize(&project.script, voice_id.as_deref().unwrap_or("zh-CN-XiaoxiaoNeural"))
            .await?;
        project.audio_track = Some(audio);
        Ok(())
    }

    async fn generate_captions(
        &self,
        project: &mut MonologueProject,
        style: CaptionStyle,
    ) -> Result<(), SceneFabError> {
        let captions = self.caption_generator
            .generate(&project.script, project.audio_track.as_ref().unwrap(), style)
            .await?;
        project.subtitles = captions;
        Ok(())
    }

    async fn publish_progress(
        &self,
        task_id: Uuid,
        stage: &str,
        progress: f32,
        message: &str,
    ) {
        self.event_bus.publish("task.progress", json!({
            "task_id": task_id,
            "stage": stage,
            "progress": progress,
            "message": message,
        })).await;
    }
}
```

### 2.3 插件系统（WASM 沙箱）

#### 2.3.1 插件清单（TOML）

```toml
# ~/.scenefab/plugins/deepseek-voice/plugin.toml
[plugin]
id = "scenefab.plugin.deepseek_voice"
name = "DeepSeek Voice Clone"
version = "1.0.0"
author = "Community"
description = "DeepSeek API 音色克隆插件"
plugin_type = "voice_clone"
entry_point = "deepseek_voice:Plugin"
wasm = "plugin.wasm"
homepage = "https://github.com/example/deepseek-voice"
license = "MIT"

[permissions]
network = ["api.deepseek.com", "*.volces.com"]
filesystem = [{ path = "$HOME/.scenefab/voice_models", mode = "read" }]
environment = []

[dependencies]
"scenefab.plugin.sdk" = "^1.0"

[signature]
algorithm = "ed25519"
public_key = "f3b8...c1d2"
signature = "a7c9...e5f6"  # 对 plugin.wasm 字节的签名
```

#### 2.3.2 插件 SDK（Rust → WASM）

```rust
// crates/scenefab-plugin/src/sdk/mod.rs

/// 插件必须实现的 trait
#[async_trait]
pub trait Plugin: Send + Sync {
    fn manifest(&self) -> &PluginManifest;

    async fn initialize(&mut self, context: &dyn PluginContext) -> Result<(), PluginError>;
    async fn enable(&mut self) -> Result<(), PluginError>;
    async fn disable(&mut self) -> Result<(), PluginError>;
    async fn destroy(&mut self) -> Result<(), PluginError>;

    /// 插件自定义命令（由 plugin.toml 中 commands 列表定义）
    async fn execute(&self, command: &str, args: Value) -> Result<Value, PluginError>;
}

/// 插件上下文（注入到插件，提供受限能力）
#[async_trait]
pub trait PluginContext: Send + Sync {
    /// 读取文件（受 manifest 权限限制）
    async fn read_file(&self, path: &Path) -> Result<Vec<u8>, PluginError>;
    /// 写入文件
    async fn write_file(&self, path: &Path, data: &[u8]) -> Result<(), PluginError>;
    /// 发送网络请求（受 host 白名单限制）
    async fn http_request(&self, req: HttpRequest) -> Result<HttpResponse, PluginError>;
    /// 记录日志
    fn log(&self, level: LogLevel, message: &str);
    /// 读取配置
    async fn get_config(&self, key: &str) -> Result<Option<Value>, PluginError>;
    /// 写入配置
    async fn set_config(&self, key: &str, value: Value) -> Result<(), PluginError>;
}

/// 简化插件开发的宏
#[macro_export]
macro_rules! scenefab_plugin {
    ($plugin_type:ty) => {
        #[no_mangle]
        pub extern "C" fn _scenefab_plugin_create() -> *mut dyn $crate::Plugin {
            Box::into_raw(Box::new(<$plugin_type>::default()))
        }

        #[no_mangle]
        pub extern "C" fn _scenefab_plugin_destroy(ptr: *mut dyn $crate::Plugin) {
            if !ptr.is_null() {
                unsafe { drop(Box::from_raw(ptr)); }
            }
        }
    };
}
```

#### 2.3.3 插件示例（DeepSeek Voice）

```rust
// crates/scenefab-plugin/examples/deepseek_voice/src/lib.rs

use scenefab_plugin::prelude::*;
use serde::{Deserialize, Serialize};
use async_trait::async_trait;

#[derive(Default)]
pub struct DeepSeekVoicePlugin {
    manifest: PluginManifest,
    context: Option<Box<dyn PluginContext>>,
    enabled: bool,
}

#[async_trait]
impl Plugin for DeepSeekVoicePlugin {
    fn manifest(&self) -> &PluginManifest {
        &self.manifest
    }

    async fn initialize(&mut self, context: &dyn PluginContext) -> Result<(), PluginError> {
        self.context = Some(unsafe { std::mem::transmute_copy(&context) });
        Ok(())
    }

    async fn enable(&mut self) -> Result<(), PluginError> {
        self.enabled = true;
        Ok(())
    }

    async fn disable(&mut self) -> Result<(), PluginError> {
        self.enabled = false;
        Ok(())
    }

    async fn destroy(&mut self) -> Result<(), PluginError> {
        self.context = None;
        Ok(())
    }

    async fn execute(&self, command: &str, args: Value) -> Result<Value, PluginError> {
        match command {
            "list_voices" => Ok(serde_json::json!([
                { "id": "deepseek_female_1", "name": "DeepSeek 女声 1", "language": "zh-CN" },
                { "id": "deepseek_male_1", "name": "DeepSeek 男声 1", "language": "zh-CN" }
            ])),
            "generate_voice" => {
                let req: GenerateVoiceRequest = serde_json::from_value(args)?;
                let ctx = self.context.as_ref().ok_or(PluginError::NotInitialized)?;

                // 调 DeepSeek API
                let response = ctx.http_request(HttpRequest {
                    method: "POST".into(),
                    url: "https://api.deepseek.com/v1/audio/speech".into(),
                    headers: vec![("Authorization".into(), format!("Bearer {}", req.api_key))],
                    body: serde_json::to_vec(&req)?,
                }).await?;

                Ok(serde_json::json!({ "audio": response.body }))
            }
            _ => Err(PluginError::UnknownCommand(command.to_string())),
        }
    }
}

#[derive(Deserialize)]
struct GenerateVoiceRequest {
    text: String,
    voice_id: String,
    api_key: String,
}

scenefab_plugin!(DeepSeekVoicePlugin);
```

**编译为 WASM**：

```toml
# crates/scenefab-plugin/examples/deepseek_voice/Cargo.toml
[package]
name = "deepseek_voice_plugin"
version = "1.0.0"
edition = "2021"

[lib]
crate-type = ["cdylib"]

[dependencies]
scenefab-plugin = { path = "../.." }
async-trait = "0.1"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
```

```bash
cargo build --target wasm32-unknown-unknown --release
# 产物: target/wasm32-unknown-unknown/release/deepseek_voice_plugin.wasm
```

#### 2.3.4 wasmtime 沙箱加载

```rust
// crates/scenefab-plugin/src/runtime.rs

use wasmtime::*;

pub struct PluginRuntime {
    engine: Engine,
    instances: HashMap<String, PluginInstance>,
}

pub struct PluginInstance {
    store: Store<PluginHostState>,
    instance: Instance,
    plugin: Box<dyn Plugin>,
    manifest: PluginManifest,
}

pub struct PluginHostState {
    context: Box<dyn PluginContext>,
    permissions: Vec<Permission>,
}

impl PluginRuntime {
    pub fn new() -> Result<Self, PluginError> {
        let mut config = Config::default();
        config.wasm_component_model(true);
        config.async_support(true);
        config.consume_fuel(true);  // 防止无限循环
        let engine = Engine::new(&config)?;
        Ok(Self {
            engine,
            instances: HashMap::new(),
        })
    }

    pub async fn load(
        &self,
        wasm_bytes: &[u8],
        manifest: PluginManifest,
        context: Box<dyn PluginContext>,
    ) -> Result<PluginInstance, PluginError> {
        // 1. 验证签名
        if let Some(sig) = &manifest.signature {
            SignatureVerifier::default().verify(wasm_bytes, sig)?;
        }

        // 2. 编译模块
        let module = Module::new(&self.engine, wasm_bytes)?;

        // 3. 链接 host functions（受限 API）
        let mut linker = Linker::new(&self.engine);
        self.register_host_functions(&mut linker)?;

        // 4. 设置 fuel（防止资源耗尽）
        let host_state = PluginHostState { context, permissions: manifest.permissions.clone() };
        let mut store = Store::new(&self.engine, host_state);
        store.set_fuel(1_000_000)?;

        // 5. 实例化
        let instance = linker.instantiate_async(&mut store, &module).await?;

        // 6. 调用 _scenefab_plugin_create
        let create_fn = instance.get_typed_func::<(), *mut dyn Plugin, _>(&mut store, "_scenefab_plugin_create")?;
        let plugin_ptr = create_fn.call_async(&mut store, ()).await?;

        Ok(PluginInstance {
            store,
            instance,
            plugin: unsafe { Box::from_raw(plugin_ptr) },
            manifest,
        })
    }
}
```

### 2.4 Updater 子系统

```rust
// crates/scenefab-update/src/service.rs

pub struct UpdaterService {
    channel: UpdateChannel,
    current_version: Version,
    api_url: String,
    downloader: Downloader,
    installer: Installer,
    state: Arc<RwLock<UpdaterState>>,
    event_tx: broadcast::Sender<UpdaterEvent>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Type)]
pub struct UpdaterState {
    pub stage: UpdateStage,
    pub manifest: Option<UpdateManifestDto>,
    pub progress_percent: f32,
    pub progress_speed_bps: f32,
    pub last_error: String,
    pub backup_record: Option<BackupRecordDto>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, Type)]
#[serde(rename_all = "snake_case")]
pub enum UpdateStage {
    Idle,
    Checking,
    Available,
    Downloading,
    Verifying,
    Installing,
    Done,
    Failed,
    RolledBack,
}

impl UpdaterService {
    /// 检查更新
    pub async fn check(&self) -> Result<Option<UpdateManifestDto>, SceneFabError> {
        self.set_stage(UpdateStage::Checking).await;
        let payload = self.fetch_release_payload().await
            .map_err(|e| {
                self.set_stage(UpdateStage::Failed).await;
                SceneFabError::Update(format!("Failed to fetch release: {}", e))
            })?;
        let manifests = parse_release_manifest(&payload, self.channel)?;
        let best = select_best_manifest(&manifests, &self.current_version);

        if let Some(m) = best {
            self.state.write().await.manifest = Some(m.clone().into());
            self.set_stage(UpdateStage::Available).await;
            self.event_tx.send(UpdaterEvent::UpdateAvailable(m.into())).ok();
            Ok(Some(m.into()))
        } else {
            self.set_stage(UpdateStage::Idle).await;
            self.event_tx.send(UpdaterEvent::UpdateUnavailable).ok();
            Ok(None)
        }
    }

    /// 下载并安装
    pub async fn download_and_install(&self) -> Result<(), SceneFabError> {
        let manifest = self.state.read().await.manifest.clone()
            .ok_or(SceneFabError::Update("No manifest available".into()))?;

        // 阶段 1: 下载
        self.set_stage(UpdateStage::Downloading).await;
        let pkg_path = self.downloader.download(
            &manifest.download_url,
            &self.download_cache.join(&manifest.asset_name),
            |progress| {
                // 进度回调
                self.report_progress(progress.percent, &format!("下载中 {:.1}%", progress.percent));
            },
        ).await?;

        // 阶段 2: 校验
        self.set_stage(UpdateStage::Verifying).await;
        verify_sha256(&pkg_path, &manifest.sha256)?;

        // 阶段 3: 备份
        let backup = self.installer.backup_current(&self.app_dir, &self.current_version.to_string())?;

        // 阶段 4: 安装
        self.set_stage(UpdateStage::Installing).await;
        match self.installer.install(&pkg_path, &self.app_dir).await {
            Ok(_) => {
                self.state.write().await.current_version = manifest.version.clone();
                self.set_stage(UpdateStage::Done).await;
                self.event_tx.send(UpdaterEvent::InstallComplete(manifest.version.to_string())).ok();
                Ok(())
            }
            Err(e) => {
                // 安装失败 → 回滚
                self.installer.rollback(&backup, &self.app_dir).await.ok();
                self.set_stage(UpdateStage::RolledBack).await;
                Err(SceneFabError::Update(format!("Install failed: {}", e)))
            }
        }
    }

    /// 回滚
    pub async fn rollback(&self, version: Option<&str>) -> Result<(), SceneFabError> {
        let records = self.installer.list_backups().await?;
        let target = match version {
            Some(v) => records.into_iter().find(|r| r.version == v),
            None => records.first().cloned(),
        }.ok_or(SceneFabError::Update("No backup available".into()))?;

        self.installer.rollback(&target, &self.app_dir).await?;
        self.state.write().await.current_version = target.version.clone();
        self.set_stage(UpdateStage::RolledBack).await;
        self.event_tx.send(UpdaterEvent::RolledBack(target.version)).ok();
        Ok(())
    }
}
```

## 3. 错误处理统一规范

### 3.1 Rust 端错误分类

```rust
// crates/scenefab-core/src/error.rs

#[derive(Debug, thiserror::Error)]
pub enum SceneFabError {
    // 配置
    #[error("配置错误: {message}")]
    Config { message: String, source: Option<Box<dyn std::error::Error + Send + Sync>> },

    // IO
    #[error("IO 错误: {0}")]
    Io(#[from] std::io::Error),

    // 序列化
    #[error("序列化错误: {0}")]
    Serde(#[from] serde_json::Error),

    // 数据库
    #[error("数据库错误: {0}")]
    Database(#[from] sqlx::Error),

    // LLM
    #[error("LLM 调用错误: {0}")]
    Llm(String),

    // TTS
    #[error("TTS 调用错误: {0}")]
    Tts(String),

    // FFmpeg
    #[error("FFmpeg 执行错误: {0}")]
    Ffmpeg(String),

    // 路径安全
    #[error("路径非法: {path}（原因: {reason}）")]
    InvalidPath { path: String, reason: String },

    // 插件
    #[error("插件错误: {0}")]
    Plugin(String),

    // 更新
    #[error("更新错误: {0}")]
    Update(String),

    // 业务
    #[error("服务未找到: {0}")]
    ServiceNotFound(String),

    #[error("权限拒绝: {0}")]
    PermissionDenied(String),

    #[error("已存在: {0}")]
    AlreadyExists(String),

    #[error("未找到: {0}")]
    NotFound(String),

    #[error("验证失败: {0}")]
    Validation(String),

    #[error("用户取消")]
    Cancelled,

    #[error("超时")]
    Timeout,

    #[error("限流: {0}")]
    RateLimited(String),

    #[error("内部错误: {0}")]
    Internal(String),
}
```

### 3.2 前端错误处理

```typescript
// apps/desktop/src/lib/error.ts

export class SceneFabError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "SceneFabError";
  }

  static fromTauri(err: unknown): SceneFabError {
    if (isSceneFabErrorPayload(err)) {
      return new SceneFabError(err.error, err.message, err.details);
    }
    return new SceneFabError("UNKNOWN_ERROR", String(err));
  }

  isUserCancelled(): boolean {
    return this.code === "CANCELLED" || this.code === "USER_CANCELLED";
  }

  isRetryable(): boolean {
    return [
      "TIMEOUT",
      "RATE_LIMITED",
      "NETWORK_ERROR",
      "INTERNAL_ERROR",
    ].includes(this.code);
  }
}

// TanStack Query 全局错误处理
queryClient.setDefaultOptions({
  queries: {
    retry: (failureCount, error) => {
      if (error instanceof SceneFabError) {
        return error.isRetryable() && failureCount < 3;
      }
      return false;
    },
    onError: (error) => {
      if (error instanceof SceneFabError) {
        toast.error(getI18nMessage(`errors.${error.code}`, error.message));
      }
    },
  },
});
```

## 4. 性能优化策略

### 4.1 关键优化点

| 优化点            | 策略                                                  | 预期效果                   |
| ----------------- | ----------------------------------------------------- | -------------------------- |
| **启动时间**      | lazy load 模块（tauri::Builder 不预加载未用 Command） | <500ms 启动                |
| **视频处理**      | tokio::task::spawn_blocking + rayon 并行抽帧          | 5 步流水线 <2min/1min 视频 |
| **LLM 流式**      | tokio_stream + mpsc 推送，避免 buffer 堆积            | 实时 token 输出 <50ms 延迟 |
| **FFmpeg 子进程** | tokio::process::Command + BufReader::lines() 流式解析 | 不阻塞主进程               |
| **数据库查询**    | sqlx 编译期校验 + 连接池 (max_connections=10)         | 查询 <5ms                  |
| **事件总线**      | tokio::sync::broadcast（无锁）                        | publish <1μs               |
| **i18n 资源**     | 启动时预加载到内存，切换语言零 IO                     | 语言切换 <50ms             |
| **UI 渲染**       | React 18 + Vite 5 + shadcn/ui（按需懒加载组件）       | 首屏 <300ms                |
| **状态管理**      | Zustand（无 immer）+ TanStack Query（自动缓存）       | 状态更新 <16ms             |
| **打包体积**      | LTO + strip + wasm opt + tree-shaking                 | <8MB 安装包                |

### 4.2 关键基准（criterion）

```rust
// benches/pipeline_bench.rs
use criterion::*;

fn bench_pipeline(c: &mut Criterion) {
    let rt = tokio::runtime::Runtime::new().unwrap();
    let project_path = PathBuf::from("tests/fixtures/sample_1min.mp4");

    c.bench_function("5-step pipeline (1 min video)", |b| {
        b.iter(|| {
            rt.block_on(async {
                let maker = MonologueMaker::new_test().await.unwrap();
                let mut project = maker.create_project(vec![project_path.clone()], MultiVideoStrategy::Single, "context".into(), EmotionType::Healing, NarrationStyle::Documentary).await.unwrap();
                maker.run_full_pipeline(&mut project, MonologueMakerConfig::default()).await.unwrap();
            });
        });
    });
}

criterion_group!(benches, bench_pipeline);
criterion_main!(benches);
```

## 5. 测试迁移方案

### 5.1 Python 测试作为"行为黄金文件"

```python
# tests/python_baseline/test_pipeline.py (保留运行 v2.4.3 Python 版)

def test_5_step_pipeline_sample_video():
    """作为 v3.0 Rust 实现的对照基准"""
    maker = MonologueMaker()
    project = maker.create_project("tests/fixtures/sample_1min.mp4", "test context", "healing")
    maker.run_full_pipeline(project)

    # 断言输出 JSON 与 v3.0 字段一致
    assert project.script
    assert project.audio_track
    assert project.subtitles
    assert os.path.exists(project.output_path)
```

**对比脚本**：

```python
# tests/python_baseline/compare_with_rust.py

import json
import subprocess

def run_rust_pipeline(video_path: str) -> dict:
    """调用 v3.0 Rust 二进制（CLI 模式）"""
    result = subprocess.run(
        ["scenefab-cli", "pipeline", "run", "--input", video_path, "--format", "json"],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)

def compare_outputs(python_out: dict, rust_out: dict) -> list[str]:
    """对比 Python 与 Rust 实现的输出，返回差异列表"""
    diffs = []
    # 对比脚本长度
    if abs(len(python_out["script"]) - len(rust_out["script"])) > 50:
        diffs.append(f"Script length diff: py={len(python_out['script'])} rust={len(rust_out['script'])}")
    # 对比音频时长
    if abs(python_out["audio_duration"] - rust_out["audio_duration"]) > 1.0:
        diffs.append(f"Audio duration diff: py={python_out['audio_duration']} rust={rust_out['audio_duration']}")
    # 对比字幕条数
    if abs(len(python_out["subtitles"]) - len(rust_out["subtitles"])) > 2:
        diffs.append(f"Subtitle count diff: py={len(python_out['subtitles'])} rust={len(rust_out['subtitles'])}")
    return diffs

if __name__ == "__main__":
    video = "tests/fixtures/sample_1min.mp4"
    py_out = run_python_pipeline(video)
    rust_out = run_rust_pipeline(video)
    diffs = compare_outputs(py_out, rust_out)
    if diffs:
        print("Differences found:")
        for d in diffs:
            print(f"  - {d}")
        exit(1)
    else:
        print("✅ Python and Rust outputs are equivalent")
```

### 5.2 Rust 单元测试

```rust
// crates/scenefab-llm/tests/openai_compat_test.rs

#[tokio::test]
async fn test_openai_compat_complete() {
    let mut server = mockito::Server::new_async().await;
    let mock = server.mock("POST", "/chat/completions")
        .with_status(200)
        .with_header("content-type", "application/json")
        .with_body(r#"{
            "id": "chatcmpl-123",
            "model": "gpt-4o",
            "choices": [{
                "index": 0,
                "message": { "role": "assistant", "content": "Hello!" },
                "finish_reason": "stop"
            }],
            "usage": { "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15 }
        }"#)
        .create_async()
        .await;

    let provider = OpenAiCompatProvider::new(OpenAiCompatConfig {
        provider_type: ProviderType::OpenAiCompat,
        display_name: "Test".into(),
        base_url: server.url(),
        api_key: "test-key".into(),
        default_model: "gpt-4o".into(),
        supported_models: vec!["gpt-4o".into()],
        max_context_tokens: 4096,
        request_timeout: Duration::from_secs(5),
    });

    let response = provider.complete(LlmRequest {
        model: "gpt-4o".into(),
        messages: vec![LlmMessage { role: LlmRole::User, content: "Hi".into() }],
        temperature: None,
        max_tokens: None,
        top_p: None,
        stop: None,
        user: None,
        stream: false,
    }).await.unwrap();

    assert_eq!(response.content, "Hello!");
    assert_eq!(response.usage.total_tokens, 15);
    mock.assert_async().await;
}
```

### 5.3 Playwright E2E

```typescript
// tests/e2e/pipeline.spec.ts

import { test, expect } from "@playwright/test";
import { startApp, stopApp } from "./helpers/tauri";

test("5-step pipeline with sample video", async ({ page }) => {
  await startApp(page);

  // 1. 进入生产页
  await page.click("text=生产");
  await expect(page).toHaveURL(/.*production/);

  // 2. 上传视频
  await page.setInputFiles(
    'input[type="file"]',
    "tests/fixtures/sample_1min.mp4",
  );
  await expect(page.locator("text=sample_1min.mp4")).toBeVisible();

  // 3. 启动流水线
  await page.click('button:has-text("开始制作")');

  // 4. 等待进度更新
  await expect(page.locator('[data-testid="progress-bar"]')).toHaveAttribute(
    "aria-valuenow",
    /\d+/,
  );

  // 5. 等待完成
  await expect(page.locator("text=处理完成")).toBeVisible({ timeout: 120_000 });

  // 6. 验证输出
  await expect(page.locator("text=sample_1min_jianying")).toBeVisible();

  await stopApp(page);
});
```

## 6. 总结

本章详细描述了 4 大子系统（API/Service/Plugin/Updater）的 Rust 重写方案：

- **API**：HTTP 改 Tauri Command，35 个 Command 替代 5 个 router
- **Service**：11 个 LLM Provider 1:1 迁移，MonologueMaker 5 步流水线，wasmtime 插件沙箱
- **Plugin**：Rust → WASM 编译，数字签名验证，权限模型
- **Updater**：5 阶段状态机保留，集成 tauri-plugin-updater
- **错误处理**：统一 SceneFabError + TS SceneFabError 类
- **性能**：多级优化（tokio/rayon/sqlx/wasm opt/LTO）
- **测试**：Python 作为行为黄金文件 + cargo test + Playwright E2E

下一步：

- [§08-frontend-react.md](./08-frontend-react.md) ── React 前端架构
- [§09-tauri-integration.md](./09-tauri-integration.md) ── Tauri 集成
- [§10-implementation-roadmap.md](./10-implementation-roadmap.md) ── 实施路线图
