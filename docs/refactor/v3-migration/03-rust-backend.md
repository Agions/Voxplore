# 03 · Rust 后端：crate 选型与依赖清单

> 📌 本章详细列出 v3.0 Rust workspace 的所有 crate 选型、版本、特性、依赖关系。

## 1. 选型总览（13 个 crate）

```
crates/
├── scenefab-core           基础设施（error/event/di/config/security/audit/task/i18n/monitor/path/fs/version/retry/metrics）
├── scenefab-domain         领域模型（纯数据 + 业务规则，不依赖 IO/UI）
├── scenefab-ffmpeg         FFmpeg/FFprobe 包装（tokio::process + 进度回调）
├── scenefab-llm            LLM 子系统（11 个 Provider + LlmManager + 流式）
├── scenefab-tts            TTS 子系统（Edge-TTS + TtsManager）
├── scenefab-video          视频处理（MonologueMaker / PipelineIntegrator / Analyzer）
├── scenefab-export         导出器（VideoExporter / JianyingExporter / Subtitle）
├── scenefab-pipeline       叙事流水线（5 步状态机 / fp_workflow / short_drama）
├── scenefab-plugin         插件系统（Registry / Loader / wasmtime 沙箱 / 签名）
├── scenefab-update         自动更新（Service / Downloader / Installer / 备份回滚）
├── scenefab-help           帮助系统（registry / markdown / i18n）
├── scenefab-i18n           国际化（后端文案，rust-i18n）
└── apps/desktop/src-tauri      Tauri 应用入口（Command 路由 + 事件桥）
```

### 1.1 各 crate 一句话定位

| Crate                | 一句话定位                                                                |
| -------------------- | ------------------------------------------------------------------------- |
| `scenefab-core`      | 跨领域基础设施：error/di/event/config/task/security/audit/monitor/path/fs |
| `scenefab-domain`    | 领域模型 + 业务规则：Project/Video/Narration/Series/Config/Preset         |
| `scenefab-ffmpeg`    | FFmpeg/FFprobe 进程包装：异步执行、进度回调、错误转译、硬件加速检测       |
| `scenefab-llm`       | LLM 抽象 + 11 个 Provider：OpenAI 兼容、Claude、DeepSeek、Gemini、Qwen 等 |
| `scenefab-tts`       | TTS 抽象 + Edge-TTS：WebSocket 流式、音频后处理                           |
| `scenefab-video`     | 视频处理核心：MonologueMaker 5 步 + PerspectiveMapper + VideoInterleaver  |
| `scenefab-export`    | 导出器：MP4/剪映草稿/字幕 SRT/ASS/VTT + 批量 + 预设                       |
| `scenefab-pipeline`  | 叙事流水线：5 步状态机 + 第一人称校验 + 整季短剧                          |
| `scenefab-plugin`    | 插件系统：WASM 沙箱 + 数字签名 + 权限模型 + SDK + 2 示例插件              |
| `scenefab-update`    | 自动更新：5 阶段状态机 + GitHub Releases + 增量包 fallback + 备份回滚     |
| `scenefab-help`      | 帮助系统：注册表 + Markdown 解析 + 主题 + 工具提示                        |
| `scenefab-i18n`      | 国际化：后端文案（rust-i18n）                                             |
| `apps/desktop/src-tauri` | Tauri 应用入口：Command 路由 + 事件桥 + Capability 声明 + 集成所有子系统  |

## 2. 各 crate 详细依赖

### 2.1 `scenefab-core`

**职责**：所有其他 crate 共享的基础设施。**0 业务依赖**。

```toml
[package]
name = "scenefab-core"
version.workspace = true
edition.workspace = true
license.workspace = true

[dependencies]
# 异步
tokio.workspace = true
async-trait.workspace = true
futures.workspace = true

# 序列化
serde.workspace = true
serde_json.workspace = true
serde_yaml.workspace = true
toml.workspace = true

# 错误
thiserror.workspace = true
anyhow.workspace = true

# 日志
tracing.workspace = true
tracing-subscriber.workspace = true
tracing-appender.workspace = true

# 安全
keyring.workspace = true
ring.workspace = true
constant_time_eq.workspace = true
sha2.workspace = true
hmac.workspace = true
hex.workspace = true
base64.workspace = true

# 系统
sysinfo.workspace = true
chrono.workspace = true
uuid.workspace = true

# 文件
tokio-util.workspace = true
zip.workspace = true
tempfile.workspace = true
walkdir.workspace = true

# 数据库
sqlx.workspace = true
sled.workspace = true

# 配置
figment.workspace = true
arc-swap.workspace = true

# 锁
parking_lot.workspace = true
flock.workspace = true

# 限流
governor.workspace = true

# 国际化
rust-i18n.workspace = true
unic-langid.workspace = true

# 实用
url.workspace = true
mime.workspace = true
bytes.workspace = true
dotenvy.workspace = true
directories.workspace = true
once_cell.workspace = true
regex.workspace = true
crossbeam-channel.workspace = true
rayon.workspace = true

# 并行
futures-util.workspace = true

[dev-dependencies]
tokio-test.workspace = true
mockito.workspace = true
wiremock.workspace = true
proptest.workspace = true
criterion.workspace = true
tempfile.workspace = true
```

**关键内部模块清单**：

```
src/
├── lib.rs                       # 模块导出
├── error.rs                     # SceneFabError + Result
├── result.rs                    # 类型别名
├── di.rs                        # AppContext
├── event.rs                     # EventBus (tokio broadcast)
├── event_types.rs               # 事件枚举
├── state.rs                     # AppState
├── config/
│   ├── mod.rs
│   ├── manager.rs               # ConfigManager
│   ├── settings.rs              # SettingsManager
│   └── definitions.rs           # ConfigDefinition 注册表
├── audit.rs                     # AuditLogger
├── security/
│   ├── mod.rs
│   ├── keyring.rs               # Keyring 包装
│   └── path.rs                  # 路径白名单
├── ratelimit.rs                 # RateLimiter
├── metrics.rs                   # 指标聚合
├── monitor.rs                   # SystemMonitor
├── retry.rs                     # 重试策略
├── version.rs                   # 版本号
├── time.rs                      # 时间工具
├── fs/
│   ├── mod.rs
│   ├── atomic_write.rs
│   └── zip.rs
├── task/
│   ├── mod.rs
│   ├── store.rs                 # TaskStore trait
│   ├── memory.rs                # InMemoryTaskStore
│   ├── sqlite.rs                # SqliteTaskStore
│   └── record.rs                # TaskRecord 数据
├── worker.rs                    # BaseWorker
└── i18n/
    ├── mod.rs
    └── messages.rs              # 后端文案加载
```

**关键 API 契约**（供其他 crate 使用）：

```rust
// error.rs
#[derive(Debug, thiserror::Error)]
pub enum SceneFabError {
    #[error("配置错误: {0}")]
    Config(String),

    #[error("IO 错误: {0}")]
    Io(#[from] std::io::Error),

    #[error("序列化错误: {0}")]
    Serde(#[from] serde_json::Error),

    #[error("数据库错误: {0}")]
    Database(#[from] sqlx::Error),

    #[error("LLM 调用错误: {0}")]
    Llm(String),

    #[error("TTS 调用错误: {0}")]
    Tts(String),

    #[error("FFmpeg 执行错误: {0}")]
    Ffmpeg(String),

    #[error("路径非法: {0}")]
    InvalidPath(String),

    #[error("插件错误: {0}")]
    Plugin(String),

    #[error("更新错误: {0}")]
    Update(String),

    #[error("服务未找到: {0}")]
    ServiceNotFound(String),

    #[error("权限拒绝: {0}")]
    PermissionDenied(String),

    #[error("已存在: {0}")]
    AlreadyExists(String),

    #[error("未找到: {0}")]
    NotFound(String),

    #[error("用户取消")]
    Cancelled,

    #[error("超时")]
    Timeout,

    #[error("{0}")]
    Other(String),
}

pub type Result<T> = std::result::Result<T, SceneFabError>;
```

### 2.2 `scenefab-domain`

**职责**：纯数据模型 + 业务规则。**仅依赖 core 的 error/result**。

```toml
[package]
name = "scenefab-domain"
version.workspace = true
edition.workspace = true

[dependencies]
scenefab-core = { path = "../scenefab-core" }

serde.workspace = true
serde_json.workspace = true
thiserror.workspace = true
chrono.workspace = true
uuid.workspace = true
specta = { workspace = true, features = ["derive"] }
ts-rs.workspace = true
url.workspace = true

[dev-dependencies]
proptest.workspace = true
```

**关键模块**：

```rust
// project.rs
#[derive(Debug, Clone, Serialize, Deserialize, specta::Type, ts_rs::TS)]
#[serde(rename_all = "snake_case")]
pub struct Project {
    pub id: Uuid,
    pub name: String,
    pub path: PathBuf,
    pub metadata: ProjectMetadata,
    pub settings: ProjectSettings,
    pub media_files: HashMap<Uuid, ProjectMedia>,
    pub timeline: ProjectTimeline,
    pub is_modified: bool,
    pub is_loaded: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, specta::Type)]
pub struct ProjectMetadata {
    pub name: String,
    pub description: Option<String>,
    pub project_type: ProjectType,
    pub author: String,
    pub version: String,
    pub created_at: DateTime<Utc>,
    pub modified_at: DateTime<Utc>,
}

// ... 更多模型
```

**关键约束**：

- 字段顺序与 v2.4.3 完全一致（向后兼容 JSON）
- 枚举使用 `#[serde(rename_all = "snake_case")]`
- 数值类型精度保留（如 f64 → f64，不要 f32）

### 2.3 `scenefab-ffmpeg`

**职责**：FFmpeg/FFprobe 异步进程包装。

```toml
[package]
name = "scenefab-ffmpeg"
version.workspace = true
edition.workspace = true

[dependencies]
scenefab-core = { path = "../scenefab-core" }

tokio.workspace = true
async-trait.workspace = true
serde.workspace = true
serde_json.workspace = true
thiserror.workspace = true
tracing.workspace = true
chrono.workspace = true
sysinfo.workspace = true
once_cell.workspace = true
```

**关键 API**：

```rust
// ffmpeg.rs
pub struct Ffmpeg {
    binary_path: PathBuf,
    ffprobe_path: PathBuf,
    hardware_accel: Option<HardwareAccel>,
}

impl Ffmpeg {
    pub fn new() -> Result<Self, SceneFabError> {
        // 探测 ffmpeg/ffprobe 路径
        // 探测硬件加速
    }

    /// 执行 ffmpeg 命令并返回进度流
    pub async fn execute<F>(&self, args: &[&str], on_progress: F) -> Result<PathBuf, SceneFabError>
    where
        F: Fn(FfmpegProgress) + Send + 'static,
    {
        // 启动 tokio::process::Command
        // 解析 stderr 中的 time=00:00:00.00 字段
        // 通过 on_progress 回调
    }

    /// 探测视频元数据
    pub async fn probe(&self, path: &Path) -> Result<MediaInfo, SceneFabError> {
        // ffprobe -v error -print_format json -show_format -show_streams
    }

    /// 拼接多个视频
    pub async fn concat(&self, inputs: &[PathBuf], output: &Path) -> Result<(), SceneFabError> { ... }

    /// 提取音频
    pub async fn extract_audio(&self, input: &Path, output: &Path) -> Result<(), SceneFabError> { ... }

    /// 视频穿插（按 timeline）
    pub async fn interleave(
        &self,
        timeline: &InterleaveTimeline,
        output: &Path,
    ) -> Result<(), SceneFabError> { ... }
}
```

**关键约束**：

- 不使用 `ffmpeg-next`（GPL 风险）
- 走子进程方式（稳定、跨平台）
- 进度解析需容错（不同 ffmpeg 版本输出格式微差异）

### 2.4 `scenefab-llm`

**职责**：LLM Provider 抽象 + 11 个实现 + LlmManager 路由。

```toml
[package]
name = "scenefab-llm"
version.workspace = true
edition.workspace = true

[dependencies]
scenefab-core = { path = "../scenefab-core" }
scenefab-domain = { path = "../scenefab-domain" }

tokio.workspace = true
async-trait.workspace = true
reqwest.workspace = true
futures.workspace = true
futures-util.workspace = true
serde.workspace = true
serde_json.workspace = true
thiserror.workspace = true
tracing.workspace = true
governor.workspace = true
chrono.workspace = true
url.workspace = true
once_cell.workspace = true
tokio-stream.workspace = true
pin-project-lite = "0.2"
```

**关键 API**：

```rust
// provider.rs
#[async_trait]
pub trait LlmProvider: Send + Sync {
    fn provider_type(&self) -> ProviderType;
    fn name(&self) -> &str;
    fn default_model(&self) -> &str;
    fn supported_models(&self) -> &[&str];
    fn max_context_tokens(&self) -> usize;

    /// 普通调用
    async fn complete(&self, request: LlmRequest) -> Result<LlmResponse, LlmError>;

    /// 流式调用
    async fn stream(
        &self,
        request: LlmRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<LlmChunk, LlmError>> + Send>>, LlmError>;

    /// 健康检查
    async fn health_check(&self) -> Result<(), LlmError>;
}

#[derive(Debug, Clone, Serialize, Deserialize, specta::Type)]
pub struct LlmRequest {
    pub model: String,
    pub messages: Vec<LlmMessage>,
    pub temperature: f32,
    pub max_tokens: Option<usize>,
    pub top_p: Option<f32>,
    pub stop: Option<Vec<String>>,
    pub user: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, specta::Type)]
#[serde(tag = "role", rename_all = "lowercase")]
pub enum LlmMessage {
    System { content: String },
    User { content: String },
    Assistant { content: String },
}

#[derive(Debug, Clone, Serialize, Deserialize, specta::Type)]
pub struct LlmResponse {
    pub id: String,
    pub model: String,
    pub content: String,
    pub usage: TokenUsage,
    pub finish_reason: FinishReason,
}
```

**11 个 Provider 实现位置**：

- `providers/openai_compat.rs` ── 通用 OpenAI 兼容协议
- `providers/claude.rs` ── Anthropic Claude
- `providers/deepseek.rs` ── DeepSeek
- `providers/doubao.rs` ── 字节豆包
- `providers/gemini.rs` ── Google Gemini
- `providers/glm5.rs` ── 智谱 GLM-5
- `providers/hunyuan.rs` ── 腾讯混元
- `providers/kimi.rs` ── Moonshot Kimi
- `providers/local.rs` ── Ollama
- `providers/qwen.rs` ── 阿里通义千问
- `providers/qwen37.rs` ── 通义 3.7

**关键约束**：

- 所有 Provider 实现统一 `LlmProvider` trait
- 流式响应统一返回 `Pin<Box<dyn Stream<Item = Result<LlmChunk, LlmError>>>>`
- 自动重试 + 失败切换（LlmManager 负责）
- token 限流（governor）

### 2.5 `scenefab-tts`

**职责**：TTS 抽象 + Edge-TTS 实现。

```toml
[package]
name = "scenefab-tts"
version.workspace = true
edition.workspace = true

[dependencies]
scenefab-core = { path = "../scenefab-core" }
scenefab-domain = { path = "../scenefab-domain" }

tokio.workspace = true
async-trait.workspace = true
reqwest.workspace = true
futures.workspace = true
serde.workspace = true
serde_json.workspace = true
thiserror.workspace = true
tracing.workspace = true
chrono.workspace = true
url.workspace = true
tokio-tungstenite = "0.24"  # Edge-TTS WebSocket
hound = "3.5"  # WAV 读写
```

**关键 API**：

```rust
#[async_trait]
pub trait TtsProvider: Send + Sync {
    fn provider_type(&self) -> TtsProviderType;
    fn name(&self) -> &str;
    async fn list_voices(&self) -> Result<Vec<VoiceInfo>, TtsError>;
    async fn synthesize(&self, request: TtsRequest) -> Result<TtsResult, TtsError>;
}

pub struct EdgeTtsProvider {
    config: EdgeTtsConfig,
}

impl EdgeTtsProvider {
    pub async fn new() -> Result<Self, TtsError> {
        // 探测 edge-tts 命令（子进程方式）
    }
}
```

**关键约束**：

- Edge-TTS 必须用子进程（避免 Python 依赖）
- 提供 fallback（edge-tts 不可用时降级到浏览器端 Web Speech API，前端处理）

### 2.6 `scenefab-video`

**职责**：视频处理核心（最复杂模块）。

```toml
[package]
name = "scenefab-video"
version.workspace = true
edition.workspace = true

[dependencies]
scenefab-core = { path = "../scenefab-core" }
scenefab-domain = { path = "../scenefab-domain" }
scenefab-ffmpeg = { path = "../scenefab-ffmpeg" }
scenefab-llm = { path = "../scenefab-llm" }
scenefab-tts = { path = "../scenefab-tts" }

tokio.workspace = true
async-trait.workspace = true
futures.workspace = true
rayon.workspace = true
serde.workspace = true
serde_json.workspace = true
thiserror.workspace = true
tracing.workspace = true
chrono.workspace = true
uuid.workspace = true
once_cell.workspace = true
```

**关键模块**：

```rust
// monologue_maker.rs
pub struct MonologueMaker {
    ffmpeg: Arc<Ffmpeg>,
    llm: Arc<LlmManager>,
    tts: Arc<TtsManager>,
    caption_gen: Arc<CaptionGenerator>,
    event_bus: Arc<EventBus>,
}

impl MonologueMaker {
    pub async fn create_project(
        &self,
        source_videos: Vec<PathBuf>,
        strategy: MultiVideoStrategy,
        context: String,
        emotion: EmotionType,
        style: NarrationStyle,
    ) -> Result<MonologueProject, SceneFabError> { ... }

    /// 步骤 1: 分析场景
    pub async fn analyze_scenes(
        &self,
        project: &mut MonologueProject,
    ) -> Result<SceneInfo, SceneFabError> { ... }

    /// 步骤 2: 生成脚本
    pub async fn generate_script(
        &self,
        project: &mut MonologueProject,
        custom_script: Option<String>,
    ) -> Result<Script, SceneFabError> { ... }

    /// 步骤 3: 生成配音
    pub async fn generate_voice(
        &self,
        project: &mut MonologueProject,
    ) -> Result<AudioTrack, SceneFabError> { ... }

    /// 步骤 4: 生成字幕
    pub async fn generate_captions(
        &self,
        project: &mut MonologueProject,
        style: CaptionStyle,
    ) -> Result<Vec<SubtitleItem>, SceneFabError> { ... }

    /// 步骤 5: 导出
    pub async fn export_to_jianying(
        &self,
        project: &MonologueProject,
        output_dir: &Path,
    ) -> Result<PathBuf, SceneFabError> { ... }

    /// 完整流水线
    pub async fn run_full_pipeline(
        &self,
        project: &mut MonologueProject,
        include_interleave: bool,
    ) -> Result<InterleaveTimeline, SceneFabError> { ... }
}
```

**关键约束**：

- 5 步流程串行执行，步骤间通过 `project.script/audio_track/captions` 字段串联
- 每步通过 event_bus 发布 `pipeline.progress` 事件
- 支持 cancel（tokio::sync::watch）
- CPU 密集操作（抽帧/分析）用 `tokio::task::spawn_blocking` 或 `rayon`

### 2.7 `scenefab-export`

**职责**：导出器（视频、剪映草稿、字幕）。

```toml
[package]
name = "scenefab-export"
version.workspace = true
edition.workspace = true

[dependencies]
scenefab-core = { path = "../scenefab-core" }
scenefab-domain = { path = "../scenefab-domain" }
scenefab-ffmpeg = { path = "../scenefab-ffmpeg" }

tokio.workspace = true
async-trait.workspace = true
serde.workspace = true
serde_json.workspace = true
thiserror.workspace = true
tracing.workspace = true
chrono.workspace = true
```

**关键 API**：

```rust
pub struct ExportManager {
    ffmpeg: Arc<Ffmpeg>,
    presets: HashMap<ExportFormat, ExportPreset>,
}

impl ExportManager {
    /// 导出为 MP4
    pub async fn export_mp4(
        &self,
        timeline: &InterleaveTimeline,
        audio: &AudioTrack,
        output: &Path,
        preset: ExportPreset,
    ) -> Result<PathBuf, SceneFabError> { ... }

    /// 导出为剪映草稿
    pub async fn export_jianying(
        &self,
        project: &MonologueProject,
        output_dir: &Path,
    ) -> Result<PathBuf, SceneFabError> { ... }

    /// 导出字幕 SRT/ASS/VTT
    pub async fn export_subtitle(
        &self,
        subtitles: &[SubtitleItem],
        format: SubtitleFormat,
        output: &Path,
    ) -> Result<(), SceneFabError> { ... }

    /// 批量导出
    pub async fn batch_export(
        &self,
        jobs: Vec<ExportJob>,
        on_progress: impl Fn(ExportProgress),
    ) -> Result<Vec<PathBuf>, SceneFabError> { ... }
}
```

### 2.8 `scenefab-pipeline`

**职责**：叙事流水线（5 步状态机 + 第一人称校验 + 整季短剧）。

```toml
[package]
name = "scenefab-pipeline"
version.workspace = true
edition.workspace = true

[dependencies]
scenefab-core = { path = "../scenefab-core" }
scenefab-domain = { path = "../scenefab-domain" }
scenefab-video = { path = "../scenefab-video" }
scenefab-llm = { path = "../scenefab-llm" }

tokio.workspace = true
async-trait.workspace = true
serde.workspace = true
thiserror.workspace = true
tracing.workspace = true
```

**关键 API**：

```rust
pub struct PipelineState {
    pub stage: PipelineStage,
    pub progress: f32,
    pub error: Option<String>,
}

pub enum PipelineStage {
    Import,
    Analyze,
    Script,
    Voice,
    Caption,
    Export,
    Completed,
    Failed,
    Cancelled,
}

pub trait PipelineStep: Send + Sync {
    fn name(&self) -> &str;
    fn stage(&self) -> PipelineStage;
    async fn execute(
        &self,
        context: &mut PipelineContext,
    ) -> Result<(), SceneFabError>;
}
```

### 2.9 `scenefab-plugin`

**职责**：插件系统（Registry + Loader + wasmtime 沙箱 + 数字签名）。

```toml
[package]
name = "scenefab-plugin"
version.workspace = true
edition.workspace = true

[dependencies]
scenefab-core = { path = "../scenefab-core" }
scenefab-domain = { path = "../scenefab-domain" }

tokio.workspace = true
async-trait.workspace = true
serde.workspace = true
serde_json.workspace = true
toml.workspace = true
thiserror.workspace = true
tracing.workspace = true
wasmtime.workspace = true
wasmtime-wasi.workspace = true
ring.workspace = true
ed25519-dalek = "2.1"
chrono.workspace = true
uuid.workspace = true
walkdir.workspace = true
once_cell.workspace = true
url.workspace = true
```

**关键 API**：

```rust
// manifest.rs
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginManifest {
    pub id: String,
    pub name: String,
    pub version: String,
    pub author: String,
    pub description: String,
    pub plugin_type: PluginType,
    pub entry_point: String,
    pub wasm: Option<PathBuf>,
    pub dependencies: HashMap<String, String>,
    pub permissions: Vec<Permission>,
    pub signature: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Permission {
    Network { allowed_hosts: Vec<String> },
    Filesystem { allowed_paths: Vec<PathBuf>, mode: FsMode },
    Environment { allowed_vars: Vec<String> },
    SystemInfo,
    Notifications,
}

pub enum PluginType {
    AiGenerator,
    SubtitleStyle,
    Export,
    VoiceClone,
    VideoEffect,
    SceneDetector,
}

// runtime.rs
pub struct PluginRuntime {
    engine: wasmtime::Engine,
    instances: HashMap<String, PluginInstance>,
}

impl PluginRuntime {
    pub async fn load(
        &self,
        manifest: &PluginManifest,
        context: &AppContext,
    ) -> Result<PluginHandle, PluginError> { ... }

    pub async fn call(
        &self,
        handle: &PluginHandle,
        func: &str,
        args: Vec<WasmValue>,
    ) -> Result<Vec<WasmValue>, PluginError> { ... }

    pub async fn unload(&self, handle: PluginHandle) -> Result<(), PluginError> { ... }
}

// signature.rs
pub struct SignatureVerifier {
    trusted_keys: Vec<ed25519_dalek::VerifyingKey>,
}

impl SignatureVerifier {
    pub fn verify(
        &self,
        wasm_bytes: &[u8],
        signature_b64: &str,
        public_key_b64: &str,
    ) -> Result<(), SignatureError> { ... }
}
```

**关键约束**：

- 第三方插件必须 WASM 化（不能用动态链接库）
- 数字签名强制（v2.5 无，v3.0 新增）
- 权限模型最小化（用户在 UI 显式授权）

### 2.10 `scenefab-update`

**职责**：自动更新（基于 tauri-plugin-updater 上层封装）。

```toml
[package]
name = "scenefab-update"
version.workspace = true
edition.workspace = true

[dependencies]
scenefab-core = { path = "../scenefab-core" }
scenefab-domain = { path = "../scenefab-domain" }

tokio.workspace = true
async-trait.workspace = true
reqwest.workspace = true
serde.workspace = true
serde_json.workspace = true
thiserror.workspace = true
tracing.workspace = true
chrono.workspace = true
sha2.workspace = true
hex.workspace = true
zip.workspace = true
```

**关键 API**：

```rust
pub struct UpdaterService {
    channel: UpdateChannel,
    current_version: Version,
    api_url: String,
    downloader: Downloader,
    installer: Installer,
    state: Arc<RwLock<UpdaterState>>,
    event_tx: broadcast::Sender<UpdaterEvent>,
}

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
    pub async fn check(&self) -> Result<Option<UpdateManifest>, SceneFabError> { ... }
    pub async fn download_and_install(
        &self,
        manifest: &UpdateManifest,
    ) -> Result<(), SceneFabError> { ... }
    pub async fn rollback(&self, version: &str) -> Result<(), SceneFabError> { ... }
    pub fn subscribe(&self) -> broadcast::Receiver<UpdaterEvent> { ... }
}
```

### 2.11 `scenefab-help`

**职责**：帮助系统。

```toml
[package]
name = "scenefab-help"
version.workspace = true
edition.workspace = true

[dependencies]
scenefab-core = { path = "../scenefab-core" }
scenefab-domain = { path = "../scenefab-domain" }

serde.workspace = true
serde_json.workspace = true
thiserror.workspace = true
pulldown-cmark = "0.12"
chrono.workspace = true
uuid.workspace = true
```

### 2.12 `scenefab-i18n`

**职责**：后端国际化（rust-i18n 包装）。

```toml
[package]
name = "scenefab-i18n"
version.workspace = true
edition.workspace = true

[dependencies]
scenefab-core = { path = "../scenefab-core" }

rust-i18n.workspace = true
unic-langid.workspace = true
serde.workspace = true
serde_json.workspace = true
thiserror.workspace = true
```

### 2.13 `apps/desktop/src-tauri`

**职责**：Tauri 应用入口。

```toml
[package]
name = "apps/desktop/src-tauri"
version.workspace = true
edition.workspace = true

[lib]
name = "scenefab_app_lib"
crate-type = ["staticlib", "cdylib", "rlib"]

[build-dependencies]
tauri-build = { version = "2.0", features = [] }

[dependencies]
# 内部 crate
scenefab-core = { path = "../scenefab-core" }
scenefab-domain = { path = "../scenefab-domain" }
scenefab-ffmpeg = { path = "../scenefab-ffmpeg" }
scenefab-llm = { path = "../scenefab-llm" }
scenefab-tts = { path = "../scenefab-tts" }
scenefab-video = { path = "../scenefab-video" }
scenefab-export = { path = "../scenefab-export" }
scenefab-pipeline = { path = "../scenefab-pipeline" }
scenefab-plugin = { path = "../scenefab-plugin" }
scenefab-update = { path = "../scenefab-update" }
scenefab-help = { path = "../scenefab-help" }
scenefab-i18n = { path = "../scenefab-i18n" }

# Tauri
tauri = { workspace = true, features = ["macos-private-api", "tray-icon"] }
tauri-plugin-fs.workspace = true
tauri-plugin-dialog.workspace = true
tauri-plugin-shell.workspace = true
tauri-plugin-updater.workspace = true
tauri-plugin-store.workspace = true
tauri-plugin-os.workspace = true
tauri-plugin-notification.workspace = true
tauri-plugin-process.workspace = true
tauri-plugin-window-state.workspace = true
tauri-plugin-deep-link.workspace = true
tauri-plugin-log.workspace = true
tauri-plugin-single-instance.workspace = true

# Specta (IPC 类型)
specta.workspace = true
specta-typescript.workspace = true
specta-derive = "2.0.0-rc.20"

# 异步
tokio.workspace = true
async-trait.workspace = true

# 序列化
serde.workspace = true
serde_json.workspace = true

# 错误
thiserror.workspace = true
anyhow.workspace = true

# 日志
tracing.workspace = true
tracing-subscriber.workspace = true

# 其他
chrono.workspace = true
uuid.workspace = true
```

## 3. 关键依赖版本约束

| Crate           | 版本        | 关键理由                                |
| --------------- | ----------- | --------------------------------------- |
| `tokio`         | 1.42        | 稳定的 async runtime，Tauri 2 默认依赖  |
| `tauri`         | 2.1         | Tauri 2 稳定版 + tray-icon 支持         |
| `serde`         | 1.0         | 序列化标准                              |
| `serde_json`    | 1.0         | JSON 支持（向后兼容 .scenefab 必需）    |
| `sqlx`          | 0.8         | compile-time checked SQL，async         |
| `sled`          | 0.34        | 嵌入式 KV，零依赖                       |
| `reqwest`       | 0.12        | HTTP 客户端（rustls-tls，避开 OpenSSL） |
| `wasmtime`      | 29.0        | WASM 运行时，最新版                     |
| `keyring`       | 3.6         | 跨平台密钥存储                          |
| `rustls`        | 0.23        | 现代 TLS 实现（无 OpenSSL）             |
| `figment`       | 0.10        | 配置管理（YAML/TOML/ENV）               |
| `rust-i18n`     | 3.1         | 国际化（与前端 i18next 兼容）           |
| `thiserror`     | 2.0         | 错误定义（编译期派生）                  |
| `tracing`       | 0.1         | 结构化日志                              |
| `specta`        | 2.0.0-rc.20 | Tauri Command 类型生成（TS 绑定）       |
| `governor`      | 0.7         | 限流（Rate Limiter）                    |
| `criterion`     | 0.5         | 性能基准                                |
| `cargo-nextest` | 0.9         | 测试运行器（并行）                      |

## 4. 开发工具链

```toml
# rust-toolchain.toml
[toolchain]
channel = "1.85.0"
profile = "default"
components = ["clippy", "rustfmt", "rust-analyzer", "rust-src"]
```

```toml
# .rustfmt.toml
max_width = 100
hard_tabs = false
tab_spaces = 4
edition = "2021"
use_small_heuristics = "Max"
imports_granularity = "Crate"
group_imports = "StdExternalCrate"
```

```toml
# .clippy.toml
avoid-breaking-exported-api = false
msrv = "1.85"
cognitive-complexity-threshold = 30
too-many-arguments-threshold = 7
```

## 5. 编译性能优化

```toml
# .cargo/config.toml
[build]
rustc-wrapper = "sccache"  # 共享编译缓存（CI 必需）

[target.x86_64-unknown-linux-gnu]
linker = "clang"
rustflags = ["-C", "link-arg=-fuse-ld=mold"]

[target.aarch64-apple-darwin]
linker = "clang"
rustflags = ["-C", "link-arg=-fuse-ld=lld"]

[target.x86_64-apple-darwin]
linker = "clang"
rustflags = ["-C", "link-arg=-fuse-ld=lld"]

[target.x86_64-pc-windows-msvc]
linker = "lld-link"
```

**编译时间预估**：

- 全 workspace clean build：~12 分钟（CI）
- 增量编译（修改 1 个文件）：~3-8 秒
- 启用 sccache：CI 首次 ~12 分钟，缓存命中后 ~2 分钟

## 6. 测试矩阵

| Crate                | 单元测试 (cargo test) | 集成测试 (cargo test --test)  | 覆盖率目标 |
| -------------------- | --------------------- | ----------------------------- | ---------- |
| `scenefab-core`      | ✅ 全模块             | -                             | ≥ 80%      |
| `scenefab-domain`    | ✅ 全模块             | -                             | ≥ 70%      |
| `scenefab-ffmpeg`    | ✅ 包装层             | ✅ 真实 ffmpeg 集成           | ≥ 70%      |
| `scenefab-llm`       | ✅ Provider 抽象      | ✅ 11 个 Provider 集成 (mock) | ≥ 70%      |
| `scenefab-tts`       | ✅ Provider 抽象      | ✅ Edge-TTS 集成              | ≥ 60%      |
| `scenefab-video`     | ✅ 关键算法           | ✅ 端到端小视频               | ≥ 70%      |
| `scenefab-export`    | ✅ JSON 序列化        | ✅ 剪映草稿集成               | ≥ 70%      |
| `scenefab-pipeline`  | ✅ 状态机             | -                             | ≥ 80%      |
| `scenefab-plugin`    | ✅ Registry           | ✅ wasmtime 沙箱              | ≥ 70%      |
| `scenefab-update`    | ✅ 5 阶段状态机       | -                             | ≥ 80%      |
| `scenefab-help`      | ✅ Markdown 解析      | -                             | ≥ 60%      |
| `scenefab-i18n`      | ✅ 加载               | -                             | ≥ 60%      |
| `apps/desktop/src-tauri` | ✅ Command 参数       | ✅ E2E 工作流                 | ≥ 60%      |

## 7. 关键性能基准（criterion）

```rust
// benches/pipeline_bench.rs
use criterion::{criterion_group, criterion_main, Criterion};

fn bench_monologue_pipeline(c: &mut Criterion) {
    c.bench_function("5-step pipeline (1 min video)", |b| {
        b.iter(|| {
            // 加载 fixture，运行完整流水线
        });
    });
}

fn bench_llm_streaming(c: &mut Criterion) {
    c.bench_function("LLM streaming 1000 tokens", |b| {
        b.iter(|| {
            // mock LLM 流式响应
        });
    });
}

criterion_group!(benches, bench_monologue_pipeline, bench_llm_streaming);
criterion_main!(benches);
```

## 8. 总结

- **13 个 crate**，严格分层（infra → domain → service → application）
- **依赖方向**：app → 6 service crate → 3 infra crate → 3rd-party
- **关键 crate**：scenefab-video（最复杂）、scenefab-llm（11 个 Provider）、scenefab-plugin（WASM 沙箱）
- **测试覆盖**：核心 crate ≥ 80%，服务 crate ≥ 70%
- **编译优化**：sccache + mold/lld linker，CI 缓存命中后 ~2 分钟
- **关键版本**：Rust 1.85、Tauri 2.1、tokio 1.42、sqlx 0.8、wasmtime 29

详细模块映射见 [§04-module-mapping.md](./04-module-mapping.md)。
